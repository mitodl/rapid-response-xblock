"""Settings to provide to edX"""


def plugin_settings(settings):
    """
    Populate settings
    """
    settings.TRACKING_BACKENDS['rapid_response'] = {
        'ENGINE': 'rapid_response_xblock.logger.LoggerBackend',
        'OPTIONS': {
            'name': 'rapid_response',
        }
    }
