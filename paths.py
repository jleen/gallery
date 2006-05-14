import gallery_config

import re
import os

img_extns = ['.jpeg', '.jpg', '.JPG']

def breadcrumbs_for_path(dir_fname, final_is_link):
    breadcrumbs = []
    dirname = ''
    for crumb in (dir_fname).split(os.path.sep):
        if len(crumb) < 1: continue
        dirname = os.path.join(dirname, crumb)
        dir = os.path.join(gallery_config.browse_prefix, trim_serials(dirname), '')
        display = format_fn_for_display(trim_serials(crumb))
        breadcrumbs.append([1, dir, display])
    # The last breadcrumb might not be a link
    breadcrumbs[-1][0] = final_is_link;
    return breadcrumbs

def path_to_url(path, size = None, ext = None):
    rel_path = path[len(gallery_config.img_prefix):]
    url = trim_serials(os.path.join(gallery_config.browse_prefix, rel_path))
    (base, url_ext) = os.path.splitext(url)
    if size != None:
        base = base + "_" + size
    if ext != None:
        url_ext = "." + ext
    return base + url_ext

def infer_image_path(base):
    for ext in img_extns:
        if os.path.exists(gallery_config.img_prefix + base + ext): return base + ext
    raise ValueError

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


trim_serials_regexp = re.compile('(^\d+_|(?<=/)\d+_)')

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

def decompose_image_path(path):
    (path, fname) = os.path.split(path)
    (base, extn) = os.path.splitext(fname)
    base = degrade_filename(trim_serials(base))
    return (path, base, extn)

