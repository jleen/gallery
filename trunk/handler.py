# vim:sw=4:ts=4
import cgi
import os
import re
import stat
import string
import sys
import time

from cache import *
from exif import *
from paths import *
import whatsnew
import templates.browse
import templates.photopage

import EXIF
from StringIO import StringIO

import jon.cgi as cgi

from config import configs

small_size = "600"
med_size = "1024"
big_size = "original"
thumb_size = "200"
preview_size = "100"

thumb_size_int = string.atoi(thumb_size)
preview_size_int = string.atoi(preview_size)

class GalleryHandler(cgi.Handler):
    def process(self, req):
        handler(req)

def handler(req):
    req.set_buffering(0)
    try:
        os.umask(0002)
        config = configs[req.params['config']]
        reqpath = req.environ["PATH_INFO"].lower()
        extn = os.path.splitext(reqpath)[1]
        if os.path.split(reqpath)[1] == 'index.html':
            return gallery(req, config)
        elif os.path.split(reqpath)[1] == 'whatsnew.html':
            return whatsnew.spew_recent_whats_new(req, config)
        elif os.path.split(reqpath)[1] == 'whatsnew_all.html':
            return whatsnew.spew_all_whats_new(req, config)
        elif extn.lower() in img_extns: return photo(req, config)
        elif extn == '.html': return photopage(req, config)
        elif extn.lower() in img_extns or len(extn) < 1: return gallery(req, config)
        else: send_404(req)
    except UnableToDisambiguateException: send_404(req)

def send_404(req):
    req.set_header('Status', '404 Not Found')
    req.set_header('Content-type', 'text/html')
    spew_file(req, "/home/jmleen/saturnvalley.org/errors/404.html")

def photopage(req, config):
    url = req.environ["PATH_INFO"][1:]
    (url_dir, base, extn) = split_path_ext(url)
    rel_dir = url_to_rel(url_dir, config)
    abs_image = url_to_abs(os.path.join(url_dir, base), config, infer_suffix = 1)
    if check_client_cache(req, 'text/html; charset="UTF-8"',
        max_ctime_for_files([abs_image, scriptdir('templates/photopage.tmpl')])): return

    abs_info = os.path.splitext(abs_image)[0] + '.info'
    description = ''
    if os.path.exists(abs_info):
        for line in file(abs_info):
            if line.startswith('Description: '):
                description = line[len('Description: '):]

    a = {}
    a['framed_img_url'] = abs_to_url(abs_image, config, size = "700x500")
    a['full_img_url'] = abs_to_url(abs_image, config, size = big_size)
    a['gallery_title'] =  config['short_name']
    a['photo_title'] = get_displayname_for_file(abs_image, config)
    a['description'] = description
    a['exifdata'] = exif_tags(abs_image)
    (prev, next) = get_nearby_for_file(abs_image, config)
    if prev: prev = abs_to_url(prev, config, ext = 'html')
    if next: next = abs_to_url(next, config, ext = 'html')
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
        a['from_caption'] = format_for_display(os.path.basename(dir_dest_path), config)
        a['from_url'] = os.path.join(config['browse_prefix'], pruned_dest)

    breadcrumbs = breadcrumbs_for_path("./" + rel_dir, final_is_link = 0, config = config)
    a['breadcrumbs'] = breadcrumbs

    template = templates.photopage.photopage(searchList=[a])
    req.write(str(template))

def photo(req, config):
    url = req.environ["PATH_INFO"][1:]
    size_index = url.rfind('_')
    ext_index = url.rfind('.')
    base = url[:size_index]
    size = url[size_index+1:ext_index]
    ext = url[ext_index+1:]
    rel_image = url_to_rel(base + '.' + ext, config)
    image_ctime = lctime(rel_to_abs(rel_image, config))
    if check_client_cache(req, "image/jpeg", image_ctime): return
    try: allow_original = config['allow_original']
    except KeyError:
        allow_original = 1
    if size == "original" and not allow_original:
        size = "full"
    if size == "original":
        return spew_file(req, rel_to_abs(rel_image), config)
    else:
        return spew_photo(req, rel_image, size, config)

def spew_photo(req, rel, size, config):
    abs_cachedir = os.path.join(config['cache_prefix'], size)
    abs_cachefile = os.path.join(abs_cachedir, rel)
    abs_raw_image = rel_to_abs(rel, config)
    if iscached(abs_raw_image, abs_cachefile):
        return spew_file(req, abs_cachefile)
    else:
        width = 0
        height = 0
        if size != "full":
            dims = size.split("x")
            width = int(dims[0])
            if len(dims) > 1: height = int(dims[1])
            else: height = width
        cache_img(req, rel, width, height, abs_cachedir, abs_cachefile, 1, config)
        return

def spew_html(abs):
    if check_client_cache( 'text/html; charset="UTF-8"',
            max_ctime_for_files([abs])):
        return
    spew_file(abs)

def spew_file(req, abs):
    fil = file(abs, 'rb')
    req.write(fil.read())
    fil.close()

def first_image_in_dir(rel_dir, config):
    abs_dir = rel_to_abs(rel_dir, config)
    items = get_directory_tuples(abs_dir, config)
    for item in items:
        (scratch, base, ext) = split_path_ext(item['filename'])
        if ext.lower() in img_extns:
            return item['filename']
    
    # Got this far and didn't find an image.  Let's look in subdirs next.
    for dir_item in items:
        dir_fname = dir_item['filename']
        if os.path.isdir(os.path.join(abs_dir, dir_fname)):
            recurse = first_image_in_dir(os.path.join(rel_dir, dir_fname), config)
            return os.path.join(dir_fname, recurse)

def send_redirect(req, new_url):
    new_full_url = 'http://www.saturnvalley.org' + new_url
    req.set_header('Content-type', 'text/html')
    req.write('<meta http-equiv="refresh" content="0;%s">' % new_full_url)

def ensure_trailing_slash_and_check_needs_refresh(req):
    uri = req.environ["REQUEST_URI"]
    if not uri.endswith('/'):
        send_redirect(req, uri + '/')
        return 1
    return 0

def find_preview(rel_dir, config):
    abs_dir = rel_to_abs(rel_dir, config)
    for fn in os.listdir(abs_dir):
        if fn == ".preview.jpeg" or fn.lower() == "preview.jpg":
            return os.path.join(rel_dir, fn)
    return None

def gallery(req, config):
    if ensure_trailing_slash_and_check_needs_refresh(req): return

    url_dir = req.environ["PATH_INFO"][1:]
    rel_dir = url_to_rel(url_dir, config)
    abs_dir = rel_to_abs(rel_dir, config)
    items = get_directory_tuples(abs_dir, config)

    abs_images = []
    for item in items:
        fname = item['filename']
        abs_images.append(os.path.join(abs_dir, fname))

    if check_client_cache(
            req,
            'text/html; charset="UTF-8"',
            max_ctime_for_files(
                [abs_dir] + [scriptdir('templates/browse.tmpl')] + abs_images)):
        return

    image_records = []
    for item in items:
        fname = item['filename']
        displayname = item['displayname']
        (scratch, base, ext) = split_path_ext(fname)
        if ext.lower() not in img_extns: continue

        rel_image = os.path.join(rel_dir, fname)
        url_medium = rel_to_url(rel_image, config, ext = 'html')
        url_big = rel_to_url(rel_image, config, size = big_size)
        url_thumb = rel_to_url(rel_image, config, size = thumb_size)
        caption = displayname
        (width, height) = img_size(rel_image, thumb_size_int, config)
        image_records.append((url_medium, url_big, url_thumb, caption, width, height))

    index_html = None
    rel_index = os.path.join(rel_dir, 'index.html')
    abs_index = rel_to_abs(rel_index, config)
    if os.path.exists(abs_index):
        fh = file(abs_index, 'r')
        index_html = fh.read()
        fh.close()

    subdir_records = []
    for item in items:
        fname = item['filename']
        displayname = item['displayname']
        rel_subdir = os.path.join(rel_dir, fname)
        if not os.path.isdir(rel_to_abs(rel_subdir, config)): continue
        url_subdir = rel_to_url(rel_subdir, config, trailing_slash = 1)
        caption = displayname
        rel_preview = find_preview(rel_subdir, config)
        if not rel_preview:
            rel_preview = first_image_in_dir(rel_subdir, config)
            if rel_preview:
                rel_preview = os.path.join(rel_subdir, rel_preview)

        preview = None
        width = 0
        height = 0
        if rel_preview:
            preview = os.path.join(url_subdir, rel_to_url(rel_preview, config, size = preview_size))
            (width, height) = img_size(rel_preview, 100, config)

        subdir_records.append((url_subdir, caption, preview, width, height))

    breadcrumbs = breadcrumbs_for_path('./' + rel_dir[:-1], 0, config)

    a = {}
    template = templates.browse.browse(searchList=[a])
    leafdir = os.path.split(rel_dir[:-1])[1]
    use_wn = 0
    if len(leafdir) == 0:
        leafdir = config['short_name']
        # Set up the What's New link for the root.
        wn_txt_path = os.path.join(config['img_prefix'], "whatsnew.txt")
        wn_updates = None
        if os.path.exists(wn_txt_path):
            wn_updates = whatsnew.read_update_entries(whatsnew.whatsnew_src_file(config), config)
        if wn_updates != None and len(wn_updates) > 0:
            use_wn = 1
    if use_wn:
        wn_ctime = time.strftime('%B %d', time.strptime(wn_updates[0]['date'], '%m-%d-%Y'))
        a['whatsnew_name'] = "What's New (updated " +  wn_ctime + ")"
        a['whatsnew_url'] = os.path.join(config['browse_prefix'], "whatsnew.html")
    else:
        a['whatsnew_name'] = None
        a['whatsnew_url'] = None

    a['title'] = config['long_name']
    a['breadcrumbs'] = breadcrumbs
    a['thisdir'] = format_for_display(leafdir, config)
    a['imgurls'] = image_records
    a['subdirs'] = subdir_records
    a['index_html'] = index_html

    req.write(str(template))
    return
