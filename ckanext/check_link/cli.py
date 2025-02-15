from __future__ import annotations

import logging
from collections import Counter
from itertools import islice
from typing import Iterable, TypeVar

from datetime import datetime
from datetime import date

import ckan.model as model
import ckan.plugins.toolkit as tk
import click
from .model import Report

T = TypeVar("T")
log = logging.getLogger(__name__)


def get_commands():
    return [check_link]


@click.group(short_help="Check link availability")
@click.pass_context
def check_link(ctx):
    pass


@check_link.command()
@click.option(
    "-d", "--include-draft", is_flag=True, help="Check draft packages as well"
)
@click.option(
    "-p", "--include-private", is_flag=True, help="Check private packages as well"
)
@click.option(
    "-c",
    "--chunk",
    help="Number of packages that processed simultaneously",
    default=1,
    type=click.IntRange(
        1,
    ),
)
@click.option(
    "-d", "--delay", default=0, help="Delay between requests", type=click.FloatRange(0)
)
@click.option(
    "-t", "--timeout", default=60, help="Request timeout", type=click.FloatRange(0)
)
@click.argument("ids", nargs=-1)
def check_packages(
        include_draft: bool, include_private: bool, ids: tuple[str, ...], chunk: int,
        delay: float, timeout: float
):
    """Check every resource inside each package.

    Scope can be narrowed via arbitary number of arguments, specifying
    package's ID or name.

    """
    user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"user": user["name"]}

    check = tk.get_action("check_link_search_check")
    states = ["active"]

    if include_draft:
        states.append("draft")

    q = model.Session.query(model.Package.id).filter(
        model.Package.state.in_(states),
    )

    if not include_private:
        q = q.filter(model.Package.private == False)

    if ids:
        q = q.filter(model.Package.id.in_(ids) | model.Package.name.in_(ids))

    stats = Counter()
    with click.progressbar(q, length=q.count()) as bar:
        while True:
            buff = _take(bar, chunk)
            if not buff:
                break

            result = check(
                context.copy(),
                {
                    "fq": "id:({})".format(" OR ".join(p.id for p in buff)),
                    "save": True,
                    "clear_available": False,
                    "include_drafts": include_draft,
                    "include_private": include_private,
                    "skip_invalid": True,
                    "rows": chunk,
                    "link_patch": {"delay": delay, "timeout": timeout},
                },
            )
            stats.update(r["state"] for r in result)
            overview = (
                ", ".join(
                    f"{click.style(k,  underline=True)}:"
                    f" {click.style(str(v),bold=True)}"
                    for k, v in stats.items()
                )
                or "not available"
            )
            bar.label = f"Overview: {overview}"

    click.secho("Done", fg="green")


def _take(seq: Iterable[T], size: int) -> list[T]:
    return list(islice(seq, size))


class Date(click.ParamType):
    name = 'date'

    def __init__(self, formats=None):
        self.formats = formats or [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d'
        ]

    def get_metavar(self, param):
        return '[{}]'.format('|'.join(self.formats))

    def _try_to_convert_date(self, value, format):
        try:
            return datetime.strptime(value, format)
        except ValueError:
            return None

    def convert(self, value, param, ctx):
        for format in self.formats:
            date = self._try_to_convert_date(value, format)
            if date:
                return date

        self.fail(
            'invalid date format: {}. (choose from {})'.format(
                value, ', '.join(self.formats)))

    def __repr__(self):
        return 'Date'

def _purge_stale_applications( older_than ):
    """ When a URL is changed on an application, the check-link record for the old URL remains in the check_link_report table. 
    This function is used to remove check-link records for application links that have not been checked since 'older_than'.
    This function is called immediately after doing a check-applications with older_than set to the datetime when the check-applications process began.
    It can also be invoked from the CLI with an arbitraty older_than value.

    Args:
        older_than (Date): string formatted as %Y-%m-%dT%H:%M:%S, %Y-%m-%d %H:%M:%S, or %Y-%m-%d
    """

    log.info( 'Purging application resource records that have not been checked since {}'.format( older_than ))

    q = model.Session.query(Report).filter(
        Report.resource_id.is_(None),
        Report.last_checked < older_than
    )

    if q.count() == 0:
        log.info( 'No stale resource records found.' )
    else:
        log.info( '{} stale check_link application resource records found.'.format( q.count() ) )

        user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
        context = {"user": user["name"]}

        action = tk.get_action("check_link_report_delete")

        with click.progressbar(q, length=q.count()) as bar:
            for report in bar:
                log.info( 'Deleting check_link record for record {}'.format( report.id ) )
                action(context.copy(), {"id": report.id})


@check_link.command()
@click.option(
    "-d", "--include-draft", is_flag=True, help="Check draft applications as well"
)
@click.option(
    "-p", "--include-private", is_flag=True, help="Check private applications as well"
)
@click.option(
    "-c",
    "--chunk",
    help="Number of applications that processed simultaneously",
    default=1,
    type=click.IntRange(
        1,
    ),
)
@click.option(
    "-d", "--delay", default=0, help="Delay between requests", type=click.FloatRange(0)
)
@click.option(
    "-t", "--timeout", default=60, help="Request timeout", type=click.FloatRange(0)
)
@click.option(
    "-i", "--ignore-local-resources", is_flag=True, help="Do not check resources hosted locally"
)
@click.argument("ids", nargs=-1)
def check_applications(
        include_draft: bool, include_private: bool, ids: tuple[str, ...], chunk: int,
        delay: float, timeout: float,  ignore_local_resources: bool,
):
    """Check every application link.

    Scope can be narrowed via arbitary number of arguments, specifying
    application's ID or name.

    """
    start_time = datetime.now()
    site_url = tk.config.get('ckan.site_url')

    user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"user": user["name"]}

    check = tk.get_action("check_link_application_check")
    states = ["active"]
    types = ["application"]

    if include_draft:
        states.append("draft")

    q = model.Session.query(model.Package.id,model.Package.title).filter(
        model.Package.state.in_(states),
        model.Package.type.in_(types),
    )

    if not include_private:
        q = q.filter(model.Package.private == False)

    if ids:
        q = q.filter(model.Package.id.in_(ids) | model.Package.name.in_(ids))

    if ignore_local_resources:
        log.info( "--ignore_local_resources is set, so local resources will not be checked" )
        # Ignore resources hosted on the same domain as the portal
        q = q.filter(model.Package.url.notlike("{site_url}%".format(site_url=site_url)))
        # Ignore resources that don't start with http
        q = q.filter(~(model.Package.url.notlike("http%")))


    log.info( 'APPLICATIONS TO CHECK:')
    for result in q:
        log.info("{name}".format(name=result.title))

    
    stats = Counter()
    with click.progressbar(q, length=q.count()) as bar:
        while True:

            buff = _take(bar, chunk)
            if not buff:
                break

            result = check(
                context.copy(),
                {
                    "fq": "id:({})".format(" OR ".join(p.id for p in buff)),
                    "save": True,
                    "clear_available": False,
                    "include_drafts": include_draft,
                    "include_private": include_private,
                    "skip_invalid": True,
                    "rows": chunk,
                    "link_patch": {"delay": delay, "timeout": timeout},
                },
            )
            stats.update(r["state"] for r in result)
            overview = (
                ", ".join(
                    f"{click.style(k,  underline=True)}:"
                    f" {click.style(str(v),bold=True)}"
                    for k, v in stats.items()
                )
                or "not available"
            )
            bar.label = f"Overview: {overview}"

    # tk.get_action("check_link_email_report")({},{})

    click.secho("Done", fg="green")

    _purge_stale_applications( start_time )


@check_link.command()
@click.argument('older_than', type=Date())
def purge_stale_applications( older_than ):
    _purge_stale_applications( older_than )

def _take(seq: Iterable[T], size: int) -> list[T]:
    return list(islice(seq, size))


@check_link.command()
@click.option(
    "-d", "--delay", default=0, help="Delay between requests", type=click.FloatRange(0)
)
@click.option(
    "-t", "--timeout", default=60, help="Request timeout", type=click.FloatRange(0)
)
@click.option(
    "-i", "--ignore-local-resources", is_flag=True, help="Do not check resources hosted locally"
)
@click.argument("ids", nargs=-1)
def check_resources(ids: tuple[str, ...], delay: float, timeout: float, ignore_local_resources: bool, ):
    """Check every resource on the portal.

    Scope can be narrowed via arbitary number of arguments, specifying
    resource's ID or name.
    """

    site_url = tk.config.get('ckan.site_url')

    user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"user": user["name"]}

    check = tk.get_action("check_link_resource_check")
    q = model.Session.query(model.Resource.id,model.Resource.name,model.Resource.url).filter_by(state="active")

    if ids:
        q = q.filter(model.Resource.id.in_(ids))

    if ignore_local_resources:
        log.info( "--ignore_local_resources is set, so local resources will not be checked" )
        # Ignore resources hosted on the same domain as the portal
        q = q.filter(model.Resource.url.notlike("{site_url}%".format(site_url=site_url)))
        # Ignore resources that don't start with http
        q = q.filter(~(model.Resource.url.notlike("http%")))

    q = q.filter(model.Resource.url.notlike("http://_datastore_only_resource%"))

    stats = Counter()
    total = q.count()
    overview = "Not ready yet"
    results = []

    log.info( 'RESOURCE URLS TO CHECK:')
    for r in q:
        log.info("{name} : {url}".format(name=r.name or 'Unknown',url=r.url or 'Unknown'))

    with click.progressbar(q, length=total) as bar:
        for res in bar:
            bar.label = f"Current: {res.id}. Overview({total} total): {overview}"
            try:
                result = check(
                    context.copy(),
                    {
                        "save": True,
                        "clear_available": False,
                        "id": res.id,
                        "link_patch": {"delay": delay, "timeout": timeout},
                    },
                )
            except tk.ValidationError as e:
                log.error("Cannot check %s: %s", res.id, e)
                result = {"state": "exception"}

            results.append( result )

            stats[result["state"]] += 1
            overview = (
                ", ".join(
                    f"{click.style(k,  underline=True)}:"
                    f" {click.style(str(v),bold=True)}"
                    for k, v in stats.items()
                )
                or "not available"
            )
            bar.label = f"Current: {res.id}. Overview({total} total): {overview}"

    click.secho("Done", fg="green")

    # tk.get_action("check_link_email_report")({},{})

@check_link.command()
@click.option("-o", "--orphans-only", is_flag=True, help="Only drop reports for resources that point to a nonexistent dataset")
def purge_reports(orphans_only: bool):
    """Purge check-link reports.
    """
    q = model.Session.query(Report)

    if orphans_only:
        q = q.outerjoin(model.Resource, Report.resource_id == model.Resource.id).filter(
            Report.resource_id.isnot(None),
            model.Resource.id.is_(None) | (model.Resource.state != "active")
        )

    if q.count() == 0:
        if orphans_only:
            log.info( 'No orphaned check_link resource records found.' )
        else:
            log.info( 'No check_link resource records found.' )
    else:
        if orphans_only:
            log.info( '{} orphaned check_link resource records found.'.format( q.count() ) )
        else:
            log.info( '{} check_link resource records found.'.format( q.count() ) )
        user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
        context = {"user": user["name"]}

        action = tk.get_action("check_link_report_delete")
        with click.progressbar(q, length=q.count()) as bar:
            for report in bar:
                log.info( 'Deleting check_link record for resource {}'.format( report.resource_id ) )
                action(context.copy(), {"id": report.id})

@check_link.command()
@click.pass_context
def mail_report(ctx):
    """
    Email check_link report
    """

    flask_app = ctx.meta["flask_app"]
    user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"user": user["name"]}

    report = tk.get_action("check_link_email_report")

    with flask_app.test_request_context():
        report( context.copy(), {} )