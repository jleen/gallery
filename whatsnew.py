# vim:sw=4:ts=4

import re
import time
from Cheetah.Template import Template
import sys
import os

import paths
import cache
import gallery_config

galleryUrlRoot = "http://saturnvalley.org" + gallery_config.browse_prefix
whatsNewSrc = gallery_config.img_prefix + "/whatsnew.txt"
whatsNewShort = gallery_config.img_prefix + "/whatsnew.html"
whatsNewFull = gallery_config.img_prefix + "/whatsnew_all.html"


def whatsnew_src_file():
    return os.path.join(gallery_config.img_prefix, "whatsnew.txt")

def read_update_entries(fname):
    src = open(fname, "r")

    update_entries = []
    date_expr = re.compile('^DATE\s+(.*)$')
    dir_expr = re.compile('^DIR\s+(.*)$')
    for line in src:
        if line.startswith('START'):
            current_entry = {}
            current_entry['dir'] = []
            current_entry['desc'] = ''
        elif line.startswith('END'):
            update_entries.append(current_entry)
        else:
            date_match = date_expr.search(line)
            if date_match:
                current_entry['date'] = time.strftime( '%m-%d-%Y', time.strptime(date_match.group(1)) )
            else:
                dir_match = dir_expr.search(line)
            #ambiguate and qualify?
                if dir_match:
                    dir = dir_match.group(1)
                    url = galleryUrlRoot + dir
                    is_movie_dir = 0
                    if dir.endswith('Movies'):
                        is_movie_dir = 1
                        dir = dir[0:dir.rfind('/')]
                    idx = dir.rfind('/')
                    if idx == -1:
                        idx = 0
                    else:
                        idx = idx + 1
                    dir = dir[idx:]
                    dir = paths.format_for_display(dir)
                    if is_movie_dir:
                        dir += " - Movies"
                    current_entry['dir'].append((dir, url))
                else:
                    current_entry['desc'] += line

    src.close()
    return update_entries


def spew_whats_new(update_entries, title_str, next_url, next_link_name):
    search = {}
    search['gallerytitle'] = gallery_config.short_name
    search['title'] = title_str
    search['updates'] = update_entries
    search['nextLinkTitle'] = next_link_name
    search['nextLink'] = next_url
    template = Template(file=cache.scriptdir('whatsnewpage.tmpl'), searchList=[search])

    sys.stdout.write(str(template))


def spew_recent_whats_new():
    fname = whatsnew_src_file()
    update_entries = read_update_entries(fname)
    all_updates = "See all updates: " + str(len(update_entries)) + " entries"
    #slim it down to 10 entries
    if len(update_entries) > 10:
        idx = 9
        lastDate = update_entries[idx]['date']
        while idx < len(update_entries):
            if update_entries[idx]['date'] != lastDate:
                break;
            idx = idx + 1;
    else:
        idx = len(update_entries)

    if cache.check_client_cache( 'text/html; charset="UTF-8"',
            cache.max_mtime_for_files([fname])):
        return
    spew_whats_new(update_entries[:idx], "Recent Updates", "http://saturnvalley.org" + (os.path.join(gallery_config.browse_prefix, "whatsnew_all.html")), all_updates)

def spew_all_whats_new():
    fname = whatsnew_src_file()
    update_entries = read_update_entries(fname)

    if cache.check_client_cache( 'text/html; charset="UTF-8"',
            cache.max_mtime_for_files([fname])):
        return

    spew_whats_new(update_entries, "All Updates", None, None)

