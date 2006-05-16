# vim:sw=4:ts=4
import cgi
import os
import re
import stat
import sys
import time

from cache import *
from exif import *
from paths import *
import whatsnew

import EXIF
from StringIO import StringIO
from Cheetah.Template import Template

import gallery_config

small_size = "600"
med_size = "1024"
big_size = "full"
thumb_size = "200"
preview_size = "100"



def handler():
    os.umask(0002)
    reqpath = os.environ["PATH_INFO"].lower()
    extn = os.path.splitext(reqpath)[1]
    if os.path.split(reqpath)[1] == 'index.html': return gallery()
    elif os.path.split(reqpath)[1] == 'whatsnew.html':
        return whatsnew.spew_recent_whats_new()
    elif os.path.split(reqpath)[1] == 'whatsnew_all.html':
        return whatsnew.spew_all_whats_new()
    elif extn.lower() in img_extns: return photo()
    elif reqpath.lower().endswith('_exif.html'): return exifpage()
    elif extn == '.html': return photopage()
    else: return gallery()

def photopage():
    url = os.environ["PATH_INFO"][1:]
    (url_dir, base, extn) = split_path_ext(url)
    abs_image = url_to_abs(os.path.join(url_dir, base), infer_suffix = 1)
    image_mtime = lmtime(abs_image)
    if check_client_cache('text/html; charset="UTF-8"', image_mtime): return
    abs_info = os.path.splitext(abs_image)[0] + '.info'
    description = ''
    if os.path.exists(abs_info):
        for line in file(abs_info):
            if line.startswith('Description: '):
                description = line[len('Description: '):]

    a = {}
    a['framed_img_url'] = abs_to_url(abs_image, size = "700")
    a['full_img_url'] = abs_to_url(abs_image, size = "full")
    a['gallery_title'] =  gallery_config.short_name
    a['photo_title'] = format_for_display(base)
    a['description'] = description
    a['exifdata'] = exif_tags(abs_image)
    a['show_exif'] = gallery_config.show_exif;
    
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

    breadcrumbs = breadcrumbs_for_path("./" + url_dir, 0)
    a['breadcrumbs'] = breadcrumbs

    template = Template(file=scriptdir('photopage.tmpl'), searchList=[a])
    sys.stdout.write(str(template))

def exifpage():
    url = os.environ["PATH_INFO"][1:]
    img_index = url.rfind('_')
    img_path = url[:img_index]
    abs_image = url_to_abs(img_path)

    image_mtime = lmtime(abs_image)
    if check_client_cache('text/html; charset="UTF-8"', image_mtime): return

    a = {}
    template = Template(file=scriptdir('exif.tmpl'), searchList=[a])
    #ambiguate this name?
    a['title'] = os.path.basename(abs_image)

    processedTags = exif_tags(abs_image)

    a['data'] = processedTags

    sys.stdout.write(str(template))
    return
    
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
    if size == "full":
        return spewfile(rel_to_abs(rel_image))
    else:
        size = int(size)
        return spewphoto(rel_image, size)

def spewphoto(rel, size):
    abs_cachedir = os.path.join(gallery_config.cache_prefix, "%d" % size)
    abs_cachefile = os.path.join(abs_cachedir, rel)
    abs_raw_image = rel_to_abs(rel)
    if iscached(abs_raw_image, abs_cachefile):
        return spewfile(abs_cachefile)
    else:
        cache_img(rel, size, abs_cachedir, abs_cachefile, 1)
        return

def spewhtml(abs):
    if check_client_cache( 'text/html; charset="UTF-8"',
            max_mtime_for_files([abs])):
        return
    spewfile(abs)


def spewfile(abs):
    fil = file(abs, 'rb')
    sys.stdout.write(fil.read())
    fil.close()

def first_image_fname(dir_fname):
    img_dir = os.path.join(gallery_config.img_prefix, dir_fname)
    fnames = os.listdir(img_dir)
    fnames.sort()
    for fname in fnames:
        (base, extn) = os.path.splitext(fname)
        if extn.lower() not in img_extns: continue
        if base.startswith('.'): continue
        return fname
    # Got this far and didn't find an image.  Let's look in subdirs next.
    for fname in fnames:
        if os.path.isdir(os.path.join(img_dir, fname)):
            return os.path.join(fname, first_image_fname(os.path.join(dir_fname, fname)))

def send_redirect(new_url):
    sys.stdout.write("Location: http://www.saturnvalley.org" + new_url + "\n\n")

def ensure_trailing_slash():
    uri = os.environ["REQUEST_URI"]
    if not uri.endswith('/'):
        send_redirect(uri + '/')
        return

def gallery():
    ensure_trailing_slash()

    url_dir = os.environ["PATH_INFO"][1:]
    dir_fname = url_to_rel(url_dir)
    img_dir = os.path.join(gallery_config.img_prefix, dir_fname)
    fnames = os.listdir(img_dir)
    fnames.sort()

    fs_img_dir = os.path.join(gallery_config.img_prefix, dir_fname)
    fs_img_files = [ os.path.join(fs_img_dir, fn) for fn in fnames ]
    if check_client_cache(
            'text/html; charset="UTF-8"',
            max_mtime_for_files([fs_img_dir] + fs_img_files)):
        return

    imgurls = []
    for fname in fnames:
        (scratch, fnamebase, extn) = split_path_ext(fname)
        if extn.lower() not in img_extns: continue
        if fnamebase.startswith('.'): continue
        pageurl = ""
        imgbase = os.path.join(gallery_config.browse_prefix, url_dir, fnamebase)
        smallurl = imgbase + "_" + small_size + extn
        medurl = imgbase + '.html'
        bigurl = imgbase + "_" + big_size + extn
        thumburl = imgbase + "_" + thumb_size + extn
        exifurl = imgbase + extn + "_exif.html"
        caption = format_for_display(fnamebase)
        rel_img_path = os.path.join(dir_fname, fname)
        imgurls.append((smallurl, medurl, bigurl, thumburl, exifurl, caption))

    subdirs = []
    for fname in fnames:
        dirname = os.path.join(dir_fname, fname)
        if not os.path.isdir(gallery_config.img_prefix + dirname): continue
        dir = rel_to_url(dirname, trailing_slash = 1)
        display = format_for_display(fname)
        # (fnamebase, extn) = os.path.splitext(fname)
        preview_fname = '.preview.jpeg';
        if not os.path.exists(os.path.join(gallery_config.img_prefix, dir_fname, fname, preview_fname)):
            preview_fname = first_image_fname(os.path.join(dir_fname, fname))
        if preview_fname:
            (preview_base, preview_extn) = os.path.splitext(preview_fname)
            preview = os.path.join(dir, preview_base + '_' + preview_size + preview_extn)
            rel_img_path = os.path.join(dir_fname, fname, preview_fname)
            subdirs.append((dir, display, preview))
        else:
            subdirs.append((dir, display, None))

    breadcrumbs = breadcrumbs_for_path('./' + dir_fname[:-1], 0)

    a = {}
    template = Template(file=scriptdir('browse.tmpl'), searchList=[a])
    leafdir = os.path.split(dir_fname[:-1])[1]
    use_wn = 0
    if len(leafdir) == 0:
        leafdir = gallery_config.short_name
        #set up the what's new link for the root.
        wn_txt_path = os.path.join(gallery_config.img_prefix, "whatsnew.txt")
        wn_updates = None
        if os.path.exists(wn_txt_path):
            wn_updates = whatsnew.read_update_entries(whatsnew.whatsnew_src_file())
        if len(wn_updates) > 0:
            use_wn = 1
    if use_wn:
        wn_mtime = time.strftime('%B %d', time.strptime(wn_updates[0]['date'], '%m-%d-%Y'))
        a['whatsnew_name'] = "What's New (updated " +  wn_mtime + ")"
        #a['whatsnew_name'] = "What's New (updated " + time.strftime('%B %d', wn_mtime) + ")"
        a['whatsnew_url'] = os.path.join(gallery_config.browse_prefix, "whatsnew.html")
    else:
        a['whatsnew_name'] = None
        a['whatsnew_url'] = None

    a['title'] = gallery_config.long_name
    a['breadcrumbs'] = breadcrumbs
    a['thisdir'] = format_for_display(leafdir)
    a['imgurls'] = imgurls
    a['subdirs'] = subdirs
    a['show_exif'] = gallery_config.show_exif

    sys.stdout.write(str(template))
    return
