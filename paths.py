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
        dir = rel_to_url(dirname, trailing_slash = 1)
        display = format_for_display(crumb)
        breadcrumbs.append([1, dir, display])
    # The last breadcrumb might not be a link
    breadcrumbs[-1][0] = final_is_link;
    return breadcrumbs

def rel_to_abs(rel):
    return os.path.join(gallery_config.img_prefix, rel)

def abs_to_rel(abs):
    return abs[len(gallery_config.img_prefix):]

def abs_to_url(abs, size = None, ext = None):
    return rel_to_url(
            abs_to_rel(abs),
            size = size,
            ext = ext,
            trailing_slash = 0)

def rel_to_url(rel, size = None, ext = None, trailing_slash = 0):
    url = trim_serials(os.path.join(gallery_config.browse_prefix, rel))
    (base, url_ext) = os.path.splitext(url)
    if size != None:
        base = base + "_" + size
    if ext != None:
        url_ext = "." + ext
    if trailing_slash:
        url_ext = os.path.join(url_ext, '')
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

def url_to_abs(url, infer_suffix = 0):
    return rel_to_abs(url_to_rel(url, infer_suffix = infer_suffix))

def url_to_rel(url, infer_suffix = 0):
    fname = os.path.join(gallery_config.img_prefix, url)
    
    # Handle the trivial case first
    if os.path.exists(fname): return fname[len(gallery_config.img_prefix):]

    (dir, basename) = os.path.split(fname)

    # Recursively try to disambiguate the parent directory
    if not os.path.exists(dir):
        newdir = url_to_rel(dir[len(gallery_config.img_prefix):])
        dir = os.path.join(gallery_config.img_prefix, newdir)

    # By induction, all but the leaf are now unambiguous.  So let's
    # disambiguate the leaf within the parent.
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

def trim_serials(path):
    return trim_serials_regexp.sub('', path)

def format_for_display(fn):
    fn = trim_serials(fn)
    if fn == '.': return gallery_config.short_name
    if fn.startswith('DSC_'): return ''
    fn = fn.replace('_', ' ')
    fn = fn.replace('~', '?')
    fn = fn.replace("'", '&rsquo;')
    fn = fn.replace('{o:}', '\xc3\xb6')
    fn = fn.replace('{a:}', '\xc3\xa4')
    return fn

def split_path_ext(path):
    (path, fname) = os.path.split(path)
    (base, extn) = os.path.splitext(fname)
    base = degrade_filename(trim_serials(base))
    return (path, base, extn)

