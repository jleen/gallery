# vim:sw=4:ts=4

import os
import re
import time
import xml
from typing import Dict, List

from gallery import cache, paths


def whatsnew_src_file(config):
    return os.path.join(config['img_prefix'], "whatsnew.txt")


def read_update_entries(fname, config, tuples) -> List[Dict]:
    src = open(fname, "r", encoding='utf-8')

    update_entries = []
    date_expr = re.compile('^DATE\s+(.*)$')
    dir_expr = re.compile('^DIR\s+(.*)$')
    for line in src:
        if line.startswith('START'):
            current_entry = {'dir': [], 'desc': ''}
        elif line.startswith('END'):
            update_entries.append(current_entry)
        else:
            date_match = date_expr.search(line)
            if date_match:
                t = time.strptime(date_match.group(1), '%a %b %d %H:%M:%S %Y')
                current_entry['date'] = time.strftime('%m-%d-%Y', t)
                # +0000 is wrong, but the what's new file doesn't have a TZ in
                # it.  Perhaps I should just fabricate one from the current
                # timezone.
                current_entry['date_822'] = time.strftime(
                    "%a, %d %b %Y %H:%M:%S +0000", t)
            else:
                dir_match = dir_expr.search(line)
                # REVIEW: Ambiguate and qualify?
                if dir_match:
                    dirname = dir_match.group(1)
                    url = paths.rel_to_url(dirname, config, tuples,
                                           trailing_slash=1)
                    is_movie_dir = 0
                    if dirname.endswith('Movies'):
                        is_movie_dir = 1
                        dirname = dirname[0:dirname.rfind('/')]
                    idx = dirname.rfind('/')
                    if idx == -1:
                        idx = 0
                    else:
                        idx += 1
                    dirname = dirname[idx:]
                    dirname = paths.format_for_display(dirname, config)
                    if is_movie_dir:
                        dirname += " - Movies"
                    current_entry['dir'].append((dirname, url))
                else:
                    current_entry['desc'] += line

    src.close()
    return update_entries


def spew_whats_new(
        start_response, update_entries, title_str, next_url,
        next_link_name, config, jenv, server_date):
    search = {
        'gallerytitle': config['short_name'], 'title': title_str,
        'updates': update_entries, 'nextLinkTitle': next_link_name,
        'nextLink': next_url
        }
    template = jenv.get_template('whatsnewpage.html.jj')

    search['browse_prefix'] = config['browse_prefix']
    start_response('200 OK', cache.add_cache_headers(
            [('Content-Type', 'text/html; charset="UTF-8"')], server_date))
    return [template.render(search).encode('utf-8')]


def spew_recent_whats_new(environ, start_response, config, tuples, jenv):
    fname = whatsnew_src_file(config)
    update_entries = read_update_entries(fname, config, tuples)
    all_updates = "See all updates: " + str(len(update_entries)) + " entries"

    # slim it down to 10 entries or 3 days, whichever is greater
    # walk through the list.  Make sure never to take a partial day's entries
    # (i.e. only break out at the day change.
    entries = 0
    days = 0
    last_date = update_entries[0]['date']
    while entries < len(update_entries):
        if update_entries[entries]['date'] != last_date:
            last_date = update_entries[entries]['date']
            days += 1
        if entries >= 10 and days >= 3:
            break
        entries += 1

    server_date = cache.check_client_cache(
            environ, cache.max_ctime_for_files([fname]), config)

    return spew_whats_new(
            start_response,
            update_entries[:entries],
            "Recent Updates",
            os.path.join(config['browse_prefix'], "whatsnew_all.html"),
            all_updates,
            config, jenv, server_date)


def spew_all_whats_new(environ, start_response, config, tuples, jenv):
    fname = whatsnew_src_file(config)
    update_entries = read_update_entries(fname, config, tuples)

    server_date = cache.check_client_cache(
            environ, cache.max_ctime_for_files([fname]), config)

    return spew_whats_new(
            start_response, update_entries, "All Updates",
            None, None, config, jenv, server_date)


def spew_whats_new_rss(environ, start_response, config, tuples, jenv):
    fname = whatsnew_src_file(config)
    update_entries = read_update_entries(fname, config, tuples)

    server_date = cache.check_client_cache(environ,
                                           cache.max_ctime_for_files([fname]),
                                           config)

    search = {
        'gallerytitle': xml_escape(config['short_name']),
        'title': xml_escape(config['long_name']),
        'updates': update_entries
        }

    # ok, since this is going into xml, html unescape the entries and then xml
    # escape them.  Good thing that python doesn't have library functions for
    # html unescaping.
    #
    # Do the escaping in the filter
    #
    # Oh yea, and the dirnames need to be unescaped too.  Sweet.

    for entry in update_entries:
        entry['desc'] = xml_escape(html_unescape(entry['desc']))
        entry['dir'] = [
            [xml_escape(html_unescape(tup[0])), xml_escape(tup[1])]
            for tup in entry['dir']]

    template = jenv.get_template('whatsnewrss.xml.jj')

    search['browse_prefix'] = xml_escape(config['browse_prefix'])
    search['hostname'] = "www.saturnvalley.org"
    start_response('200 OK', cache.add_cache_headers(
            [('Content-Type', 'text/xml; charset="UTF-8"')], server_date))
    return [template.render(search).encode('utf-8')]


def html_unescape(s):
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    s = s.replace("&apos;", "'")
    s = s.replace("&quot;", '"')
    s = s.replace("&rsquo;", "'")
    s = s.replace("&amp;", "&")  # Must be last
    return s


def xml_escape(val):
    if val is None:
        return ''
    return xml.sax.saxutils.escape(str(val))
