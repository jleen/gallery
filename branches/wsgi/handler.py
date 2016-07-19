# vim:sw=4:ts=4

import os
import string
from StringIO import StringIO
import time
import traceback

import stat

from mod_python import apache

small_size = "600"
med_size = "1024"
big_size = "original"
thumb_size = "200"
preview_size = "100"

thumb_size_int = string.atoi(thumb_size)
preview_size_int = string.atoi(preview_size)

preload_modules = [ 'cache', 'paths', 'whatsnew' ]

def application(req, config):
    import_modules(config)
    try:
        os.umask(0002)

        tuple_cache = config['mod.paths'].new_tuple_cache()
        reqpath = os.path.split(req.filename)[1] + req.path_info

        extn = os.path.splitext(reqpath)[1]
        if os.path.split(reqpath)[1] == 'index.html':
            return gallery(req, reqpath, config, tuple_cache)
        elif os.path.split(reqpath)[1] == 'whatsnew.html':
            return config['mod.whatsnew'].spew_recent_whats_new(
                    req, config, tuple_cache,
                    import_one_module('templates.whatsnewpage', config))
        elif os.path.split(reqpath)[1] == 'whatsnew_all.html':
            return config['mod.whatsnew'].spew_all_whats_new(
                    req, config, tuple_cache,
                    import_one_module('templates.whatsnewpage', config))
        elif os.path.split(reqpath)[1] == 'whatsnew.xml':
            return config['mod.whatsnew'].spew_whats_new_rss(
                    req, config, tuple_cache,
                    import_one_module('templates.whatsnewrss', config))
        elif extn.lower() in config['mod.paths'].img_extns:
            return photo(req, reqpath, config, tuple_cache)
        elif extn == '.html':
            return photopage(req, reqpath, config, tuple_cache)
        elif len(extn) < 1:
            return gallery(req, reqpath, config, tuple_cache)
        else: send_404(req)
    except config['mod.paths'].UnableToDisambiguateException: send_404(req)
        
def import_one_module(modname, config):
    return apache.import_module(config['namespace'] + '.' + modname)

def import_modules(config):
    for modname in preload_modules:
        the_module = import_one_module(modname, config)
        config['mod.' + modname] = the_module

def send_404(req):
    raise apache.SERVER_RETURN, apache.HTTP_NOT_FOUND

def photopage(req, url, config, tuples):
    (url_dir, base, extn) = config['mod.paths'].split_path_ext(url)
    rel_dir = config['mod.paths'].url_to_rel(url_dir, config, tuples)
    abs_dir = config['mod.paths'].rel_to_abs(rel_dir, config)
    abs_image = config['mod.paths'].url_to_abs(
            os.path.join(url_dir, base),
            config, tuples, infer_suffix = 1)
    cache_time = config['mod.cache'].max_ctime_for_files(
            [abs_image, abs_dir, config['mod.cache'].scriptdir(
                'templates/photopage.tmpl')])
    config['mod.cache'].check_client_cache(
            req, 'text/html; charset="UTF-8"', cache_time, config)

    abs_info = os.path.splitext(abs_image)[0] + '.info'
    description = ''
    if os.path.exists(abs_info):
        for line in file(abs_info):
            if line.startswith('Description: '):
                description = line[len('Description: '):]

    a = {}
    a['framed_img_url'] = config['mod.paths'].abs_to_url(
            abs_image, config, tuples, "700x500")
    a['full_img_url'] = config['mod.paths'].abs_to_url(
            abs_image, config, tuples)
    a['gallery_title'] =  config['long_name']
    photo_title = config['mod.paths'].get_displayname_for_file(
            abs_image, config, tuples)
    bread_title = photo_title
    if len(bread_title) == 0: bread_title = '(untitled)'
    a['photo_title'] = photo_title
    a['bread_title'] = bread_title
    a['description'] = description
    show_exif = config.get('show_exif', 0)
    if show_exif:
        a['exifdata'] = import_one_module('exif', config).exif_tags(abs_image)
    else:
        a['exifdata'] = 0
    (prev, next) = config['mod.paths'].get_nearby_for_file(
            abs_image, config, tuples)
    if prev: prev = config['mod.paths'].abs_to_url(
            prev, config, tuples, ext = 'html')
    if next: next = config['mod.paths'].abs_to_url(
            next, config, tuples, ext = 'html')
    a['prev'] = prev
    a['next'] = next
    
    # A set of breadcrumbs that link back to the containing directory.
    if os.path.islink(abs_image):
        img_dest_path = os.path.realpath(abs_image)
        dir_dest_path = os.path.dirname(img_dest_path)
        # Hacky way to prune off the leading path.  The +1 gets rid of the
        # trailing / to make the path relative.  Also, I need to use realpath
        # to canonicalize both sides of this heinous equation.
        pruned_dest = dir_dest_path[len(os.path.realpath(
            config['img_prefix'])) + 1 :]
        leaf = os.path.basename(dir_dest_path)
        a['from_caption'] = config['mod.paths'].format_for_display(
                leaf, config)
        a['from_url'] = os.path.join(config['browse_prefix'], pruned_dest)

    breadcrumbs = config['mod.paths'].breadcrumbs_for_path(
            "./" + rel_dir, config, tuples)
    a['breadcrumbs'] = breadcrumbs

    template = import_one_module('templates.photopage', config).photopage(
            searchList=[a])
    a['browse_prefix'] = config['browse_prefix']
    if config.has_key('footer_message'):
        a['footer_message'] = config['footer_message']
    else:
        a['footer_message'] = None
    req.write(str(template))

def photo(req, url, config, tuples):
    size_index = url.rfind('_')
    ext_index = url.rfind('.')
    base = url[:ext_index]
    size = big_size
    ext = url[ext_index+1:]
    try:
        # Attempt a disambiguation to see if the file exists.
        config['mod.paths'].url_to_rel(base + '.' + ext, config, tuples)
    except:
        # If it fails, then try it with the underscore as a size separator.
        base = url[:size_index]
        size = url[size_index+1:ext_index]
    rel_image = config['mod.paths'].url_to_rel(
            base + '.' + ext, config, tuples)
    image_ctime = config['mod.cache'].lctime(
            config['mod.paths'].rel_to_abs(rel_image, config))
    config['mod.cache'].check_client_cache(
            req, "image/jpeg", image_ctime, config)
    try: allow_original = config['allow_original']
    except KeyError:
        allow_original = 1
    if size == "original" and not allow_original:
        size = "full"
    if size == "original":
        return spew_file(req, config['mod.paths'].rel_to_abs(
            rel_image, config))
    else:
        return spew_photo(req, rel_image, size, config)

def spew_photo(req, rel, size, config):
    abs_cachedir = os.path.join(config['cache_prefix'], size)
    abs_cachefile = os.path.join(abs_cachedir, rel)
    abs_raw_image = config['mod.paths'].rel_to_abs(rel, config)
    if config['mod.cache'].is_cached(abs_raw_image, abs_cachefile, config):
        return spew_file(req, abs_cachefile)
    else:
        config['mod.cache'].cache_img(req, rel, size, config)
        return

def spew_file(req, abs):
    #set the content length to avoid the evil chunked transfer coding
    req.set_content_length(os.stat(abs)[stat.ST_SIZE])
    req.sendfile(abs)


def first_image_in_dir(rel_dir, config, tuples):
    abs_dir = config['mod.paths'].rel_to_abs(rel_dir, config)
    items = config['mod.paths'].get_directory_tuples(abs_dir, config, tuples)
    for item in items:
        (scratch, base, ext) = config['mod.paths'].split_path_ext(
                item['filename'])
        if ext.lower() in config['mod.paths'].img_extns:
            return item['filename']
    
    # Got this far and didn't find an image.  Let's look in subdirs next.
    for dir_item in items:
        dir_fname = dir_item['filename']
        if os.path.isdir(os.path.join(abs_dir, dir_fname)):
            rel_subdir = os.path.join(rel_dir, dir_fname)
            recurse = first_image_in_dir(rel_subdir, config, tuples)
            return os.path.join(dir_fname, recurse)

# TODO: Fix this for mod_python
def ensure_trailing_slash_and_check_needs_refresh(req):
    uri = req.uri
    if not uri.endswith('/'):
        send_redirect(req, uri + '/')
        return 1
    return 0

def find_preview(rel_dir, config):
    abs_dir = config['mod.paths'].rel_to_abs(rel_dir, config)
    for fn in os.listdir(abs_dir):
        if fn == ".preview.jpeg" or fn.lower() == "preview.jpg":
            return os.path.join(rel_dir, fn)
    return None

def gallery(req, url_dir, config, tuples):
    # HACK: Since IE can't seem to handle meta refresh properly, I've
    # disabled redirect and instead we'll just patch up PATH_INFO to
    # pretend we got a trailing slash.

    #if ensure_trailing_slash_and_check_needs_refresh(req): return

    if url_dir.startswith('/home'): url_dir = '/'
    if not url_dir.endswith('/'): url_dir += '/'
    rel_dir = config['mod.paths'].url_to_rel(url_dir, config, tuples)
    abs_dir = config['mod.paths'].rel_to_abs(rel_dir, config)
    items = config['mod.paths'].get_directory_tuples(abs_dir, config, tuples)

    abs_images = []
    for item in items:
        fname = item['filename']
        abs_images.append(os.path.join(abs_dir, fname))

    config['mod.cache'].check_client_cache(
            req,
            'text/html; charset="UTF-8"',
            config['mod.cache'].max_ctime_for_files(
                [abs_dir] + [config['mod.cache'].scriptdir(
                    'templates/browse.tmpl')] + abs_images),
                config)

    image_records = []
    for item in items:
        fname = item['filename']
        displayname = item['displayname']
        (scratch, base, ext) = config['mod.paths'].split_path_ext(fname)
        if ext.lower() not in config['mod.paths'].img_extns: continue

        rel_image = os.path.join(rel_dir, fname)
        url_medium = config['mod.paths'].rel_to_url(
                rel_image, config, tuples, ext = 'html')
        url_big = config['mod.paths'].rel_to_url(
                rel_image, config, tuples, size = big_size)
        url_thumb = config['mod.paths'].rel_to_url(
                rel_image, config, tuples, size = thumb_size)
        caption = displayname
        (width, height) = config['mod.cache'].img_size(
                rel_image, thumb_size_int, config)
        rec = (url_medium, url_big, url_thumb, caption, width, height)
        image_records.append(rec)

    index_html = None
    rel_index = os.path.join(rel_dir, 'index.html')
    abs_index = config['mod.paths'].rel_to_abs(rel_index, config)
    if os.path.exists(abs_index):
        fh = file(abs_index, 'r')
        index_html = fh.read()
        fh.close()

    subdir_records = []
    for item in items:
        fname = item['filename']
        displayname = item['displayname']
        rel_subdir = os.path.join(rel_dir, fname)
        if fname.startswith('_'): continue
        if not os.path.isdir(config['mod.paths'].rel_to_abs(
            rel_subdir, config)): continue
        url_subdir = config['mod.paths'].rel_to_url(
                rel_subdir, config, tuples, trailing_slash = 1)
        caption = displayname
        rel_preview = find_preview(rel_subdir, config)
        if not rel_preview:
            rel_preview = first_image_in_dir(rel_subdir, config, tuples)
            if rel_preview:
                rel_preview = os.path.join(rel_subdir, rel_preview)

        preview = None
        width = 0
        height = 0
        if rel_preview:
            url_preview = config['mod.paths'].rel_to_url(
                    rel_preview, config, tuples, preview_size)
            preview = os.path.join(url_subdir, url_preview)
            (width, height) = config['mod.cache'].img_size(
                    rel_preview, 100, config)

        subdir_records.append((url_subdir, caption, preview, width, height))

    breadcrumbs = config['mod.paths'].breadcrumbs_for_path(
            './' + rel_dir[:-1], config, tuples)

    a = {}
    template = import_one_module('templates.browse', config).browse(
            searchList=[a])
    leafdir = os.path.split(rel_dir[:-1])[1]
    use_wn = 0
    if len(leafdir) == 0:
        leafdir = config['short_name']
        # Set up the What's New link for the root.
        wn_txt_path = os.path.join(config['img_prefix'], "whatsnew.txt")
        wn_updates = None
        if os.path.exists(wn_txt_path):
            wn_src = config['mod.whatsnew'].whatsnew_src_file(config)
            wn_updates = config['mod.whatsnew'].read_update_entries(
                    wn_src, config, tuples)
        if wn_updates and len(wn_updates) > 0:
            use_wn = 1
    if use_wn:
        wn_date = wn_updates[0]['date']
        wn_ctime = time.strftime('%B %d', time.strptime(wn_date, '%m-%d-%Y'))
        a['whatsnew_name'] = "What's New (updated " +  wn_ctime + ")"
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
    a['thisdir'] = config['mod.paths'].format_for_display(leafdir, config)
    a['imgurls'] = image_records
    a['subdirs'] = subdir_records
    a['index_html'] = index_html
    a['browse_prefix'] = config['browse_prefix']
    if config.has_key('footer_message'):
        a['footer_message'] = config['footer_message']
    else:
        a['footer_message'] = None


    req.write(str(template))
