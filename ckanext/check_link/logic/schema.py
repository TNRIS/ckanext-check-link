from ckan.logic.schema import validator_args


@validator_args
def url_check(
    not_missing,
    json_list_or_string,
    default,
    convert_to_json_if_string,
    boolean_validator,
):
    return {
        "url": [not_missing, json_list_or_string],
        "save": [default(False), boolean_validator],
        "clear_available": [default(False), boolean_validator],
        "skip_invalid": [default(False), boolean_validator],
        "link_patch": [default("{}"), convert_to_json_if_string],
    }


@validator_args
def resource_check(
    not_missing,
    resource_id_exists,
    boolean_validator,
    default,
    convert_to_json_if_string,
):
    return {
        "id": [not_missing, resource_id_exists],
        "save": [default(False), boolean_validator],
        "clear_available": [default(False), boolean_validator],
        "link_patch": [default("{}"), convert_to_json_if_string],
    }


@validator_args
def base_search_check(
    boolean_validator, default, int_validator, convert_to_json_if_string
):
    return {
        "save": [default(False), boolean_validator],
        "clear_available": [default(False), boolean_validator],
        "skip_invalid": [default(False), boolean_validator],
        "include_drafts": [default(False), boolean_validator],
        # "include_deleted": [default(False), boolean_validator],
        "include_private": [default(False), boolean_validator],
        "start": [default(0), int_validator],
        "rows": [default(10), int_validator],
        "link_patch": [default("{}"), convert_to_json_if_string],
    }


@validator_args
def package_check(not_missing, package_id_or_name_exists):
    return dict(base_search_check(), id=[not_missing, package_id_or_name_exists])


@validator_args
def organization_check(not_missing, convert_group_name_or_id_to_id):
    return dict(base_search_check(), id=[not_missing, convert_group_name_or_id_to_id])


@validator_args
def group_check(not_missing, group_id_or_name_exists):
    return dict(base_search_check(), id=[not_missing, group_id_or_name_exists])


@validator_args
def user_check(not_missing, convert_user_name_or_id_to_id):
    return dict(base_search_check(), id=[not_missing, convert_user_name_or_id_to_id])


@validator_args
def search_check(unicode_safe, default):
    return dict(base_search_check(), fq=[default("*:*"), unicode_safe])


@validator_args
def report_save(
    unicode_safe,
    resource_id_exists,
    ignore_missing,
    not_missing,
    default,
    convert_to_json_if_string,
):
    return {
        "id": [ignore_missing, unicode_safe],
        "url": [not_missing, unicode_safe],
        "state": [not_missing, unicode_safe],
        "resource_id": [ignore_missing, resource_id_exists],
        "details": [default("{}"), convert_to_json_if_string],
    }


@validator_args
def report_show(unicode_safe, ignore_missing, resource_id_exists):
    return {
        "id": [ignore_missing, unicode_safe],
        "url": [ignore_missing, unicode_safe],
        "resource_id": [ignore_missing, resource_id_exists],
    }


@validator_args
def report_search(
    ignore_empty, default, int_validator, boolean_validator, json_list_or_string
):
    return {
        "limit": [default(10), int_validator],
        "offset": [default(0), int_validator],
        "exclude_state": [ignore_empty, json_list_or_string],
        "include_state": [ignore_empty, json_list_or_string],
        "attached_only": [default(False), boolean_validator],
        "free_only": [default(False), boolean_validator],
    }


@validator_args
def url_search(
    not_missing, unicode_safe
):
    return {
        "url": [not_missing, unicode_safe]
    }


@validator_args
def report_delete(unicode_safe, not_missing):
    return report_show()
