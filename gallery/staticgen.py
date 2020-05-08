import configparser
import os
import sys

from gallery import handler
from gallery import paths


def ignore_response(foo, bar):
    pass


def target_filename(rel_url, config, tuples):
    pseudo_url = paths.rel_to_url(rel_url, config, tuples)
    target_path = paths.url_to_os(pseudo_url[len(config['browse_prefix']):])
    return os.path.join(config['target_prefix'], target_path)

def generate(generator, rel_url, filename, config, tuples):
    print("Generating " + filename)

    content = generator(None, ignore_response, rel_url, config, tuples)
    with open(filename, 'wb') as f:
        f.write(content[0])

def hack_extn(path, extn):
    base = os.path.splitext(path)[0]
    return base + extn

def staticgen():
    config_data = configparser.ConfigParser()
    config_data.read(os.environ.get('GALLERY_RC', 'gallery.rc'))
    config = config_data['gallery']
    tuples = paths.new_tuple_cache()

    for photodir, _, photos in os.walk(config['img_prefix']):
        rel_url = paths.abs_to_rel(photodir, config)
        target_dir = target_filename(rel_url, config, tuples)
        os.makedirs(target_dir, exist_ok=True)
        index_file = os.path.join(target_dir, 'index.html')
        generate(handler.gallery, rel_url, index_file, config, tuples)

        for photo in photos:
            photopath = os.path.join(photodir, photo)

            rel_photo_url = paths.abs_to_rel(photopath, config)
            target_photo = target_filename(rel_photo_url, config, tuples)
            generate(handler.photo, rel_photo_url, target_photo,
                     config, tuples)

            rel_photo_url = paths.abs_to_rel(photopath, config)
            target_photo = target_filename(rel_photo_url, config, tuples)
            generate(handler.photo, rel_photo_url, target_photo,
                     config, tuples)

            rel_thumb_url = hack_extn(rel_photo_url, '_200.jpg')
            target_thumb = hack_extn(target_photo, '_200.jpg')
            generate(handler.photo, rel_thumb_url, target_thumb,
                     config, tuples)
            rel_page_url = hack_extn(rel_photo_url, '.html')
            target_page = hack_extn(target_photo, '.html')
            generate(handler.photopage, rel_page_url, target_page,
                     config, tuples)
