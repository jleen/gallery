#!/usr/bin/env python2.2


import gallery_engine
import gallery_config
import re
import time
from Cheetah.Template import Template
import sys


whatsNewSrc = gallery_config.img_prefix + "/whatsnew.txt"
whatsNewShort = gallery_config.img_prefix + "/whatsnew.html"
whatsNewFull = gallery_config.img_prefix + "/whatsnew_all.html"



def parseSrc(src):
    src = open(src, "r")

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
                    url = "http://saturnvalley.org" + gallery_config.browse_prefix + dir
                    idx = dir.rfind('/')
                    if idx == -1:
                        idx = 0
                    else:
                        idx = idx + 1
                    dir = dir[idx:]
                    current_entry['dir'].append((dir, url))
                else:
                    current_entry['desc'] += line

    src.close()
    return update_entries

recent_template = """
<style>
body
{
    font-family: Georgia, Times New Roman, Times, serif;
    font-size: 90%;
    color: #333333;
    background-color: #eeeeee;
}
}
a
{
    text-decoration: none;
    color: #333333;
}
</style>
<html><head><title>$title</title></head>
<body>
#set lastDate = ""
<h2>$title</h2>
#for $entry in $updates
#if $lastDate != $entry['date']
    $entry['date']<br>
#end if
#set lastDate = $entry['date']
#for $dirname, $url in $entry['dir']
<a href=$url>$dirname</a><br>
#end for
$entry['desc']<br>
#end for
</body>
"""

def emitWhatsNew(template_str, update_entries, title_str, filename):
    search = {}
    search['title'] = title_str
    search['updates'] = update_entries
    template = Template(template_str, searchList=[search])

    f = open(filename, "w")
    f.write(str(template))
    f.close()



#main
update_entries = parseSrc(whatsNewSrc)
emitWhatsNew(recent_template, update_entries, "All Updates", whatsNewFull)

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

emitWhatsNew(recent_template, update_entries[:idx], "Recent Updates", whatsNewShort)

#print update_entries

