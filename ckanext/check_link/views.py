from __future__ import annotations
from typing import Any, Optional

import ckan.authz as authz
import ckan.plugins.toolkit as tk
from ckan.lib.helpers import Page
from flask import Blueprint

CONFIG_BASE_TEMPLATE = "ckanext.check_link.report.base_template"
CONFIG_REPORT_URL = "ckanext.check_link.report.url"


DEFAULT_BASE_TEMPLATE = "check_link/base_admin.html"
DEFAULT_REPORT_URL = "/check-link/report/global"


bp = Blueprint("check_link", __name__)


def get_blueprints():
    report_url = tk.config.get(CONFIG_REPORT_URL, DEFAULT_REPORT_URL)
    if report_url:
        bp.add_url_rule(report_url, view_func=report)

    return [bp]


def report():
    if not authz.is_authorized_boolean(
        "check_link_view_report_page", {"user": tk.g.user}, {}
    ):
        return tk.abort(403)

    try:
        page = max(1, tk.asint(tk.request.args.get("page", 1)))
    except ValueError:
        page = 1

    per_page = 20
    reports = tk.get_action("check_link_report_search")(
        {},
        {
            "limit": per_page,
            "offset": per_page * page - per_page,
            "attached_only": True,
            "exclude_state": ["available"],
        },
    )

    def pager_url(*args: Any, **kwargs: Any):
        return tk.url_for("check_link.report", **kwargs)

    base_template = tk.config.get(CONFIG_BASE_TEMPLATE, DEFAULT_BASE_TEMPLATE)
    return tk.render(
        "check_link/report.html",
        {
            "base_template": base_template,
            "page": Page(
                reports["results"],
                url=pager_url,
                page=page,
                item_count=reports["count"],
                items_per_page=per_page,
                presliced_list=True,
            ),
        },
    )

