import configparser
import os

from gallery import handler


def application(environ, start_response):
    config_data = configparser.ConfigParser()
    config_data.read(os.environ.get('GALLERY_RC', '/etc/gallery.rc'))
    if 'SCRIPT_NAME' in environ and environ['SCRIPT_NAME']:
        config_section = environ['SCRIPT_NAME']
    else:
        config_section = '/'
    config = config_data[config_section]
    return handler.application(environ, start_response, config)
