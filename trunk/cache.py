# vim:sw=4:ts=4
import gallery_config
from paths import *

import os
import rfc822
import stat
import time
import sys
from PIL import Image
from StringIO import StringIO
import EXIF

def scriptdir(fname):
    return os.path.join(os.path.split(__file__)[0], fname)

cache_dependencies = [
    gallery_config.__file__,
    scriptdir('cache_sentinel')
]
scriptfiles = [
    gallery_config.__file__,
    scriptdir('browse.tmpl'),
    scriptdir('exif.tmpl')
]

def normalize_date(date):
    if date == None: return None
    return time.asctime(time.gmtime(
        rfc822.mktime_tz(rfc822.parsedate_tz(date))))

def check_client_cache(content_type, mtime):
    mtime = max(mtime, script_mtime())
    client_date = normalize_date(os.environ.get('HTTP_IF_MODIFIED_SINCE'))
    client_etag = os.environ.get('HTTP_IF_NONE_MATCH')
    server_date = time.asctime(time.gmtime(mtime))
    if (client_date == server_date and client_etag == server_date
            or client_date == None and client_etag == server_date
            or client_etag == None and client_date == server_date):
        sys.stdout.write('Status: 304 Not Modified\r\n\r\n')
        return 1
    else:
        #content_type = 'text/plain'
        sys.stdout.write("Content-type: " + content_type + "\n")
        sys.stdout.write('Last-Modified: ' + server_date + '\n')
        sys.stdout.write('ETag: ' + server_date + '\n')
        sys.stdout.write('\n')
        #sys.stdout.write('Last-Modified: ' + server_date + '\n')
        #sys.stdout.write('ETag: ' + server_date + '\n')
        #print 'client raw date', os.environ.get('HTTP_IF_MODIFIED_SINCE')
        #print 'client raw etag', os.environ.get('HTTP_IF_NONE_MATCH')
        #print "client date", client_date
        #print 'client etag', client_etag
        #print 'server date', server_date
        #print 'server etag', server_date
        #sys.stdout.write('\n')
        return 0

def img_size(rel_image, max_size):
    abs_cachedir = os.path.join(gallery_config.cache_prefix, "%d" % max_size)
    abs_cachefile = os.path.join(abs_cachedir, rel_image)
    abs_raw_image = rel_to_abs(rel_image)
    if iscached(abs_raw_image, abs_cachefile):
        cache_image = Image.open(abs_cachefile)
        return cache_image.size
    else:
        raw_image = Image.open(abs_raw_image)
        (width, height) = raw_image.size
        if width < max_size and height < max_size: return (width, height)
        if width > height:
            return (max_size, (max_size * height) / width)
        else:
            return ((max_size * width) / height, max_size)

def script_mtime():
    return max_mtime_for_files(scriptfiles)

def iscached(srcfile, cachefile):
    if not os.path.isfile(cachefile): return 0
    for dependency in [ srcfile ] + cache_dependencies:
        if lmtime(cachefile) < lmtime(dependency):
            return 0
    return 1 

def lmtime(fname):
    return os.lstat(fname)[stat.ST_MTIME]

def makedirsfor(fname):
    dirname = os.path.split(fname)[0]
    if not os.path.isdir(dirname): os.makedirs(dirname)

def cache_img(fname, width, height, cachedir, cachefile, do_output):
    img = Image.open(gallery_config.img_prefix + fname)
    f = open(gallery_config.img_prefix + fname, 'rb')
    tags = {}
    try: tags = EXIF.process_file(f)
    except: pass
    img.thumbnail((width,height), Image.ANTIALIAS)

    if gallery_config.apply_rotation:
        orientation_tag = tags.get('Image Orientation')
        if orientation_tag == None:
            orientation_tag = ''
        else:
            orientation_tag = orientation_tag.printable
        if orientation_tag.startswith("Rotated 90 CW"):
            img = img.rotate(-90, Image.NEAREST)
        elif orientation_tag.startswith("Rotated 90 CCW"):
            img = img.rotate(90, Image.NEAREST)

    buf = StringIO()
    img.save(buf, "JPEG", quality = 95)
    if do_output:
        sys.stdout.write(buf.getvalue())
    if os.path.isdir(cachedir):
        makedirsfor(cachefile)
        fil = file(cachefile, 'wb')
        fil.write(buf.getvalue())
        fil.close()
    buf.close()
    return img.size

def max_mtime_for_files(fnames):
    max_mtime = 0
    for fname in fnames:
        mtime = lmtime(fname)
        if mtime > max_mtime: max_mtime = mtime
    return max_mtime

