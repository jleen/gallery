#!/usr/bin/env python2.2


import gallery_engine
import gallery_config
import re
import time
from Cheetah.Template import Template
import sys


galleryUrlRoot = "http://saturnvalley.org" + gallery_config.browse_prefix
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
                    dir = gallery_engine.format_fn_for_display(gallery_engine.trim_serials(dir))
                    if is_movie_dir:
                        dir += " - Movies"
                    current_entry['dir'].append((dir, url))
                else:
                    current_entry['desc'] += line

    src.close()
    return update_entries

recent_template = """<html>
<style>
body
{
    font-family: Georgia, Times New Roman, Times, serif;
    font-size: 90%;
    color: #333333;
    background-color: #eeeeee;
}
a
{
    text-decoration: none;
    color: #333399;
}
.datebox
{
}
.datebox h3
{
    font-size: medium;
    font-weight: 900;
    margin-bottom: 0;
}
.datecontents
{
    width: 90%;
    margin-left:5%;
    margin-right:5%;
}
.datetitles
{
    width: 90%;
    margin-left:3%;
    font-size: larger;
    font-weight: bold;
    margin-bottom:.5em;
    margin-top:1em;
}
.datecomment
{
    margin-left:6%;
    margin-right:5%;
    margin-bottom: 1.5em;
}
</style>
<head><title>$title</title></head>
<body>
#set lastDate = ""
#set firstTime = 1
<a href="."><b>$gallerytitle</b></a>
&gt;&gt;
<b>$title</b>

#if $nextLinkTitle
<br><br><i>(<a href="$nextLink">$nextLinkTitle)</a></i>
#end if

<br><br>
#for $entry in $updates
#if $lastDate != $entry['date']
#if not $firstTime
    </div> <!--end datebox-->
#else
#set firstTime = 0
#end if 
    <div class="datebox"><hr><h3>$entry['date']</h3>
#end if
#set lastDate = $entry['date']
<div class="datetitles">
#for $dirname, $url in $entry['dir']
<a href="$url">$dirname</a><br>
#end for
</div> <!--end datetitles-->
<div class="datecomment">
$entry['desc']
</div> <!--end datecomment-->
#else
    </div>
#end for
<!--
#if $nextLinkTitle
<br><br><h3><a href="$nextLink">$nextLinkTitle</a></h3>
#end if
-->
</body>
"""

def emitWhatsNew(template_str, update_entries, title_str, nextUrl, nextLinkName, filename):
    search = {}
    search['gallerytitle'] = gallery_config.short_name
    search['title'] = title_str
    search['updates'] = update_entries
    search['nextLinkTitle'] = nextLinkName
    search['nextLink'] = nextUrl
    template = Template(template_str, searchList=[search])

    f = open(filename, "w")
    f.write(str(template))
    f.close()



#main
update_entries = parseSrc(whatsNewSrc)
emitWhatsNew(recent_template, update_entries, "All Updates", None, None, whatsNewFull)

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

all_updates = "See all updates: " + str(len(update_entries)) + " entries"
emitWhatsNew(recent_template, update_entries[:idx], "Recent Updates",
             galleryUrlRoot + "whatsnew_all.html", all_updates,
             whatsNewShort)

#print update_entries

