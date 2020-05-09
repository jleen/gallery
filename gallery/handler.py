# vim:sw=4:ts=4

import os
import time

from jinja2 import Environment, PackageLoader

from gallery import cache, exif, paths, whatsnew

SMALL_SIZE = "600"
MED_SIZE = "1024"
BIG_SIZE = "original"
THUMB_SIZE = "200"
PREVIEW_SIZE = "100"

GALLERY_CSS = os.path.join(os.path.dirname(__file__),
                           "static", "gallery.css")

THUMB_SIZE_INT = int(THUMB_SIZE)
PREVIEW_SIZE_INT = int(PREVIEW_SIZE)

jenv = Environment(loader=PackageLoader('gallery', 'templates'))


def application(environ, start_response, config):
    try:
        os.umask(0o002)

        tuple_cache = paths.new_tuple_cache()
        reqpath = environ.get('PATH_INFO', '')
        
        if config['multitenant_prefix']:
            reqpath = reqpath[len(config['multitenant_prefix']) + 1:]

        extn = os.path.splitext(reqpath)[1]
        if os.path.split(reqpath)[1] == 'index.html':
            return gallery(
                    environ, start_response, reqpath, config, tuple_cache)
        elif os.path.split(reqpath)[1] == 'whatsnew.html':
            return whatsnew.spew_recent_whats_new(
                    environ, start_response, config, tuple_cache, jenv)
        elif os.path.split(reqpath)[1] == 'whatsnew_all.html':
            return whatsnew.spew_all_whats_new(
                    environ, start_response, config, tuple_cache, jenv)
        elif os.path.split(reqpath)[1] == 'whatsnew.xml':
            return whatsnew.spew_whats_new_rss(
                    environ, start_response, config, tuple_cache, jenv)
        elif os.path.split(reqpath)[1] == 'gallery.css':
            return css(environ, start_response, config)
        elif extn.lower() in paths.IMG_EXTNS:
            return photo(environ, start_response, reqpath, config, tuple_cache)
        elif extn == '.html':
            return photopage(
                    environ, start_response, reqpath, config, tuple_cache)
        elif len(extn) < 1:
            return gallery(
                    environ, start_response, reqpath, config, tuple_cache)
        else:
            return send_404(start_response)
    except cache.NotModifiedException:
        return send_304(start_response)
    except paths.UnableToDisambiguateException:
        return send_404(start_response)


def send_304(start_response):
    start_response('304 NOT MODIFIED', [('Content-Type', 'text/plain')])
    return []


def send_404(start_response):
    start_response('404 NOT FOUND', [('Content-Type', 'text/plain')])
    return [b'Not Found']


def photopage(environ, start_response, url, config, tuples):
    (url_dir, base, extn) = paths.split_path_ext(url)
    rel_dir = paths.url_to_rel(url_dir, config, tuples)
    abs_dir = paths.rel_to_abs(rel_dir, config)
    abs_image = paths.url_to_abs(
            os.path.join(url_dir, base),
            config, tuples, infer_suffix=1)
    cache_time = cache.max_ctime_for_files([abs_image, abs_dir])
    server_date = cache.check_client_cache(environ, cache_time, config)

    abs_info = os.path.splitext(abs_image)[0] + '.info'
    description = ''
    if os.path.exists(abs_info):
        with open(abs_info) as info_file:
            for line in info_file:
                if line.startswith('Description: '):
                    description = line[len('Description: '):]

    a = {
        'framed_img_url': paths.abs_to_relurl(
                abs_image, rel_dir, config, tuples, "700x500"),
        'full_img_url': paths.abs_to_relurl(
                abs_image, rel_dir, config, tuples),
        'gallery_title': config['long_name']
    }
    photo_title = paths.get_displayname_for_file(abs_image, tuples)
    bread_title = photo_title
    if len(bread_title) == 0:
        bread_title = '(untitled)'
    a['photo_title'] = photo_title
    a['bread_title'] = bread_title
    a['description'] = description
    show_exif = config.getboolean('show_exif', fallback=False)
    if show_exif:
        a['exifdata'] = exif.exif_tags(abs_image).items()
    else:
        a['exifdata'] = None
    (prev, nxt) = paths.get_nearby_for_file(abs_image, tuples)
    if prev:
        prev = paths.abs_to_relurl(
                prev, rel_dir, config, tuples, ext='html')
    if nxt:
        nxt = paths.abs_to_relurl(
                nxt, rel_dir, config, tuples, ext='html')
    a['prev'] = prev
    a['next'] = nxt

    # A set of breadcrumbs that link back to the containing directory.
    if os.path.islink(abs_image):
        img_dest_path = os.path.realpath(abs_image)
        dir_dest_path = os.path.dirname(img_dest_path)
        # Hacky way to prune off the leading path.  The +1 gets rid of the
        # trailing / to make the path relative.  Also, I need to use realpath
        # to canonicalize both sides of this heinous equation.
        pruned_dest = dir_dest_path[len(os.path.realpath(
                config['img_prefix'])) + 1:]
        leaf = os.path.basename(dir_dest_path)
        a['from_caption'] = paths.format_for_display(leaf)
        a['from_url'] = os.path.join(config['browse_prefix'], pruned_dest)

    breadcrumbs = paths.breadcrumbs_for_path(
            "./" + rel_dir, config, tuples)
    a['breadcrumbs'] = breadcrumbs

    template = jenv.get_template('photopage.html.jj')
    a['browse_prefix'] = config['browse_prefix']
    if 'footer_message' in config:
        a['footer_message'] = config['footer_message']
    else:
        a['footer_message'] = None
    start_response('200 OK', cache.add_cache_headers(
            [('Content-Type', 'text/html; charset="UTF-8"')], server_date))
    return [template.render(a).encode('utf-8')]


def css(environ, start_response, config):
    ctime = cache.lctime(GALLERY_CSS)
    server_date = cache.check_client_cache(environ, ctime, config)
    start_response('200 OK', cache.add_cache_headers(
            [('Content-Type', 'text/css')], server_date))
    return [spew_file(GALLERY_CSS)]


def photo(environ, start_response, url, config, tuples):
    size_index = url.rfind('_')
    ext_index = url.rfind('.')
    base = url[:ext_index]
    size = BIG_SIZE
    ext = url[ext_index + 1:]
    try:
        # Attempt a disambiguation to see if the file exists.
        paths.url_to_rel(base + '.' + ext, config, tuples)
    except paths.UnableToDisambiguateException:
        # If it fails, then try it with the underscore as a size separator.
        base = url[:size_index]
        size = url[size_index + 1:ext_index]
    rel_image = paths.url_to_rel(
            base + '.' + ext, config, tuples)
    image_ctime = cache.lctime(
            paths.rel_to_abs(rel_image, config))
    server_date = cache.check_client_cache(environ, image_ctime, config)
    allow_original = config.getboolean('allow_original', fallback=True)
    if size == "original" and not allow_original:
        size = "full"
    start_response('200 OK', cache.add_cache_headers(
            [('Content-Type', 'image/jpeg')], server_date))
    if size == "original":
        return [spew_file(paths.rel_to_abs(rel_image, config))]
    else:
        return [spew_photo(rel_image, size, config)]


def spew_photo(rel, size, config):
    abs_cachedir = os.path.join(config['cache_prefix'], size)
    abs_cachefile = os.path.join(abs_cachedir, rel)
    abs_raw_image = paths.rel_to_abs(rel, config)
    if cache.is_cached(abs_raw_image, abs_cachefile, config):
        return spew_file(abs_cachefile)
    else:
        return cache.cache_img(rel, size, config)


def spew_file(abs_path):
    # TODO(jleen): set content length to avoid the evil chunked transfer coding
    # req.set_content_length(os.stat(abs)[stat.ST_SIZE])
    with open(abs_path, 'rb') as f:
        return f.read()


def first_image_in_dir(rel_dir, config, tuples):
    abs_dir = paths.rel_to_abs(rel_dir, config)
    items = paths.get_directory_tuples(abs_dir, tuples)
    for item in items:
        (scratch, base, ext) = paths.split_path_ext(
                item['filename'])
        if ext.lower() in paths.IMG_EXTNS:
            return item['filename']

    # Got this far and didn't find an image.  Let's look in subdirs next.
    for dir_item in items:
        dir_fname = dir_item['filename']
        if os.path.isdir(os.path.join(abs_dir, dir_fname)):
            rel_subdir = os.path.join(rel_dir, dir_fname)
            recurse = first_image_in_dir(rel_subdir, config, tuples)
            return os.path.join(dir_fname, recurse)


def ensure_trailing_slash_and_check_needs_refresh(environ, start_response):
    # Passenger provides REQUEST_URI.  Green Unicorn does not, but it does
    # provide RAW_URI, which seems to be just as good.  As a fallback, we'll
    # use PATH_INFO and pray.
    path = environ.get('REQUEST_URI',
                       environ.get('RAW_URI', environ.get('PATH_INFO', '')))
    if not path.endswith('/'):
        start_response('301 MOVED PERMANENTLY', [('Location', path + '/')])
        return True
    return False


def find_preview(rel_dir, config, tuples):
    rel_preview = None

    abs_dir = paths.rel_to_abs(rel_dir, config)
    for fn in os.listdir(abs_dir):
        if fn == ".preview.jpeg" or fn.lower() == "preview.jpg":
            rel_preview = os.path.join(rel_dir, fn)
    if not rel_preview:
        rel_preview = first_image_in_dir(rel_dir, config, tuples)
        if rel_preview:
            rel_preview = os.path.join(rel_dir, rel_preview)

    return rel_preview


def gallery(environ, start_response, url_dir, config, tuples):
    if environ and ensure_trailing_slash_and_check_needs_refresh(
            environ, start_response):
        return []

    if url_dir.startswith('/home'):
        url_dir = '/'
    if not url_dir.endswith('/'):
        url_dir += '/'
    rel_dir = paths.url_to_rel(url_dir, config, tuples)
    abs_dir = paths.rel_to_abs(rel_dir, config)
    items = paths.get_directory_tuples(abs_dir, tuples)

    abs_images = []
    for item in items:
        fname = item['filename']
        abs_images.append(os.path.join(abs_dir, fname))

    server_date = 0
    if environ:
        server_date = cache.check_client_cache(
                environ, cache.max_ctime_for_files([abs_dir]), config)

    image_records = []
    for item in items:
        fname = item['filename']
        displayname = item['displayname']
        (scratch, base, ext) = paths.split_path_ext(fname)
        if ext.lower() not in paths.IMG_EXTNS:
            continue

        rel_image = os.path.join(rel_dir, fname)
        url_medium = paths.rel_to_relurl(
                rel_image, url_dir, config, tuples, ext='html')
        url_big = paths.rel_to_relurl(
                rel_image, url_dir, config, tuples, size=BIG_SIZE)
        url_thumb = paths.rel_to_relurl(
                rel_image, url_dir, config, tuples, size=THUMB_SIZE)
        caption = displayname
        (width, height) = cache.img_size(
                rel_image, THUMB_SIZE_INT, config)
        rec = (url_medium, url_big, url_thumb, caption, width, height)
        image_records.append(rec)

    index_html = None
    rel_index = os.path.join(rel_dir, 'index.html')
    abs_index = paths.rel_to_abs(rel_index, config)
    if os.path.exists(abs_index):
        fh = open(abs_index, 'r', encoding='utf-8')
        index_html = fh.read()
        fh.close()

    subdir_records = []
    for item in items:
        fname = item['filename']
        displayname = item['displayname']
        rel_subdir = os.path.join(rel_dir, fname)
        if fname.startswith('_'):
            continue
        if not os.path.isdir(paths.rel_to_abs(
                rel_subdir, config)):
            continue
        url_subdir = paths.rel_to_relurl(
                rel_subdir, url_dir[:-1], config, tuples, trailing_slash=1)
        caption = displayname
        rel_preview = find_preview(rel_subdir, config, tuples)
        preview = None
        width = 0
        height = 0
        if rel_preview:
            url_preview = paths.rel_to_relurl(
                    rel_preview, url_dir[:-1], config, tuples, PREVIEW_SIZE)
            (width, height) = cache.img_size(
                    rel_preview, PREVIEW_SIZE_INT, config)

        subdir_records.append(
                (url_subdir, caption, url_preview, width, height))

    breadcrumbs = paths.breadcrumbs_for_path(
            './' + rel_dir[:-1], config, tuples)

    a = {}
    template = jenv.get_template('browse.html.jj')
    leafdir = os.path.split(rel_dir[:-1])[1]
    wn_updates = None
    if len(leafdir) == 0:
        leafdir = config['short_name']
        # Set up the What's New link for the root.
        wn_txt_path = os.path.join(config['img_prefix'], "whatsnew.txt")
        if os.path.exists(wn_txt_path):
            wn_src = whatsnew.whatsnew_src_file(config)
            wn_updates = whatsnew.read_update_entries(
                    wn_src, config, tuples)
    if wn_updates:
        wn_date = wn_updates[0]['date']
        wn_ctime = time.strftime('%B %d', time.strptime(wn_date, '%m-%d-%Y'))
        a['whatsnew_name'] = "What's New (updated " + wn_ctime + ")"
        a['whatsnew_url'] = os.path.join(
                config['browse_prefix'], "whatsnew.html")
        a['whatsnew_rss'] = os.path.join(
                config['browse_prefix'], "whatsnew.xml")
    else:
        a['whatsnew_name'] = None
        a['whatsnew_url'] = None
        a['whatsnew_rss'] = None

    a['title'] = config['long_name']
    a['breadcrumbs'] = breadcrumbs
    a['thisdir'] = paths.format_for_display(leafdir)
    a['imgurls'] = image_records
    a['subdirs'] = subdir_records
    a['index_html'] = index_html
    a['browse_prefix'] = config['browse_prefix']
    if 'footer_message' in config:
        a['footer_message'] = config['footer_message']
    else:
        a['footer_message'] = None

    start_response('200 OK', cache.add_cache_headers(
            [('Content-Type', 'text/html; charset="UTF-8"')], server_date))
    return [template.render(a).encode('utf-8')]
