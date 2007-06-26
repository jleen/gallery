# vim:sw=4:ts=4

import re
import time
from Cheetah.Template import Template
import sys
import os

import paths
import cache
import templates.whatsnewpage

def whatsnew_src_file(config):
    return os.path.join(config['img_prefix'], "whatsnew.txt")

def read_update_entries(fname, config, tuples):
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
                t = time.strptime(date_match.group(1))
                current_entry['date'] = time.strftime('%m-%d-%Y', t)
            else:
                dir_match = dir_expr.search(line)
                # REVIEW: Ambiguate and qualify?
                if dir_match:
                    dir = dir_match.group(1)
                    url = paths.rel_to_url(dir, config, tuples)
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
                    dir = paths.format_for_display(dir, config)
                    if is_movie_dir:
                        dir += " - Movies"
                    current_entry['dir'].append((dir, url))
                else:
                    current_entry['desc'] += line

    src.close()
    return update_entries


def spew_whats_new(
        req, update_entries, title_str, next_url, next_link_name, config):
    search = {}
    search['gallerytitle'] = config['short_name']
    search['title'] = title_str
    search['updates'] = update_entries
    search['nextLinkTitle'] = next_link_name
    search['nextLink'] = next_url
    template = templates.whatsnewpage.whatsnewpage(searchList = [search])

    search['browse_prefix'] = config['browse_prefix']
    req.write(str(template))


def spew_recent_whats_new(req, config, tuples):
    fname = whatsnew_src_file(config)
    update_entries = read_update_entries(fname, config, tuples)
    all_updates = "See all updates: " + str(len(update_entries)) + " entries"

    #slim it down to 10 entries or 3 days, whichever is greater
    #walk through the list.  Make sure never to take a partial day's entries
    #(i.e. only break out at the day change.
    entries = 0
    days = 0
    lastDate = update_entries[0]['date']
    while entries < len(update_entries):
        if update_entries[entries]['date'] != lastDate:
            lastDate = update_entries[entries]['date']
            days = days + 1
        if entries >= 10 and days >= 3:
            break
        entries = entries + 1



    cache.check_client_cache( req, 'text/html; charset="UTF-8"',
            cache.max_ctime_for_files([fname]))
    spew_whats_new(
            req,
            update_entries[:entries],
            "Recent Updates",
            os.path.join(config['browse_prefix'], "whatsnew_all.html"),
            all_updates,
            config)

def spew_all_whats_new(req, config, tuples):
    fname = whatsnew_src_file(config)
    update_entries = read_update_entries(fname, config, tuples)

    cache.check_client_cache( req, 'text/html; charset="UTF-8"',
            cache.max_ctime_for_files([fname]))

    spew_whats_new(req, update_entries, "All Updates", None, None, config)
