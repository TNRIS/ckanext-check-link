from __future__ import annotations

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from . import cli, views
from .logic import action, auth


def get_package_title(package_id: str) -> str:
    """Return the title of the package with the given ID"""
    package = toolkit.get_action("package_show")({}, {"id": package_id})
    return package["title"]

class CheckLinkPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IBlueprint)
    plugins.implements(plugins.IClick)
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("assets", "check_link")

    # IActions
    def get_actions(self):
        return action.get_actions()

    # IAuthFunctions
    def get_auth_functions(self):
        return auth.get_auth_functions()

    # IBlueprint
    def get_blueprint(self):
        return [views.report_bp]
        #return views.get_blueprints()

    # IClick
    def get_commands(self):
        return cli.get_commands()

    # ITemplateHelpers

    def get_helpers(self):
            """Register twdh helper functions"""

            return {
                'get_package_title': get_package_title,
            }
    
