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

import gallery_config

small_size = "600"
med_size = "1024"
big_size = "full"
thumb_size = "200"
preview_size = "100"

thumb_size_int = string.atoi(thumb_size)
preview_size_int = string.atoi(preview_size)

def handler():
    #sys.stderr = sys.stdout
    #print "Content-Type: text/plain"
    #print

    try:
        os.umask(0002)
        reqpath = os.environ["PATH_INFO"].lower()
        extn = os.path.splitext(reqpath)[1]
        if os.path.split(reqpath)[1] == 'index.html': return gallery()
        elif os.path.split(reqpath)[1] == 'whatsnew.html':
            return whatsnew.spew_recent_whats_new()
        elif os.path.split(reqpath)[1] == 'whatsnew_all.html':
            return whatsnew.spew_all_whats_new()
        elif extn.lower() in img_extns: return photo()
        elif extn == '.html': return photopage()
        elif extn.lower() in img_extns or len(extn) < 1: return gallery()
        else: send_404()
    except UnableToDisambiguateException: send_404()

def send_404():
    sys.stdout.write("Status: 404 Not Found\n")
    sys.stdout.write("Content-type: text/html\n\n")
    spewfile("/home/jmleen/saturnvalley.org/errors/404.html")

def photopage():
    url = os.environ["PATH_INFO"][1:]
    (url_dir, base, extn) = split_path_ext(url)
    rel_dir = url_to_rel(url_dir)
    abs_image = url_to_abs(os.path.join(url_dir, base), infer_suffix = 1)
    if check_client_cache('text/html; charset="UTF-8"',
        max_mtime_for_files([abs_image, scriptdir('templates/photopage.tmpl')])): return

    abs_info = os.path.splitext(abs_image)[0] + '.info'
    description = ''
    if os.path.exists(abs_info):
        for line in file(abs_info):
            if line.startswith('Description: '):
                description = line[len('Description: '):]

    a = {}
    a['framed_img_url'] = abs_to_url(abs_image, size = "700x500")
    a['full_img_url'] = abs_to_url(abs_image, size = "full")
    a['gallery_title'] =  gallery_config.short_name
    a['photo_title'] = get_displayname_for_file(abs_image)
    a['description'] = description
    a['exifdata'] = exif_tags(abs_image)
    (prev, next) = get_nearby_for_file(abs_image)
    if prev: prev = abs_to_url(prev, ext = 'html')
    if next: next = abs_to_url(next, ext = 'html')
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
            gallery_config.img_prefix)) + 1 :]
        a['from_caption'] = format_for_display(os.path.basename(dir_dest_path))
        a['from_url'] = os.path.join(gallery_config.browse_prefix, pruned_dest)

    breadcrumbs = breadcrumbs_for_path("./" + rel_dir, 0)
    a['breadcrumbs'] = breadcrumbs

    template = templates.photopage.photopage(searchList=[a])
    sys.stdout.write(str(template))

def photo():
    url = os.environ["PATH_INFO"][1:]
    size_index = url.rfind('_')
    ext_index = url.rfind('.')
    base = url[:size_index]
    size = url[size_index+1:ext_index]
    ext = url[ext_index+1:]
    rel_image = url_to_rel(base + '.' + ext)
    image_mtime = lmtime(rel_to_abs(rel_image))
    if check_client_cache("image/jpeg", image_mtime): return
    try: allow_original = gallery_config.allow_original
    except AttributeError:
        allow_original = 1
    if size == "original" and not allow_original:
        size = "full"
    if size == "full":
        return spewuncachedphoto(rel_image)
    elif size == "original":
        return spewfile(rel_to_abs(rel_image))
    else:
        return spewphoto(rel_image, size)

def spewphoto(rel, size):
    abs_cachedir = os.path.join(gallery_config.cache_prefix, size)
    abs_cachefile = os.path.join(abs_cachedir, rel)
    abs_raw_image = rel_to_abs(rel)
    if iscached(abs_raw_image, abs_cachefile):
        return spewfile(abs_cachefile)
    else:
        dims = size.split("x")
        width = int(dims[0])
        if len(dims) > 1: height = int(dims[1])
        else: height = width
        cache_img(rel, width, height, abs_cachedir, abs_cachefile, 1)
        return

def spewhtml(abs):
    if check_client_cache( 'text/html; charset="UTF-8"',
            max_mtime_for_files([abs])):
        return
    spewfile(abs)

def spewuncachedphoto(rel):
    get_image_for_display(rel_to_abs(rel)).save(sys.stdout, "JPEG", quality = 95)

def spewfile(abs):
    fil = file(abs, 'rb')
    sys.stdout.write(fil.read())
    fil.close()

def first_image_in_dir(rel_dir):
    abs_dir = rel_to_abs(rel_dir)
    items = get_directory_tuples(abs_dir)
    for item in items:
        (scratch, base, ext) = split_path_ext(item['filename'])
        if ext.lower() in img_extns:
            return item['filename']
    
    # Got this far and didn't find an image.  Let's look in subdirs next.
    for dir_item in items:
        dir_fname = dir_item['filename']
        if os.path.isdir(os.path.join(abs_dir, dir_fname)):
            recurse = first_image_in_dir(os.path.join(rel_dir, dir_fname))
            return os.path.join(dir_fname, recurse)

def send_redirect(new_url):
    sys.stdout.write("Location: http://www.saturnvalley.org" + new_url + "\n\n")

def ensure_trailing_slash():
    uri = os.environ["REQUEST_URI"]
    if not uri.endswith('/'):
        send_redirect(uri + '/')
        return

def find_preview(rel_dir):
    abs_dir = rel_to_abs(rel_dir)
    for fn in os.listdir(abs_dir):
        if fn == ".preview.jpeg" or fn.lower() == "preview.jpg":
            return os.path.join(rel_dir, fn)
    return None

def gallery():
    ensure_trailing_slash()

    url_dir = os.environ["PATH_INFO"][1:]
    rel_dir = url_to_rel(url_dir)
    abs_dir = rel_to_abs(rel_dir)
    items = get_directory_tuples(abs_dir)

    abs_images = []
    for item in items:
        fname = item['filename']
        abs_images.append(os.path.join(abs_dir, fname))

    if check_client_cache(
            'text/html; charset="UTF-8"',
                    max_mtime_for_files([abs_dir] + [scriptdir('templates/browse.tmpl')] + abs_images)):
        return

    image_records = []
    for item in items:
        fname = item['filename']
        displayname = item['displayname']
        (scratch, base, ext) = split_path_ext(fname)
        if ext.lower() not in img_extns: continue

        rel_image = os.path.join(rel_dir, fname)
        url_medium = rel_to_url(rel_image, ext = 'html')
        url_big = rel_to_url(rel_image, size = big_size)
        url_thumb = rel_to_url(rel_image, size = thumb_size)
        caption = displayname
        (width, height) = img_size(rel_image, thumb_size_int)
        image_records.append((url_medium, url_big, url_thumb, caption, width, height))

    index_html = None
    rel_index = os.path.join(rel_dir, 'index.html')
    abs_index = rel_to_abs(rel_index)
    if os.path.exists(abs_index):
        fh = file(abs_index, 'r')
        index_html = fh.read()
        fh.close()

    subdir_records = []
    for item in items:
        fname = item['filename']
        displayname = item['displayname']
        rel_subdir = os.path.join(rel_dir, fname)
        if not os.path.isdir(rel_to_abs(rel_subdir)): continue
        url_subdir = rel_to_url(rel_subdir, trailing_slash = 1)
        caption = displayname
        rel_preview = find_preview(rel_subdir)
        if not rel_preview:
            rel_preview = first_image_in_dir(rel_subdir)
            if rel_preview:
                rel_preview = os.path.join(rel_subdir, rel_preview)

        preview = None
        width = 0
        height = 0
        if rel_preview:
            preview = os.path.join(url_subdir, rel_to_url(rel_preview, size = preview_size))
            (width, height) = img_size(rel_preview, 100)

        subdir_records.append((url_subdir, caption, preview, width, height))

    breadcrumbs = breadcrumbs_for_path('./' + rel_dir[:-1], 0)

    a = {}
    template = templates.browse.browse(searchList=[a])
    leafdir = os.path.split(rel_dir[:-1])[1]
    use_wn = 0
    if len(leafdir) == 0:
        leafdir = gallery_config.short_name
        # Set up the What's New link for the root.
        wn_txt_path = os.path.join(gallery_config.img_prefix, "whatsnew.txt")
        wn_updates = None
        if os.path.exists(wn_txt_path):
            wn_updates = whatsnew.read_update_entries(whatsnew.whatsnew_src_file())
        if wn_updates != None and len(wn_updates) > 0:
            use_wn = 1
    if use_wn:
        wn_mtime = time.strftime('%B %d', time.strptime(wn_updates[0]['date'], '%m-%d-%Y'))
        a['whatsnew_name'] = "What's New (updated " +  wn_mtime + ")"
        a['whatsnew_url'] = os.path.join(gallery_config.browse_prefix, "whatsnew.html")
    else:
        a['whatsnew_name'] = None
        a['whatsnew_url'] = None

    a['title'] = gallery_config.long_name
    a['breadcrumbs'] = breadcrumbs
    a['thisdir'] = format_for_display(leafdir)
    a['imgurls'] = image_records
    a['subdirs'] = subdir_records
    a['index_html'] = index_html

    sys.stdout.write(str(template))
    return
