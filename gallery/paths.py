# vim:sw=4:ts=4

import re
import os
from typing import Dict, List

IMG_EXTNS = ['.jpeg', '.jpg', '.JPG']


class UnableToDisambiguateException(Exception):
    pass


def breadcrumbs_for_path(dir_fname, config, tuples):
    breadcrumbs = []
    dirname = ''
    for crumb in dir_fname.split(os.path.sep):
        if len(crumb) < 1:
            continue
        dirname = os.path.join(dirname, crumb)
        dir_url = rel_to_url(dirname, config, tuples, trailing_slash=1)
        # BUGBUG: Too many places know about '.' I think.  Can this be the only
        # place?
        if dirname == '.':
            display = config['short_name']
        else:
            display = format_for_display(os.path.split(dirname)[1])
        breadcrumbs.append([1, dir_url, display])
    # The last breadcrumb isn't a link.
    breadcrumbs[-1][0] = 0
    return breadcrumbs


def rel_to_abs(rel, config):
    return os.path.join(config['img_prefix'], rel)


def abs_to_rel(abs_path, config):
    return abs_path[len(config['img_prefix']):]


def abs_to_url(abs_path, config, tuples, size=None, ext=None):
    return rel_to_url(
            abs_to_rel(abs_path, config),
            config,
            tuples,
            size=size,
            ext=ext,
            trailing_slash=0)


def rel_to_url(
        rel, config, dirtuples, size=None, ext=None, trailing_slash=0):
    # First, break up the relative path and prepare each section of the url for
    # display.
    url = ""
    target_is_dir = os.path.isdir(rel_to_abs(rel, config))
    if rel.startswith(config['browse_prefix']):
        url += config['browse_prefix']
        rel = rel[len(config['browse_prefix']):]

    if target_is_dir:
        dirname = rel
        fname = ""
    else:
        (dirname, fname) = os.path.split(rel)
    abs_path = rel_to_abs("", config)
    components = dirname.split(os.path.sep)
    for component in components + [fname]:
        if not len(component):
            continue
        if component == '.':
            continue
        abs_path = os.path.join(abs_path, component)
        # Special case.  If component starts with a '.', then don't format it,
        # since we confuse the fname for an extension
        if component.startswith('.'):
            url = os.path.join(url, component)
        else:
            url = os.path.join(url, get_urlname_for_file(abs_path, dirtuples))
    url = os.path.join(config['browse_prefix'], url)

    (base, fname, url_ext) = split_path_ext(url)
    base = os.path.join(base, fname)
    if ext is not None:
        url_ext = "." + ext
    if size is not None:
        base = base + "_" + size
    url = base + url_ext
    if trailing_slash:
        url = os.path.join(url, '')
    return url


def infer_image_path(base, config):
    for ext in IMG_EXTNS:
        if os.path.exists(config['img_prefix'] + base + ext):
            return base + ext
    raise ValueError


def ambiguate_filename(fn):
    # This is horrifically bogus.  We should have a table or something.
    fn = fn.replace('{a:}', 'a')
    fn = fn.replace('{o:}', 'o')
    fn = fn.replace('{u:}', 'u')
    if fn.startswith('_'):
        fn = fn[1:]
    return fn.lower()


def degrade_filename(fn):
    # By a similar token, this function is a crock.
    fn = fn.replace('{a:}', 'a')
    fn = fn.replace('{o:}', 'o')
    fn = fn.replace('{u:}', 'u')
    fn = fn.replace('\N{LATIN SMALL LETTER A WITH DIAERESIS}', 'a')
    fn = fn.replace('\N{LATIN SMALL LETTER O WITH DIAERESIS}', 'o')
    fn = fn.replace('\N{LATIN SMALL LETTER U WITH DIAERESIS}', 'u')
    if fn.startswith('_'):
        fn = fn[1:]
    return fn


def url_to_abs(url, config, tuples, infer_suffix=0):
    rel = url_to_rel(url, config, tuples, infer_suffix=infer_suffix)
    return rel_to_abs(rel, config)


def url_to_rel(url, config, tuples, infer_suffix=0):
    fname = os.path.join(config['img_prefix'], url)

    # Handle the trivial case first
    if os.path.exists(fname):
        return fname[len(config['img_prefix']):]

    (dirname, basename) = os.path.split(fname)

    # Recursively try to disambiguate the parent directory
    if not os.path.exists(dirname):
        newdir = url_to_rel(dirname[len(config['img_prefix']):],
                            config, tuples)
        dirname = os.path.join(config['img_prefix'], newdir)

    # By induction, all but the leaf are now unambiguous.  So let's
    # disambiguate the leaf within the parent.
    newbasename = None  # basename
    tuples = get_directory_tuples(dirname, tuples,
                                  ignore_dotfiles=fname.startswith('.'))
    for dirtuple in tuples:
        amb_urlname = ambiguate_filename(dirtuple['urlname'])
        amb_basename = ambiguate_filename(basename)
        if infer_suffix:
            is_match = amb_urlname.startswith(amb_basename + '.')
        else:
            is_match = amb_urlname == amb_basename
        if is_match:
            newbasename = dirtuple['filename']
            break
    if not len(basename):
        newbasename = basename
    if newbasename is None:
        raise UnableToDisambiguateException
    return os.path.join(dirname, newbasename)[len(config['img_prefix']):]


trim_serials_regexp = re.compile('(^\d+[_ ]|(?<=/)\d+[_ ])')
remove_bracketed_stuff_regexp = re.compile('\[[^\]]*\]')
remove_brackets_regexp = re.compile('[\[\]]')


def trim_serials(path):
    return trim_serials_regexp.sub('', path)


def remove_bracketed_stuff(path):
    return remove_bracketed_stuff_regexp.sub('', path)


def remove_brackets(path):
    return remove_brackets_regexp.sub('', path)


def format_for_url(fn):
    fn = degrade_filename(fn)
    fn = trim_serials(fn)
    fn = remove_bracketed_stuff(fn)
    fn = fn.replace(' ', '_')
    fn = fn.replace('?', '~')
    fn = fn.replace('&rsquo;', "'")
    return fn


boring_filenames = ['DSC_', '_DSC', 'DSCF', 'CIMG', 'IMG_']


def format_for_display(fn):
    fn = trim_serials(fn)
    fn = remove_bracketed_stuff(fn)
    if fn[0:4] in boring_filenames:
        return ''
    if fn.startswith('JL') and fn[2].isdigit() and fn[3] == '_':
        return ''

    fn = fn.replace('_', ' ')
    fn = fn.replace('~', '?')
    fn = fn.replace("'", '&rsquo;')
    fn = fn.replace('{a:}', '\N{LATIN SMALL LETTER A WITH DIAERESIS}')
    fn = fn.replace('{o:}', '\N{LATIN SMALL LETTER O WITH DIAERESIS}')
    fn = fn.replace('{u:}', '\N{LATIN SMALL LETTER U WITH DIAERESIS}')
    return fn


def format_for_sort(fn):
    return remove_brackets(fn)


def split_path_ext(path):
    (path, base, extn) = split_path_ext_no_degrade(path)
    base = degrade_filename(trim_serials(base))
    return path, base, extn


def split_path_ext_no_degrade(path):
    (path, fname) = os.path.split(path)
    (base, extn) = os.path.splitext(fname)
    if not base and extn and fname.startswith('.'):
        base = extn
        extn = ""

    return path, base, extn


def dir_needs_tuples(dir_path):
    return os.path.exists(os.path.join(dir_path, ".dirinfo"))


def new_tuple_cache(): return {}


def get_directory_tuples(path, dir_tuple_cache,
                         ignore_dotfiles=1) -> List[Dict]:
    """
    returns a sorted sequence of dictionaries.  Each dictionary contains:
       sortkey -       The key to use for sorting
       filename -      The filename.
       displayname -   The display name for the file.
    """
    cache_key = path + " "
    # canonicalize the key
    if ignore_dotfiles:
        cache_key += "ignore_dotfiles"
    if cache_key in dir_tuple_cache:
        return dir_tuple_cache[cache_key]
    tuples = get_directory_tuples_internal(path, ignore_dotfiles)

    dir_tuple_cache[cache_key] = tuples

    return tuples


def get_directory_tuples_internal(path, ignore_dotfiles):
    """Parse the dirinfo file."""
    # print ("get_directory_tuples called for " + path +
    #        " with ignore_dotfiles " + str(ignore_dotfiles)
    dirinfo_entries = {}
    if os.path.exists(os.path.join(path, ".dirinfo")):
        dirinfo = open(os.path.join(path, ".dirinfo"), "r")
        for line in dirinfo:
            line = line.rstrip("\n")
            entry = line.split('|')
            sortkey = entry[0]
            fname = entry[1]
            if len(entry) == 3:
                displayname = entry[2]
            else:
                dirname = os.path.splitext(fname)[0]
                displayname = format_for_display(dirname)

            sortkey = sortkey + "_" + trim_serials(fname)
            dirinfo_entries[fname] = [sortkey, displayname]

        dirinfo.close()

    # Load the directory
    filenames = os.listdir(path)

    # create the tuples
    tuples = []
    for fname in filenames:
        (base, ext) = os.path.splitext(fname)
        if ignore_dotfiles:
            if base.startswith('.'):
                continue
            if fname.lower() == 'preview.jpg':
                continue

        if fname in dirinfo_entries:
            displayname = dirinfo_entries[fname][1]

            if len(displayname):
                urlname = format_for_url(displayname)
                url_ext = os.path.splitext(fname)[1]
                urlname += url_ext
            else:
                urlname = format_for_url(fname)
            dirtuple = {
                'sortkey': dirinfo_entries[fname][0], 'filename': fname,
                'displayname': dirinfo_entries[fname][1], 'urlname': urlname
            }
        else:
            if os.path.isdir(os.path.join(path, fname)):
                for_display = fname
            else:
                for_display = os.path.splitext(fname)[0]
            dirtuple = {
                'sortkey': format_for_sort(fname), 'filename': fname,
                'displayname': format_for_display(for_display),
                'urlname': format_for_url(fname)
            }
        tuples.append(dirtuple)
    tuples.sort(key=lambda x: x['sortkey'])
    return tuples


def get_name_for_file(full_fname, key, format_fn, tuples, use_ext):
    full_fname = full_fname.rstrip(os.path.sep)
    (dirname, fname, ext) = split_path_ext_no_degrade(full_fname)
    if not dir_needs_tuples(dirname):
        if use_ext:
            return format_fn(fname + ext)
        else:
            return format_fn(fname)

    # Obviously, this doesn't properly support dot directories
    ignore_dotfiles = not fname.startswith('.')
    dirtuples = get_directory_tuples(dirname, tuples, ignore_dotfiles)
    for dirtuple in dirtuples:
        if dirtuple['filename'].startswith(fname):
            return dirtuple[key]
    raise fname


def get_urlname_for_file(full_fname, tuples):
    return get_name_for_file(full_fname, 'urlname', format_for_url, tuples,
                             use_ext=1)


def get_displayname_for_file(full_fname, tuples):
    return get_name_for_file(full_fname, 'displayname', format_for_display,
                             tuples, use_ext=0)


def get_displayname_or_untitled(full_fname, tuples):
    name = get_displayname_for_file(full_fname, tuples)
    if len(name) == 0:
        name = '(untitled)'
    return name


def get_nearby_for_file(full_fname, tuples):
    (dir_path, fname) = os.path.split(full_fname)
    dirtuples = get_directory_tuples(dir_path, tuples)
    before = None
    after = None

    # Prune out all files with non-image extensions.
    new_tuples = []
    for dirtuple in dirtuples:
        ext = os.path.splitext(dirtuple['filename'])[1]
        if ext in IMG_EXTNS:
            new_tuples.append(dirtuple)

    tempiter = iter(new_tuples)
    while True:
        try:
            current = next(tempiter)
            if current['filename'].startswith(fname):
                after = next(tempiter)['filename']
                break
            else:
                before = current['filename']
        except StopIteration:
            break

    # Found the files.  Now make absolute names out of the before and after
    # that I found.

    if before:
        before = os.path.join(dir_path, before)
    if after:
        after = os.path.join(dir_path, after)

    return before, after
