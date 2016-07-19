import configparser

from gallery import handler

def application(environ, start_response):
    config_data = configparser.ConfigParser()
    config_data.read('/etc/gallery.rc')
    config = config_data[environ['SCRIPT_NAME']]
    return handler.application(environ, start_response, config)
