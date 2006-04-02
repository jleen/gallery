#!/usr/bin/env python2.2

#import cgitb; cgitb.enable()

import cgi
import os
import re
import rfc822
import sys
import time

sys.path.insert(0, '/home/jmleen/lib/python2.2/site-packages')

from PIL import Image
from StringIO import StringIO
from Cheetah.Template import Template

if os.environ['SCRIPT_URL'].startswith("/mgb/photos"):
    img_prefix = "/home/mgb/photos/"
    cache_prefix = "/home/jmleen/var/cache/gallery/mgb/"
    browse_prefix = "/mgb/photos/"
else:
    img_prefix = "/home/jmleen/saturnvalley.org/photos/"
    cache_prefix = "/home/jmleen/var/cache/gallery/"
    browse_prefix = "/gallery/"
small_size = "600"
med_size = "1024"
big_size = "full"
thumb_size = "200"
scriptfiles = ['gallery.py']
scriptdir = '/home/jmleen/saturnvalley.org/app/gallery'

img_extns = ['.jpeg', '.jpg']

trim_serials_regexp = re.compile('^\d+_')

browse_template = """
<style>
body
{
    font-family: Georgia, Times New Roman, Times, serif;
    font-size: 90%;
    color: #333333;
    background-color: #eeeeee;
}
img
{
    border: solid 2px #333366; 
}
a
{
    text-decoration: none;
    color: #333333;
}
</style>
    
<title>Saturn Valley Hall of Light: $thisdir</title>

<p>
<b>Navigate:</b>
#set $first = 1
#for $dir, $name in $subdirs
#if $first == 0
&ndash;
#end if
    <a href="<%=dir%>"><%=name%></a>
#set $first = 0
#end for
</p>

<p><b>$thisdir</b></p>
<div align="center">
#for $smallurl, $medurl, $bigurl, $thumburl, $thumb_height, $thumb_width, $caption in $imgurls:
<table style="display: inline">
<tr>
<td align="center" valign="middle" height="260" width="220">
<a href="$medurl"><img src="$thumburl" border="2" vspace="10" align="middle" height="$thumb_height" width="$thumb_width"></a><br>
<a href="$bigurl">$caption</a>
</td>
</tr>
</table>
#end for
</div>
"""


def handler():
    reqpath = os.environ["PATH_INFO"].lower()
    extn = os.path.splitext(reqpath)[1]
    if os.path.split(reqpath)[1] == 'index.html': return gallery()
    elif extn.lower() in img_extns: return photo()
    #elif extn == '.html': return photopage(req)
    else: return gallery()

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
        sys.stdout.write('Status: 304 Not Modified')
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

def infer_image_path(base):
    for ext in img_extns:
        if os.path.exists(img_prefix + base + ext): return base + ext
    raise ValueError

def script_mtime():
    scriptpaths = [ os.path.join(scriptdir, f) for f in scriptfiles ]
    return max_mtime_for_files(scriptpaths)

def ambiguate_filename(regexp):
    # This is horrifically bogus.  We should have a table or something.
    amb = ''
    for ch in regexp:
        if   ch == 'a': amb += '(a|\xc3\xa4)'
        elif ch == 'o': amb += '(o|\xc3\xb6)'
        else: amb += ch
    return amb

def degrade_filename(fn):
    # By a similar token, this function is a crock.
    fn = fn.replace('\xc3\xa4', 'a')
    fn = fn.replace('\xc3\xb6', 'o')
    return fn

def infer_serial_prefix(fname):
    fname = os.path.join(img_prefix, fname)
    if os.path.exists(fname): return fname[len(img_prefix):]
    (dir, basename) = os.path.split(fname)
    if not os.path.exists(dir):
        newdir = infer_serial_prefix(dir[len(img_prefix):])
        dir = os.path.join(img_prefix, newdir)
    candidates = os.listdir(dir)
    r = re.compile('^\d+_' + ambiguate_filename(re.escape(basename)) + '$')
    found = [ f for f in candidates if r.search(f) != None ]
    if len(found) > 0: newbasename = found[0]
    else: newbasename = basename
    return os.path.join(dir, newbasename)[len(img_prefix):]

def photo():
    fname = os.environ["PATH_INFO"][2:]
    size_index = fname.rfind('_')
    extn_index = fname.rfind('.')
    base = fname[:size_index]
    size = fname[size_index+1:extn_index]
    extn = fname[extn_index+1:]
    img_fname = infer_serial_prefix(base + '.' + extn)
    image_mtime = os.path.getmtime(os.path.join(img_prefix, img_fname))
    if check_client_cache("image/jpeg", image_mtime): return
    if size == "full":
        return spewfile(img_prefix + img_fname)
    else:
        size = int(size)
        return spewphoto(img_fname, size)

def iscached(srcfile, cachefile):
    return (os.path.isfile(cachefile) and
        os.path.getmtime(cachefile) >= os.path.getmtime(srcfile))

def spewphoto(fname, size):
    cachedir = "%s%d" % (cache_prefix, size)
    cachefile = cachedir + '/' + fname
    srcfile = img_prefix + fname
    if iscached(srcfile, cachefile):
        return spewfile(cachefile)
    else:
        cache_img(fname, size, cachedir, cachefile, 1)
        return

def spewfile(fname):
    fil = file(fname, 'rb')
    sys.stdout.write(fil.read())
    fil.close()

def makedirsfor(fname):
    dirname = os.path.split(fname)[0]
    if not os.path.isdir(dirname): os.makedirs(dirname)

def img_size(fname, size):
    cachedir = "%s%d" % (cache_prefix, size)
    cachefile = cachedir + '/' + fname
    srcfile = img_prefix + fname
    if not iscached(srcfile, cachefile):
        return cache_img(fname, size, cachedir, cachefile, 0)
    else:
        img = Image.open(cachefile)
        return img.size

def cache_img(fname, size, cachedir, cachefile, do_output):
    img = Image.open(img_prefix + fname)
    img.thumbnail((size,size), Image.ANTIALIAS)
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

def script_path(req):
    top_dirname = os.path.split(os.environ["SCRIPT_FILENAME"])[1]
    rest_dirname = os.environ["PATH_INFO"][1:]
    if len(rest_dirname) > 0:
        path = os.path.join(top_dirname, rest_dirname[:-1])
    else:
        path = top_dirname
    if os.path.split(path)[1] == 'index.html':
        return os.path.split(path)[0]
    else:
        return path
    

def max_mtime_for_files(fnames):
    max_mtime = 0
    for fname in fnames:
        mtime = os.path.getmtime(os.path.join(dir, fname))
        if mtime > max_mtime: max_mtime = mtime
    return max_mtime

def trim_serials(fn):
    return trim_serials_regexp.sub('', fn)

def format_fn_for_display(fn):
    if fn.startswith('DSC_'): return ''
    fn = fn.replace('_', ' ')
    fn = fn.replace('~', '?')
    fn = fn.replace("'", '&rsquo;')
    fn = fn.replace('{o:}', '\xc3\xb6')
    fn = fn.replace('{a:}', '\xc3\xa4')
    return fn

def send_redirect(new_url):
    sys.stdout.write("Location: http://www.saturnvalley.org" + new_url + "\n\n")

def gallery():
    uri = os.environ["REQUEST_URI"]
    if not uri.endswith('/'):
        send_redirect(uri + '/')
        return
    trimmed_dir_fname = os.environ["PATH_INFO"][2:]
    dir_fname = infer_serial_prefix(trimmed_dir_fname)
    img_dir = os.path.join(img_prefix, dir_fname)
    fnames = os.listdir(img_dir)
    fnames.sort()

    fs_img_dir = os.path.join(img_prefix, dir_fname)
    fs_img_files = [ os.path.join(fs_img_dir, fn) for fn in fnames ]
    if check_client_cache(
            'text/html; charset="UTF-8"',
            max_mtime_for_files([fs_img_dir] + fs_img_files)):
        return

    imgurls = []
    for fname in fnames:
        (fnamebase, extn) = os.path.splitext(fname)
        if extn.lower() in img_extns:
            pageurl = ""
            trimmed = degrade_filename(trim_serials(fnamebase))
            imgbase = os.path.join(browse_prefix, trimmed_dir_fname, trimmed)
            smallurl = imgbase + "_" + small_size + extn
            medurl = imgbase + "_" + med_size + extn
            bigurl = imgbase + "_" + big_size + extn
            thumburl = imgbase + "_" + thumb_size + extn
            caption = format_fn_for_display(trim_serials(fnamebase))
            rel_img_path = os.path.join(dir_fname, fname)
            (thumb_width, thumb_height) = img_size(rel_img_path, 200)
            imgurls.append((smallurl, medurl, bigurl, thumburl,
                thumb_height, thumb_width, caption))

    subdirs = []
    for fname in fnames:
        dirname = os.path.join(dir_fname, fname)
        if not os.path.isdir(img_prefix + dirname): continue
        dir = os.path.join(browse_prefix, trim_serials(dirname), '')
        subdirs.append((dir, format_fn_for_display(trim_serials(fname))))
    if len(dir_fname) > 0:
        subdirs.append(('../', '(up)'))

    a = {}
    template = Template(browse_template, searchList=[a])
    leafdir = os.path.split(dir_fname[:-1])[1]
    if len(leafdir) == 0: leafdir = 'Hall of Light'
    a['thisdir'] = format_fn_for_display(trim_serials(leafdir))
    a['imgurls'] = imgurls
    a['subdirs'] = subdirs
    sys.stdout.write(str(template))
    return


handler()
