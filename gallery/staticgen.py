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
    print('Generating ' + rel_url)

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    content = generator(None, ignore_response, paths.os_to_url(rel_url),
                        config, tuples)
    with open(filename, 'wb') as f:
        f.write(content[0])


def hack_size(path, size):
    (base, extn) = os.path.splitext(path)
    return base + "_" + size + extn


def hack_extn(path, extn):
    base = os.path.splitext(path)[0]
    return base + extn


def gen_photo(rel_photo_url, size, config, tuples):
    target_photo = target_filename(rel_photo_url, config, tuples)
    rel_thumb_url = hack_size(rel_photo_url, size)
    target_thumb = hack_size(target_photo, size)
    generate(handler.photo, rel_thumb_url, target_thumb,
             config, tuples)


def staticgen():
    config_data = configparser.ConfigParser()
    config_data.read(os.environ.get('GALLERY_RC', 'gallery.rc'))
    config = config_data['gallery']
    tuples = paths.new_tuple_cache()

    for photodir, _, photos in os.walk(config['img_prefix']):
        rel_url = paths.url_to_os(
                paths.abs_to_relurl(photodir, '', config, tuples))
        target_dir = target_filename(rel_url, config, tuples)
        index_file = os.path.join(target_dir, 'index.html')
        generate(handler.gallery, rel_url, index_file, config, tuples)

        preview = handler.find_preview(
                paths.abs_to_rel(photodir, config), config, tuples)
        preview_relurl = paths.rel_to_relurl(preview, '', config, tuples)
        gen_photo(paths.url_to_os(preview_relurl), '100', config, tuples)

        for photo in photos:
            photopath = os.path.join(photodir, photo)

            rel_photo_url = paths.url_to_os(
                    paths.abs_to_relurl(photopath, '', config, tuples))
            target_photo = target_filename(rel_photo_url, config, tuples)
            generate(handler.photo, rel_photo_url, target_photo, config, tuples)

            gen_photo(rel_photo_url, '200', config, tuples)
            gen_photo(rel_photo_url, '700x500', config, tuples)

            rel_page_url = hack_extn(rel_photo_url, '.html')
            target_page = hack_extn(target_photo, '.html')
            generate(handler.photopage, rel_page_url, target_page,
                     config, tuples)
