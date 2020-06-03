"""AppConfig for rapid response"""
from django.apps import AppConfig
from openedx.core.djangoapps.plugins.constants import (
    ProjectType,
    SettingsType,
    PluginSettings,
)


class RapidResponseAppConfig(AppConfig):
    """
    AppConfig for rapid response
    """
    name = "rapid_response_xblock"

    plugin_app = {
        PluginSettings.CONFIG: {
            ProjectType.LMS: {
                SettingsType.COMMON: {
                    PluginSettings.RELATIVE_PATH: 'settings'
                },
            }
        }
    }
