from __future__ import annotations

import ckan.plugins.toolkit as tk
from ckan import authz

from ckanext.toolbelt.decorators import Collector

CONFIG_ALLOW_USER = "ckanext.check_link.user_can_check_url"
DEFAULT_ALLOW_USER = False

auth, get_auth_functions = Collector("check_link").split()


@auth
def url_check(context, data_dict):
    allow_user_checks = tk.asbool(
        tk.config.get(
            CONFIG_ALLOW_USER,
            DEFAULT_ALLOW_USER,
        )
    )
    return {"success": allow_user_checks and not authz.auth_is_anon_user(context)}


@auth
def resource_check(context, data_dict):
    return authz.is_authorized("resource_show", context, data_dict)


@auth
def package_check(context, data_dict):
    return authz.is_authorized("package_show", context, data_dict)


@auth
def organization_check(context, data_dict):
    return authz.is_authorized("organization_show", context, data_dict)


@auth
def group_check(context, data_dict):
    return authz.is_authorized("group_show", context, data_dict)


@auth
def user_check(context, data_dict):
    return authz.is_authorized("user_show", context, data_dict)


@auth
def search_check(context, data_dict):
    return authz.is_authorized("package_search", context, data_dict)


@auth
def application_check(context, data_dict):
    return authz.is_authorized("package_search", context, data_dict)


@auth
def report_save(context, data_dict):
    return authz.is_authorized("sysadmin", context, data_dict)


@auth
def report_show(context, data_dict):
    return authz.is_authorized("sysadmin", context, data_dict)


@auth
def report_search(context, data_dict):
    return authz.is_authorized("sysadmin", context, data_dict)


@auth
def url_search(context, data_dict):
    #return authz.is_authorized("sysadmin", context, data_dict)
    return True;


@auth
def report_delete(context, data_dict):
    return authz.is_authorized("sysadmin", context, data_dict)


@auth
def view_report_page(context, data_dict):
    return authz.is_authorized("sysadmin", context, data_dict)
