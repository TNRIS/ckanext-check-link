from __future__ import annotations

import ckan.lib.helpers as h
import ckan.plugins.toolkit as tk
from ckan.logic import validate

from ckanext.check_link.model import Report
from ckanext.toolbelt.decorators import Collector

from .. import schema

from datetime import datetime
import logging

from ckan.lib import mailer
import socket
from jinja2 import escape
from flask import render_template

action, get_actions = Collector("check_link").split()

log = logging.getLogger(__name__)

@action
@validate(schema.report_save)
def report_save(context, data_dict):
    tk.check_access("check_link_report_save", context, data_dict)
    sess = context["session"]
    data_dict["details"].update(data_dict.pop("__extras", {}))

    try:
        existing = tk.get_action("check_link_report_show")(context, data_dict)
    except tk.ObjectNotFound:
        report = Report(**{**data_dict, "id": None})
        sess.add(report)
    else:
        report = sess.query(Report).filter(Report.id == existing["id"]).one()
        # this line update `last_checked` value. Consider removing old report and
        # creating a brand new one instead, as it would be nice to have ID
        # regenerated as well
        report.touch()

        #log.warning( data_dict )
        if data_dict["state"] == "available":
            # link is currently available
            report.last_available = datetime.utcnow()
        elif report.state == 'available' and data_dict["state"] != "available":
            # state changed between last check and current check, so we set
            # last_available to previous check time. 
            # NOTE: last_checked would be better named last_checked
            report.last_available = report.last_checked
        else:
            # link was unavailable during last check, and continues to be
            pass

        if data_dict["state"] != report.state:
            report.last_status_change = datetime.utcnow()
            #log.warning( 'STATUS CHANGE from %s to %s', report.state, data_dict["state"] )

        for k, v in data_dict.items():
            #log.warning( 'data_dict: %s = %s', k, v )
            if k == "id":
                continue
            setattr(report, k, v)

    sess.commit()

    return report.dictize(context)


@action
@validate(schema.report_show)
def report_show(context, data_dict):
    tk.check_access("check_link_report_show", context, data_dict)

    if "id" in data_dict:
        report = (
            context["session"]
            .query(Report)
            .filter(Report.id == data_dict["id"])
            .one_or_none()
        )
    elif "resource_id" in data_dict:
        report = Report.by_resource_id(data_dict["resource_id"])
    elif "url" in data_dict:
        report = Report.by_url(data_dict["url"])
    else:
        raise tk.ValidationError(
            {"id": ["One of the following must be provided: id, resource_id, url"]}
        )

    if not report:
        raise tk.ObjectNotFound("Report not found")

    return report.dictize(context)


@action
@validate(schema.report_search)
def report_search(context, data_dict):
    tk.check_access("check_link_report_search", context, data_dict)
    q = context["session"].query(Report)

    if data_dict["free_only"] and data_dict["attached_only"]:
        raise tk.ValidationError(
            {
                "free_only": [
                    "Filters `attached_only` and `free_only` cannot be applied"
                    " simultaneously"
                ]
            }
        )

    if data_dict["free_only"]:
        q = q.filter(Report.resource_id.is_(None))

    if data_dict["attached_only"]:
        q = q.filter(Report.resource_id.isnot(None))

    if "exclude_state" in data_dict:
        q = q.filter(Report.state.notin_(data_dict["exclude_state"]))

    if "include_state" in data_dict:
        q = q.filter(Report.state.in_(data_dict["include_state"]))

    count = q.count()
    q = q.order_by(Report.last_status_change.desc())
    q = q.limit(data_dict["limit"]).offset(data_dict["offset"])

    return {
        "count": count,
        "results": [
            r.dictize(dict(context, include_resource=True, include_package=True))
            for r in q
        ],
    }


@action
@validate(schema.url_search)
def url_search(context, data_dict):
    #tk.check_access("check_link_url_search", context, data_dict)
    q = context["session"].query(Report)

    url = data_dict["url"]
    count = 0

    q = q.filter(Report.url == url )
    count = q.count()
    q = q.order_by(Report.last_status_change.desc())
    q = q.limit(1)

    return {
        "count": count,
        "results": [
            r.dictize(dict(context, include_resource=False, include_package=False))
            for r in q
        ],
    }

@action
@validate(schema.email_report)
def email_report(context, data_dict):

    q = context["session"].query(Report)

    count = 0

    q = q.filter(Report.state != 'available' )
    count = q.count()
    q = q.order_by(Report.last_available.desc())

    log.info( 'count={}'.format( count ) )

    body = ''
    skipped = 0

    for r in q:

        try:

            package_show = tk.get_action('package_show')
            if r.package_id:
                log.info( 'resource' )
                pid =  r.package_id
            else:
                log.info( 'application' )
                pid =  r.details['package_id']

            dataset = package_show( context, {'id': pid} )


            broken_age = r.last_checked - r.last_available

            body += "<h2 style='margin-bottom: 0;'>{name}</h2>\nDataset State: {dataset_state}\nBroken link: {url}\nLink State: {link_state}\nCode / Reason / Explanation: {code} / {reason} / {explanation}\nBroken for {broken_age}\nLast checked: {last_checked}\nLast Available: {last_available}\nDataset URL: {dataset_url}\n\n".format(
                name = dataset["title"],
                broken_age = "{days} days, {hours} hours".format( days=broken_age.days, hours=( broken_age.seconds // 3600 ) ),
                url = r.url,
                link_state = r.state,
                dataset_state = "Private" if dataset["private"] else "Published",
                last_checked = r.last_checked.strftime("%m/%d/%Y at %I:%M%p").lower(),
                last_available = r.last_available.strftime("%m/%d/%Y at %I:%M%p").lower(),
                dataset_url = h.url_for('{}.read'.format( dataset["type"] ), id=dataset["name"], _external=True ),
                code = r.details["code"],
                reason = r.details["reason"],
                explanation = r.details["explanation"],
             )
        except Exception as e: 
            print(e)
            # skip record if we don't have permission to access it, for instance if it is in the trash
            log.info( 'Skipped record {}'.format( r.id ) )
            skipped += 1
            pass


    subject = '{site_title} | Broken Link Report'.format( site_title = tk.config.get('ckan.site_title') )
    body_prefix =  \
        "<li>{0} unavailable resource{1} found.</li>".format(count, "s" if count != 1 else "" ) + \
        "<li><a href='{url}/ckan-admin/broken-links'>This report is also available in the TWDH CKAN Admin</a>.</li>".format( url=tk.config.get('ckan.site_url')   )

    email_to = tk.config.get('ckanext.check_link.email_to')

    if( email_to == None ):
        raise Exception("ckanext.check_link.email_to is not set, so I can't e-mail this report")
    else:
        mail_dict = {
            'recipient_email': email_to,
            'recipient_name': tk.config.get('ckan.site_title'),
            'subject': subject,
            'body': body,
            'body_html': render_template(
                f'check_link/emails/broken_link_report.html',
                subject = subject,
                prefix = body_prefix,
                message = body,
                site_title = tk.config.get('ckan.site_title'), 
                site_url = tk.url_for( 'home.index', _external=True )
            )

        }

    try:
        mailer.mail_recipient(**mail_dict)
    except (mailer.MailerException, socket.error):
        pass

@action
@validate(schema.report_delete)
def report_delete(context, data_dict):
    tk.check_access("check_link_report_delete", context, data_dict)
    sess = context["session"]

    report = tk.get_action("check_link_report_show")(context, data_dict)
    entity = sess.query(Report).filter(Report.id == report["id"]).one()

    sess.delete(entity)
    sess.commit()
    return entity.dictize(context)
