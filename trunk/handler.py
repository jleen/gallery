import cgi
import os
import re
import stat
import sys
import time

from cache import *
from exif import *
from paths import *

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
    reqpath = os.environ["PATH_INFO"].lower()
    extn = os.path.splitext(reqpath)[1]
    if os.path.split(reqpath)[1] == 'index.html': return gallery()
    elif os.path.split(reqpath)[1] == 'whatsnew.html':
        return spewhtml(os.path.join(gallery_config.img_prefix, 'whatsnew.html'))
    elif os.path.split(reqpath)[1] == 'whatsnew_all.html':
        return spewhtml(os.path.join(gallery_config.img_prefix, 'whatsnew_all.html'))
    elif extn.lower() in img_extns: return photo()
    elif reqpath.lower().endswith('_exif.html'): return exifpage()
    elif extn == '.html': return photopage()
    else: return gallery()

def photopage():
    fname = os.environ["PATH_INFO"][1:]
    (dir, base, extn) = decompose_image_path(fname)
    img_fname = os.path.join(gallery_config.img_prefix, infer_serial_prefix(os.path.join(dir, base), infer_suffix = 1))
    image_mtime = lmtime(img_fname)
    if check_client_cache('text/html; charset="UTF-8"', image_mtime): return
    infofile = os.path.splitext(img_fname)[0] + '.info'
    description = ''
    if os.path.exists(infofile):
        for line in file(infofile):
            if line.startswith('Description: '):
                description = line[len('Description: '):]

    a = {}
    a['framed_img_url'] = path_to_url(img_fname, size = "700")
    a['full_img_url'] = path_to_url(img_fname, size = "full")
    a['gallery_title'] =  gallery_config.short_name
    a['photo_title'] = format_fn_for_display(trim_serials(base))
    a['description'] = description
    template = Template(file=scriptdir('photopage.tmpl'), searchList=[a])
    sys.stdout.write(str(template))

def exifpage():
    fname = os.environ["PATH_INFO"][1:]
    img_index = fname.rfind('_')
    img_path = fname[:img_index]
    img_fname = os.path.join(gallery_config.img_prefix, infer_serial_prefix(img_path))

    image_mtime = lmtime(img_fname)
    if check_client_cache('text/html; charset="UTF-8"', image_mtime): return

    a = {}
    template = Template(file=scriptdir('exif.tmpl'), searchList=[a])
    #ambiguate this name?
    a['title'] = os.path.basename(img_fname)

    processedTags = exif_tags(img_fname)

    a['data'] = processedTags

    sys.stdout.write(str(template))
    return
    
def photo():
    fname = os.environ["PATH_INFO"][1:]
    size_index = fname.rfind('_')
    extn_index = fname.rfind('.')
    base = fname[:size_index]
    size = fname[size_index+1:extn_index]
    extn = fname[extn_index+1:]
    img_fname = infer_serial_prefix(base + '.' + extn)
    image_mtime = lmtime(os.path.join(gallery_config.img_prefix, img_fname))
    if check_client_cache("image/jpeg", image_mtime): return
    if size == "full":
        return spewfile(gallery_config.img_prefix + img_fname)
    else:
        size = int(size)
        return spewphoto(img_fname, size)

def spewphoto(fname, size):
    cachedir = "%s%d" % (gallery_config.cache_prefix, size)
    cachefile = cachedir + '/' + fname
    srcfile = gallery_config.img_prefix + fname
    if iscached(srcfile, cachefile):
        return spewfile(cachefile)
    else:
        cache_img(fname, size, cachedir, cachefile, 1)
        return

def spewhtml(fname):
    if check_client_cache( 'text/html; charset="UTF-8"',
            max_mtime_for_files([fname])):
        return
    spewfile(fname)

def spewfile(fname):
    fil = file(fname, 'rb')
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

def gallery():
    uri = os.environ["REQUEST_URI"]
    if not uri.endswith('/'):
        send_redirect(uri + '/')
        return
    trimmed_dir_fname = os.environ["PATH_INFO"][1:]
    dir_fname = infer_serial_prefix(trimmed_dir_fname)
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
        (scratch, fnamebase, extn) = decompose_image_path(fname)
        if extn.lower() not in img_extns: continue
        if fnamebase.startswith('.'): continue
        pageurl = ""
        imgbase = os.path.join(gallery_config.browse_prefix, trimmed_dir_fname, fnamebase)
        smallurl = imgbase + "_" + small_size + extn
        medurl = imgbase + '.html'
        bigurl = imgbase + "_" + big_size + extn
        thumburl = imgbase + "_" + thumb_size + extn
        exifurl = imgbase + extn + "_exif.html"
        caption = format_fn_for_display(trim_serials(fnamebase))
        rel_img_path = os.path.join(dir_fname, fname)
        imgurls.append((smallurl, medurl, bigurl, thumburl, exifurl, caption))

    subdirs = []
    for fname in fnames:
        dirname = os.path.join(dir_fname, fname)
        if not os.path.isdir(gallery_config.img_prefix + dirname): continue
        dir = os.path.join(gallery_config.browse_prefix, trim_serials(dirname), '')
        display = format_fn_for_display(trim_serials(fname))
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
            subdirs.append((dir, display, None, 0, 0))

    breadcrumbs = []
    dirname = ''
    for crumb in ('./' + dir_fname[:-1]).split(os.path.sep):
        if len(crumb) < 1: continue
        dirname = os.path.join(dirname, crumb)
        dir = os.path.join(gallery_config.browse_prefix, trim_serials(dirname), '')
        display = format_fn_for_display(trim_serials(crumb))
        breadcrumbs.append([1, dir, display])
    # The last breadcrumb should not be a link
    breadcrumbs[-1][0] = 0;

    a = {}
    template = Template(file=scriptdir('browse.tmpl'), searchList=[a])
    leafdir = os.path.split(dir_fname[:-1])[1]
    use_wn = 0
    if len(leafdir) == 0:
        leafdir = gallery_config.short_name
        #set up the what's new link for the root.
        wn_txt_path = os.path.join(gallery_config.img_prefix, "whatsnew.txt")
        if os.path.exists(wn_txt_path):
            use_wn = 1
    if use_wn:
        wn_mtime = time.localtime(os.path.getmtime(os.path.join(gallery_config.img_prefix, "whatsnew.txt")))
        a['whatsnew_name'] = "What's New (updated " + time.strftime('%B %d', wn_mtime) + ")"
        a['whatsnew_url'] = os.path.join(gallery_config.browse_prefix, "whatsnew.html")
    else:
        a['whatsnew_name'] = None
        a['whatsnew_url'] = None

    a['title'] = gallery_config.long_name
    a['breadcrumbs'] = breadcrumbs
    a['thisdir'] = format_fn_for_display(trim_serials(leafdir))
    a['imgurls'] = imgurls
    a['subdirs'] = subdirs
    a['show_exif'] = gallery_config.show_exif

    sys.stdout.write(str(template))
    return
