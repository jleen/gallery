#!/usr/bin/env python2.4
# vim:sw=4:ts=4


import sys
sys.path.insert(0, '/home/jmleen/lib/python2.4/site-packages')
print sys.argv[1] + '\n'
sys.path.insert(0, sys.argv[1])

import handler
import gallery_config
import paths
import cache

import os
import time

total_created = 0

cache_sizes = ["700x500", handler.thumb_size]
preview_size = handler.preview_size


for root, dirs, files in os.walk(gallery_config.img_prefix):
    for name in files:
        if paths.split_path_ext(name)[2] not in paths.img_extns:
            continue
        abs = os.path.join(root, name)
        #if there is no preview, I don't cache the preview thumbnail.
        if name == ".preview.jpeg" or name.lower() == "preview.jpg":
            check_sizes = [preview_size]
        else:
            check_sizes = cache_sizes

        for size in check_sizes:
            rel = paths.abs_to_rel(abs)
            abs_cachedir = os.path.join(gallery_config.cache_prefix, size)
            abs_cachefile = os.path.join(abs_cachedir, rel)

            if cache.is_cached(abs, abs_cachefile, config):
                print abs + '(' + size + ") is up to date"
            else:
                dims = size.split("x")
                width = int(dims[0])
                if len(dims) > 1: height = int(dims[1])
                else: height = width

                print "caching " + rel + "(" + str(width) + ", " + str(height) + ")"
                cache.cache_img(rel, width, height, abs_cachedir, abs_cachefile, 0)
                #print "calling cache_img(\"" + str(rel) + "\", \"" + str(width) + "\", \"" + str(height) + "\", \"" + str(abs_cachedir) + "\", \"" + str(abs_cachefile) + "\", 0)"
                total_created = total_created + 1
                time.sleep(1)
                if total_created > 20:
                    sys.exit(1)

                pass
