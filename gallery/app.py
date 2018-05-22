import configparser
import os

from gallery import handler


def application(environ, start_response):
    config_data = configparser.ConfigParser()
    config_data.read(os.environ.get('GALLERY_RC', '/etc/gallery.rc'))

    if 'REQUEST_URI' in environ and environ['REQUEST_URI'] == '/':
        start_response('301 MOVED PERMANENTLY',
                       [('Location', config_data.sections()[0] + '/')])
        return []

    multitenant_prefix = None
    if 'SCRIPT_NAME' in environ and environ['SCRIPT_NAME']:
        config_section = environ['SCRIPT_NAME']
    elif 'REQUEST_URI' in environ and environ['REQUEST_URI']:
        for prefix in config_data.sections():
            if environ['REQUEST_URI'].startswith(prefix):
                config_section = prefix
                multitenant_prefix = prefix
    else:
        config_section = '/'
    config = config_data[config_section]
    config['multitenant_prefix'] = multitenant_prefix

    return handler.application(environ, start_response, config)
