from __future__ import annotations
from typing import Any
from itertools import islice
from check_link import Link, check_all

import ckan.plugins.toolkit as tk
from ckan.logic import validate
from ckan.lib.search.query import solr_literal

from ckanext.toolbelt.decorators import Collector

from .. import schema


action, get_actions = Collector("check_link").split()


@action
@validate(schema.url_check)
def url_check(context, data_dict):
    tk.check_access("check_link_url_check", context, data_dict)

    try:
        result = check_all(map(Link, data_dict["url"]))
    except ValueError:
        raise tk.ValidationError({"url": ["Must be a valid URL"]})

    reports = [
        {
            "url": link.link,
            "state": link.state.name,
            "code": link.code,
            "reason": link.reason,
            "explanation": link.details,
        }
        for link in result
    ]

    if data_dict["save"]:
        _save_reports(context, reports)

    return reports


@action
@validate(schema.resource_check)
def resource_check(context, data_dict):
    tk.check_access("check_link_resource_check", context, data_dict)
    resource = tk.get_action("resource_show")(context, data_dict)

    result = tk.get_action("check_link_url_check")(
        context, {"url": [resource["url"]]}
    )

    report = dict(result[0], resource_id=resource["id"], package_id=resource["package_id"])

    if data_dict["save"]:
        _save_reports(context, [report])

    return report


@action
@validate(schema.package_check)
def package_check(context, data_dict):
    tk.check_access("check_link_package_check", context, data_dict)
    return _search_check(
        context,
        "res_url:* (id:{0} OR name:{0})".format(solr_literal(data_dict["id"])),
        data_dict,
    )


@action
@validate(schema.organization_check)
def organization_check(context, data_dict):
    tk.check_access("check_link_organization_check", context, data_dict)

    return _search_check(
        context,
        "res_url:* owner_org:{}".format(solr_literal(data_dict["id"])),
        data_dict,
    )


@action
@validate(schema.group_check)
def group_check(context, data_dict):
    tk.check_access("check_link_group_check", context, data_dict)

    return _search_check(
        context, "res_url:* groups:{}".format(solr_literal(data_dict["id"])), data_dict
    )


@action
@validate(schema.user_check)
def user_check(context, data_dict):
    tk.check_access("check_link_user_check", context, data_dict)

    return _search_check(
        context,
        "res_url:* creator_user_id:{}".format(solr_literal(data_dict["id"])),
        data_dict,
    )


@action
@validate(schema.search_check)
def search_check(context, data_dict):
    tk.check_access("check_link_search_check", context, data_dict)

    return _search_check(context, data_dict["fq"], data_dict)


def _search_check(context, fq: str, data_dict: dict[str, Any]):
    params = {
        "fq": fq,
        "start": data_dict["start"],
        "include_drafts": data_dict["include_drafts"],
        "include_deleted": data_dict["include_deleted"],
        "include_private": data_dict["include_private"],
    }

    pairs = [
        ({"resource_id": res["id"], "package_id": pkg["id"]}, res["url"])
        for pkg in islice(_iterate_search(context, params), data_dict["rows"])
        for res in pkg["resources"]
    ]
    if not pairs:
        return []
    patches, urls = zip(*pairs)

    result = tk.get_action("check_link_url_check")(
        context, {"url": urls}
    )

    reports = [dict(report, **patch) for patch, report in zip(patches, result)]
    if data_dict["save"]:
        _save_reports(context, reports)

    return reports


def _iterate_search(context, params: dict[str, Any]):
    params.setdefault("start", 0)

    while True:
        pack = tk.get_action("package_search")(context.copy(), params)
        if not pack["results"]:
            return

        yield from pack["results"]

        params["start"] += len(pack["results"])


def _save_reports(context, reports):
        save = tk.get_action("check_link_report_save")
        for report in reports:
            save(context.copy(), report)
