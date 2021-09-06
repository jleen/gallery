import argparse
import configparser
import os
import sys

from gallery import cache
from gallery import handler
from gallery import paths


def ignore_response(foo, bar):
    pass


def target_filename(rel_url, config, tuples):
    pseudo_url = paths.relurl_to_url(rel_url, config)
    target_path = paths.url_to_os(pseudo_url[len(config['browse_prefix']):])
    return os.path.join(config['target_prefix'], target_path)


def generate(generator, rel_url, filename, ctime, args, config, tuples):
    if (not force_regen(filename, args) and
            os.path.exists(filename) and ctime < cache.lmtime(filename)):
        return

    print('Generating ' + rel_url)

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    content = generator(None, ignore_response, paths.os_to_url(rel_url),
                        config, tuples)
    with open(filename, 'wb') as f:
        f.write(content[0])


def force_regen(filename, args):
    if args.regen_html:
        return filename.endswith('.html') or filename.endswith('/')
    else:
        return False


def hack_size(path, size):
    (base, extn) = os.path.splitext(path)
    return base + "_" + size + extn


def hack_extn(path, extn):
    base = os.path.splitext(path)[0]
    return base + extn


def gen_photo(rel_photo_url, size, ctime, args, config, tuples):
    target_photo = target_filename(rel_photo_url, config, tuples)
    rel_thumb_url = hack_size(rel_photo_url, size)
    target_thumb = hack_size(target_photo, size)
    generate(handler.photo, rel_thumb_url, target_thumb, ctime,
             args, config, tuples)


def staticgen():
    argparser = argparse.ArgumentParser('Generate a static gallery site')
    argparser.add_argument('--regen-html', action='store_true')
    args = argparser.parse_args()

    config_data = configparser.ConfigParser()
    config_data.read(os.environ.get('GALLERY_RC',
                                    os.path.expanduser('~/gallery.rc',)))
    config = config_data['gallery']

    # Accept settings in a more sensible form, and translate them into what
    # the legacy code expects to see.
    config['short_name'] = config['title']
    config['long_name'] = config['banner']
    config['apply_rotation'] = config.get('apply_rotation', 'True')
    config['ignore_client_cache'] = 'True'
    config['img_prefix'] = config['repository']
    config['cache_prefix'] = config['target']
    config['target_prefix'] = config['target']
    config['browse_prefix'] = config['url']

    tuples = paths.new_tuple_cache()

    target_css = target_filename('gallery.css', config, tuples)
    ctime_css = cache.lmtime(handler.GALLERY_CSS)
    generate(handler.css, 'gallery.css',
             target_css, ctime_css, args, config, tuples)

    for photodir, _, photos in os.walk(config['img_prefix']):
        dirtime = cache.lmtime(photodir)

        rel_url = paths.url_to_os(
                paths.abs_to_relurl(photodir, '', config, tuples))
        target_dir = target_filename(rel_url, config, tuples)
        index_file = os.path.join(target_dir, 'index.html')
        generate(handler.gallery, rel_url, index_file,
                 dirtime, args, config, tuples)

        preview = handler.find_preview(
                paths.abs_to_rel(photodir, config), config, tuples)
        preview_relurl = paths.rel_to_relurl(preview, '', config, tuples)
        gen_photo(paths.url_to_os(preview_relurl), '100',
                  dirtime, args, config, tuples)

        for photo in photos:
            if os.path.splitext(photo)[1] not in paths.IMG_EXTNS:
                continue

            photopath = os.path.join(photodir, photo)
            ctime = cache.lmtime(photopath)

            rel_photo_url = paths.url_to_os(
                    paths.abs_to_relurl(photopath, '', config, tuples))
            target_photo = target_filename(rel_photo_url, config, tuples)

            if not os.path.exists(target_photo):
                os.link(photopath, target_photo)

            gen_photo(rel_photo_url, '200', ctime, args, config, tuples)
            gen_photo(rel_photo_url, '700x500', ctime, args, config, tuples)

            rel_page_url = hack_extn(rel_photo_url, '.html')
            target_page = hack_extn(target_photo, '.html')
            generate(handler.photopage, rel_page_url, target_page,
                     ctime, args, config, tuples)
