import configparser
import os

from gallery import handler

def application(environ, start_response):
    config_data = configparser.ConfigParser()
    config_data.read(os.environ.get('GALLERY_RC', '/etc/gallery.rc'))

    multitenant_prefix = ''

    if 'SCRIPT_NAME' in environ and environ['SCRIPT_NAME']:
        # We're being invoked as a standalone script.  Just look up the config.
        config_section = environ['SCRIPT_NAME']
    elif 'REQUEST_URI' in environ and environ['REQUEST_URI']:
        # We're in multitenant mode. Get the config from the path.
        config_section = None
        for prefix in config_data.sections():
            if environ['REQUEST_URI'].startswith(prefix):
                config_section = prefix
                multitenant_prefix = prefix
        if not config_section:
            # Default root tenant. No prefix.
            config_section = '/gallery'
            multitenant_prefix = '/'
    else:
        # We're a standalone script at the root.
        config_section = '/'
    config = config_data[config_section]
    config['multitenant_prefix'] = multitenant_prefix

    return handler.application(environ, start_response, config)
