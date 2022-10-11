from __future__ import annotations

import logging
from collections import Counter
from itertools import islice
from typing import Iterable, TypeVar

import ckan.model as model
import ckan.plugins.toolkit as tk
import click
from .model import Report

T = TypeVar("T")
log = logging.getLogger(__name__)


def get_commands():
    return [check_link]


@click.group(short_help="Check link availability")
def check_link():
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
    "-t", "--timeout", default=10, help="Request timeout", type=click.FloatRange(0)
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


@check_link.command()
@click.option(
    "-d", "--delay", default=0, help="Delay between requests", type=click.FloatRange(0)
)
@click.option(
    "-t", "--timeout", default=10, help="Request timeout", type=click.FloatRange(0)
)
@click.argument("ids", nargs=-1)
def check_resources(ids: tuple[str, ...], delay: float, timeout: float):
    """Check every resource on the portal.

    Scope can be narrowed via arbitary number of arguments, specifying
    resource's ID or name.
    """
    user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"user": user["name"]}

    check = tk.get_action("check_link_resource_check")
    q = model.Session.query(model.Resource.id).filter_by(state="active")
    if ids:
        q = q.filter(model.Resource.id.in_(ids))

    stats = Counter()
    total = q.count()
    overview = "Not ready yet"
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


@check_link.command()
@click.option("-o", "--orphans-only", is_flag=True, help="Only drop reports that point to an unexisting resource")
def delete_reports(orphans_only: bool):
    """Delete check-link reports.
    """
    q = model.Session.query(Report)
    if orphans_only:
        q = q.outerjoin(model.Resource, Report.resource_id == model.Resource.id).filter(
            Report.resource_id.isnot(None),
            model.Resource.id.is_(None) | (model.Resource.state != "active")
        )

    user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"user": user["name"]}

    action = tk.get_action("check_link_report_delete")
    with click.progressbar(q, length=q.count()) as bar:
        for report in bar:
            action(context.copy(), {"id": report.id})
