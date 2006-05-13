import cgi
import os
import re
import rfc822
import stat
import sys
import time

sys.path.insert(0, '/home/jmleen/lib/python2.4/site-packages')

import EXIF
from PIL import Image
from StringIO import StringIO
from Cheetah.Template import Template

import gallery_config

small_size = "600"
med_size = "1024"
big_size = "full"
thumb_size = "200"
preview_size = "100"

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

img_extns = ['.jpeg', '.jpg']

trim_serials_regexp = re.compile('(^\d+_|(?<=/)\d+_)')

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

def path_to_url(path, size = None, ext = None):
    rel_path = path[len(gallery_config.img_prefix):]
    url = trim_serials(os.path.join(gallery_config.browse_prefix, rel_path))
    (base, url_ext) = os.path.splitext(url)
    if size != None:
        base = base + "_" + size
    if ext != None:
        url_ext = "." + ext
    return base + url_ext

    
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

def infer_image_path(base):
    for ext in img_extns:
        if os.path.exists(gallery_config.img_prefix + base + ext): return base + ext
    raise ValueError

def script_mtime():
    return max_mtime_for_files(scriptfiles)

def lmtime(fname):
    return os.lstat(fname)[stat.ST_MTIME]

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

def infer_serial_prefix(fname, infer_suffix = 0):
    fname = os.path.join(gallery_config.img_prefix, fname)
    if os.path.exists(fname): return fname[len(gallery_config.img_prefix):]
    (dir, basename) = os.path.split(fname)
    if not os.path.exists(dir):
        newdir = infer_serial_prefix(dir[len(gallery_config.img_prefix):])
        dir = os.path.join(gallery_config.img_prefix, newdir)
    candidates = os.listdir(dir)
    r = '^(\d+_)?' + ambiguate_filename(re.escape(basename))
    if infer_suffix:
        r += '(' + '|'.join(img_extns) + ')'
    r += '$'
    r = re.compile(r)
    found = [ f for f in candidates if r.search(f) != None ]
    if len(found) > 0: newbasename = found[0]
    else: newbasename = basename
    return os.path.join(dir, newbasename)[len(gallery_config.img_prefix):]

def copyIfPresent(dst, dstKey, src, srcKey):
    if src.has_key(srcKey):
        dst[dstKey] = src[srcKey]

def fractionToDecimal(fraction):
    pieces = fraction.split('/')
    if len(pieces) == 2:
        return str(float(pieces[0]) / float(pieces[1]))
    else:
        return fraction
    
def exifpage():
    fname = os.environ["PATH_INFO"][1:]
    img_index = fname.rfind('_')
    img_path = fname[:img_index]
    img_fname = os.path.join(gallery_config.img_prefix, infer_serial_prefix(img_path))

    f = open(img_fname, 'rb')
    tags = EXIF.process_file(f)
    f.close();
    image_mtime = lmtime(img_fname)
    if check_client_cache('text/html; charset="UTF-8"', image_mtime): return

    a = {}
    template = Template(file=scriptdir('exif.tmpl'), searchList=[a])
    #ambiguate this name?
    a['title'] = os.path.basename(img_fname)

    processedTags = {}
    #copy some of the simple tags

    #light source and metering mode need mappings
    copyIfPresent(processedTags, 'Light Source', tags, 'EXIF LightSource')
    copyIfPresent(processedTags, 'Metering Mode', tags, 'EXIF MeteringMode')
    copyIfPresent(processedTags, 'Date Time', tags, 'EXIF DateTimeOriginal')
    copyIfPresent(processedTags, 'Image Optimization', tags, 'MakerNote Image Optimization')
    copyIfPresent(processedTags, 'Hue Adjustment', tags, 'MakerNote HueAdjustment')
    copyIfPresent(processedTags, 'Exposure Time', tags, 'EXIF ExposureTime')
    copyIfPresent(processedTags, 'Exposure Program', tags, 'EXIF ExposureProgram')
    copyIfPresent(processedTags, 'Focus Mode', tags, 'MakerNote FocusMode')

    copyIfPresent(processedTags, 'AutoFlashMode', tags, 'MakerNote AutoFlashMode')
    copyIfPresent(processedTags, 'Image Sharpening', tags, 'MakerNote ImageSharpening')
    copyIfPresent(processedTags, 'Tone Compensation', tags, 'MakerNote ToneCompensation')
    copyIfPresent(processedTags, 'Flash', tags, 'EXIF Flash')
    copyIfPresent(processedTags, 'Lighting Type', tags, 'MakerNote LightingType')
    copyIfPresent(processedTags, 'Noise Reduction', tags, 'MakerNote NoiseReduction')
    copyIfPresent(processedTags, 'Flash Setting', tags, 'MakerNote FlashSetting')
    copyIfPresent(processedTags, 'Bracketing Mode', tags, 'MakerNote BracketingMode')
    copyIfPresent(processedTags, 'ISO Setting', tags, 'MakerNote ISOSetting')
    copyIfPresent(processedTags, 'FlashBracketCompensationApplied', tags, 'MakerNote FlashBracketCompensationApplied')
    copyIfPresent(processedTags, 'SubSecTimeOriginal', tags, 'EXIF SubSecTimeOriginal')
    copyIfPresent(processedTags, 'AFFocusPosition', tags, 'MakerNote AFFocusPosition')
    copyIfPresent(processedTags, 'WhiteBalanceBias', tags, 'MakerNote WhiteBalanceBias')
    copyIfPresent(processedTags, 'ExposureBiasValue', tags, 'EXIF ExposureBiasValue')
    copyIfPresent(processedTags, 'Whitebalance', tags, 'MakerNote Whitebalance')


    #Map various exif data

    #fractional
    if tags.has_key('EXIF FNumber'):
        processedTags['FNumber'] = fractionToDecimal(tags['EXIF FNumber'].printable)
    if tags.has_key('EXIF FocalLength'):
        processedTags['Focal Length'] = fractionToDecimal(tags['EXIF FocalLength'].printable)

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

def iscached(srcfile, cachefile):
    if not os.path.isfile(cachefile): return 0
    for dependency in [ srcfile ] + cache_dependencies:
        if lmtime(cachefile) < lmtime(dependency):
            return 0
    return 1 
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

def makedirsfor(fname):
    dirname = os.path.split(fname)[0]
    if not os.path.isdir(dirname): os.makedirs(dirname)

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

def img_size(fname, size):
    cachedir = "%s%d" % (gallery_config.cache_prefix, size)
    cachefile = cachedir + '/' + fname
    srcfile = gallery_config.img_prefix + fname
    if not iscached(srcfile, cachefile):
        return cache_img(fname, size, cachedir, cachefile, 0)
    else:
        img = Image.open(cachefile)
        return img.size

def cache_img(fname, size, cachedir, cachefile, do_output):
    img = Image.open(gallery_config.img_prefix + fname)
    f = open(gallery_config.img_prefix + fname, 'rb')
    tags = {}
    try: tags = EXIF.process_file(f)
    except: pass
    img.thumbnail((size,size), Image.ANTIALIAS)

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

def script_path():
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
        mtime = lmtime(fname)
        if mtime > max_mtime: max_mtime = mtime
    return max_mtime

def trim_serials(fn):
    return trim_serials_regexp.sub('', fn)

def format_fn_for_display(fn):
    if fn == '.': return gallery_config.short_name
    if fn.startswith('DSC_'): return ''
    fn = fn.replace('_', ' ')
    fn = fn.replace('~', '?')
    fn = fn.replace("'", '&rsquo;')
    fn = fn.replace('{o:}', '\xc3\xb6')
    fn = fn.replace('{a:}', '\xc3\xa4')
    return fn

def send_redirect(new_url):
    sys.stdout.write("Location: http://www.saturnvalley.org" + new_url + "\n\n")

def decompose_image_path(path):
    (path, fname) = os.path.split(path)
    (base, extn) = os.path.splitext(fname)
    base = degrade_filename(trim_serials(base))
    return (path, base, extn)

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
