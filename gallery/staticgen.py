import configparser
import os
import sys

from gallery import handler
from gallery import paths


def ignore_response(foo, bar):
    pass


def staticgen():
    config_data= configparser.ConfigParser()
    config_data.read(os.environ.get('GALLERY_RC', 'gallery.rc'))
    config = config_data['gallery']

    tuples = paths.new_tuple_cache()

    url = sys.argv[2]

    if sys.argv[1] == 'gallery':
        resp = handler.gallery(None, ignore_response, url, config, tuples)
    elif sys.argv[1] == 'photo':
        resp = handler.photo(None, ignore_response, url, config, tuples)
    elif sys.argv[1] == 'photopage':
        resp = handler.photopage(None, ignore_response, url, config, tuples)

    with open(sys.argv[3], 'wb') as f:
        f.write(resp[0])
