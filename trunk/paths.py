# vim:sw=4:ts=4
import re
import os

img_extns = ['.jpeg', '.jpg', '.JPG']

class UnableToDisambiguateException(Exception): pass

def breadcrumbs_for_path(dir_fname, final_is_link, config, tuples):
    breadcrumbs = []
    dirname = ''
    for crumb in (dir_fname).split(os.path.sep):
        if len(crumb) < 1: continue
        dirname = os.path.join(dirname, crumb)
        dir = rel_to_url(dirname, config, tuples, trailing_slash = 1)
        #BUGBUG Too many places know about '.' I think.  Can this be the only
        #place?
        if dirname == '.':
            display = format_for_display(dirname, config)
        else:
            display = format_for_display(os.path.split(dirname)[1], config)
        breadcrumbs.append([1, dir, display])
    # The last breadcrumb might not be a link
    breadcrumbs[-1][0] = final_is_link;
    return breadcrumbs

def rel_to_abs(rel, config):
    return os.path.join(config['img_prefix'], rel)

def abs_to_rel(abs, config):
    return abs[len(config['img_prefix']):]

def abs_to_url(abs, config, tuples, size = None, ext = None):
    return rel_to_url(
            abs_to_rel(abs, config),
            config,
            tuples,
            size = size,
            ext = ext,
            trailing_slash = 0)

def rel_to_url(rel, config, tuples, size = None, ext = None, trailing_slash = 0):
    #first, break up the relative path and prepare each section of the url for
    #display.
    url = ""
    target_is_dir = os.path.isdir(rel_to_abs(rel, config))
    if rel.startswith(config['browse_prefix']):
        url += config['browse_prefix'];
        rel = rel[len(config['browse_prefix']):]

    if target_is_dir:
        dir = rel
        fname = ""
    else:
        (dir, fname) = os.path.split(rel);
    abs = rel_to_abs("", config)
    components = dir.split(os.path.sep)
    for component in components + [fname]:
        if not len(component): continue
        if component == '.': continue
        abs = os.path.join(abs, component)
        #special case.  If component starts with a '.', then don't format it,
        #since we confuse the fname for an extension
        if component.startswith('.'):
            url = os.path.join( url, component )
        else:
            url = os.path.join( url, get_urlname_for_file(abs, config, tuples) )
    url = os.path.join(config['browse_prefix'], url )

    (base, fname, url_ext) = split_path_ext(url)
    base = os.path.join(base, fname)
    if ext != None:
        url_ext = "." + ext
    if size != None:
        base = base + "_" + size
    url = base + url_ext
    if trailing_slash:
        url = os.path.join(url, '')
    return url

def infer_image_path(base, config):
    for ext in img_extns:
        if os.path.exists(config['img_prefix'] + base + ext): return base + ext
    raise ValueError

def ambiguate_filename(fn):
    # This is horrifically bogus.  We should have a table or something.
    fn = fn.replace('{o:}', 'o')
    fn = fn.replace('{a:}', 'a')
    return fn.lower()

def degrade_filename(fn):
    # By a similar token, this function is a crock.
    fn = fn.replace('\xc3\xa4', 'a')
    fn = fn.replace('\xc3\xb6', 'o')
    return fn

def url_to_abs(url, config, tuples, infer_suffix = 0):
    return rel_to_abs(url_to_rel(url, config, tuples, infer_suffix = infer_suffix), config)

def url_to_rel(url, config, tuples, infer_suffix = 0):
    fname = os.path.join(config['img_prefix'], url)
    
    # Handle the trivial case first
    if os.path.exists(fname): return fname[len(config['img_prefix']):]

    (dir, basename) = os.path.split(fname)

    # Recursively try to disambiguate the parent directory
    if not os.path.exists(dir):
        newdir = url_to_rel(dir[len(config['img_prefix']):], config, tuples)
        dir = os.path.join(config['img_prefix'], newdir)

    # By induction, all but the leaf are now unambiguous.  So let's
    # disambiguate the leaf within the parent.
    newbasename = None #basename
    tuples = get_directory_tuples(dir, config, tuples, ignore_dotfiles = fname.startswith('.'))
    for tuple in tuples:
        amb_urlname = ambiguate_filename(tuple['urlname'])
        amb_basename = ambiguate_filename(basename)
        if infer_suffix:
            is_match = amb_urlname.startswith(amb_basename)
        else:
            is_match = amb_urlname == amb_basename
        if is_match:
            newbasename = tuple['filename']
            break
    if not len(basename):
        newbasename = basename
    if newbasename == None:
        raise UnableToDisambiguateException
    return os.path.join(dir, newbasename)[len(config['img_prefix']):]


trim_serials_regexp = re.compile('(^\d+_|(?<=/)\d+_)')

def trim_serials(path):
    return trim_serials_regexp.sub('', path)

def format_for_url(fn, this_param_is_ignored):
    fn = degrade_filename(fn)
    fn = trim_serials(fn)
    fn = fn.replace(' ', '_')
    fn = fn.replace('?', '~')
    fn = fn.replace('&rsquo;', "'",)
    fn = fn.replace('\xc3\xb6', '{o:}' )
    fn = fn.replace('\xc3\xa4', '{a:}' )
    return fn

def format_for_display(fn, config):
    fn = trim_serials(fn)
    if fn == '.': return config['short_name']
    if fn.startswith('DSC_'): return ''
    if fn.startswith('_DSC'): return ''
    if fn.startswith('CIMG'): return ''
    if fn.startswith('IMG_'): return ''
    fn = fn.replace('_', ' ')
    fn = fn.replace('~', '?')
    fn = fn.replace("'", '&rsquo;')
    fn = fn.replace('{o:}', '\xc3\xb6')
    fn = fn.replace('{a:}', '\xc3\xa4')
    return fn

def split_path_ext(path):
    (path, base, extn) = split_path_ext_no_degrade(path)
    base = degrade_filename(trim_serials(base))
    return (path, base, extn)

def split_path_ext_no_degrade(path):
    (path, fname) = os.path.split(path)
    (base, extn) = os.path.splitext(fname)
    if len(base) == 0 and len(extn) > 0 and fname.startswith('.'):
        base = extn
        extn = ""

    return (path, base, extn)

def dirent_compare(lhs, rhs):
    lhsKey = lhs['sortkey']
    rhsKey = rhs['sortkey']
    if lhsKey < rhsKey: return -1
    if lhsKey > rhsKey: return 1
    return 0

def dir_needs_tuples(dir_path):
    return os.path.exists(os.path.join(dir_path, ".dirinfo"))

def new_tuple_cache(): return {}

#returns a sorted sequence of dictionaries.  Each dictionary contains:
#   sortkey -       The key to use for sorting
#   filename -      The filename.
#   displayname -   The display name for the file.
def get_directory_tuples(path, config, dir_tuple_cache, ignore_dotfiles = 1):
    cache_key = path + " "
    #canonicalize the key
    if ignore_dotfiles:
        cache_key = cache_key + "ignore_dotfiles"
    if dir_tuple_cache.has_key(cache_key):
        return dir_tuple_cache[cache_key]
    tuples = get_directory_tuples_internal(path, ignore_dotfiles, config)

    dir_tuple_cache[cache_key] = tuples

    return tuples

def get_directory_tuples_internal(path, ignore_dotfiles, config):
    #print "get_directory_tuples called for " + path + " with ignore_dotfiles " + str(ignore_dotfiles)
    #parse the dirinfo file
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
                displayname = format_for_display(os.path.splitext(fname)[0], config)

            sortkey = sortkey + "_" + trim_serials(fname)
            dirinfo_entries[fname] = [sortkey, displayname]

        dirinfo.close()

    # Load the directory
    filenames = os.listdir(path)

    #create the tuples
    tuples = []
    for fname in filenames:
        (base, ext) = os.path.splitext(fname)
        if ignore_dotfiles:
            if base.startswith('.'): continue
            if fname.lower() == 'preview.jpg': continue

        if dirinfo_entries.has_key(fname):
            displayname = dirinfo_entries[fname][1]

            if len(displayname):
                urlname = format_for_url(displayname, None)
                url_ext = os.path.splitext(fname)[1]
                urlname = urlname + url_ext
            else:
                urlname = format_for_url(fname, None)
            tuple = {'sortkey':dirinfo_entries[fname][0], 'filename':fname, 'displayname':dirinfo_entries[fname][1], 'urlname':urlname }
        else:
            for_display = ''
            if os.path.isdir(os.path.join(path, fname)):
                for_display = fname
            else:
                for_display = os.path.splitext(fname)[0]
            tuple = {'sortkey':fname, 'filename':fname, 'displayname':format_for_display(for_display, config), 'urlname':format_for_url(fname, None)}
        tuples.append(tuple)
    tuples.sort(dirent_compare)
    return tuples

def get_name_for_file(full_fname, key, format_fn, config, tuples, use_ext):
    (dir, fname, ext) = split_path_ext_no_degrade(full_fname.rstrip(os.path.sep))
    if not dir_needs_tuples(dir):
        if use_ext: return format_fn(fname + ext, config)
        else: return format_fn(fname, config)

    #Obviously, this doesn't properly support dot directories
    dirtuples = get_directory_tuples(dir, config, tuples, ignore_dotfiles = (not fname.startswith('.')))
    for tuple in dirtuples:
        if tuple['filename'].startswith(fname):
            return tuple[key]
    raise fname
    return None #Never reached.

def get_urlname_for_file(full_fname, config, tuples):
    return get_name_for_file(full_fname, 'urlname', format_for_url, config, tuples, use_ext = 1)

def get_displayname_for_file(full_fname, config, tuples):
    return get_name_for_file(full_fname, 'displayname', format_for_display, config, tuples, use_ext = 0)

def get_nearby_for_file(full_fname, config, tuples):
    (dir, fname) = os.path.split(full_fname);
    dirtuples = get_directory_tuples(dir, config, tuples)
    before = None
    after = None

    #prune out all files with non-image extensions
    newtuples = []
    for tuple in dirtuples:
        ext = os.path.splitext(tuple['filename'])[1]
        if ext in img_extns: newtuples.append(tuple)

    tempiter = iter(newtuples)
    while True:
        try:
            current = tempiter.next()
            current_fname = current['filename']
            if current['filename'].startswith(fname):
                after = tempiter.next()['filename']
                break
            else:
                before = current['filename']
        except StopIteration: break
    
    #Found the files.  Now make absolute names out of the before and after that
    #I found
    if before: before = os.path.join(dir, before)
    if after: after = os.path.join(dir, after)

    return (before, after)
