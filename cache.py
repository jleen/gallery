# vim:sw=4:ts=4
# -*- coding: latin-1 -*-
from paths import *

import os
import rfc822
import stat
import time
import sys
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageStat
from StringIO import StringIO
import exif

def scriptdir(fname):
    return os.path.join(os.path.split(__file__)[0], fname)

cache_dependencies = [
    scriptdir('cache_sentinel')
]

def normalize_date(date):
    if date == None: return None
    return time.asctime(time.gmtime(
        rfc822.mktime_tz(rfc822.parsedate_tz(date))))

def check_client_cache(req, content_type, ctime):
    client_date = normalize_date(req.environ.get('HTTP_IF_MODIFIED_SINCE'))
    client_etag = req.environ.get('HTTP_IF_NONE_MATCH')
    server_date = time.asctime(time.gmtime(ctime))
    if (client_date == server_date and client_etag == server_date
            or client_date == None and client_etag == server_date
            or client_etag == None and client_date == server_date):
        req.set_header('Status', '304 Not Modified')
        return 1
    else:
        #content_type = 'text/plain'
        req.set_header('Content-type', content_type)
        req.set_header('Last-Modified', server_date)
        req.set_header('ETag', server_date)
        return 0

def img_size(rel_image, max_size, config):
    abs_cachedir = os.path.join(config['cache_prefix'], "%d" % max_size)
    abs_cachefile = os.path.join(abs_cachedir, rel_image)
    abs_raw_image = rel_to_abs(rel_image, config)
    try:
        if iscached(abs_raw_image, abs_cachefile):
            cache_image = Image.open(abs_cachefile)
            return cache_image.size
        else:
            raw_image = Image.open(abs_raw_image)

            #Here's the problem.  Without checking the EXIF tags, I can't
            #properly compute the dimensions.  However, if I do this step, the
            #server sometimes times out.
            rotation_amount = None
            #rotation_amount = compute_rotation_amount(exif.exif_tags_raw(abs_raw_image), config)
            if rotation_amount and (rotation_amount == 90 or rotation_amount == -90):
                (height, width) = raw_image.size #swap them
            else:
                (width, height) = raw_image.size

            if width < max_size and height < max_size: return (width, height)
            if width > height:
                return (max_size, (max_size * height) / width)
            else:
                return ((max_size * width) / height, max_size)
    except IOError: return (50, 50)

def iscached(srcfile, cachefile):
    if not os.path.isfile(cachefile): return 0
    for dependency in [ srcfile ] + cache_dependencies:
        if lctime(cachefile) < lctime(dependency):
            return 0
    return 1 

def lctime(fname):
    return os.lstat(fname)[stat.ST_CTIME]

def makedirsfor(fname):
    dirname = os.path.split(fname)[0]
    if not os.path.isdir(dirname): os.makedirs(dirname)

def compute_rotation_amount(tags, config):
    rotation_amount = 0
    if config['apply_rotation'] and tags:
        orientation_tag = tags.get('Image Orientation')
        if orientation_tag == None:
            orientation_tag = ''
        else:
            orientation_tag = orientation_tag.printable

        if orientation_tag.startswith("Rotated 90 CW"):
            rotation_amount = -90
        elif orientation_tag.startswith("Rotated 90 CCW"):
            rotation_amount = 90
    return rotation_amount

def get_image_for_display(fname, config, width = 0, height = 0):
    img = Image.open(fname)
    tags = exif.exif_tags_raw(fname)

    if width > 0 and height > 0:
        img.thumbnail((width,height), Image.ANTIALIAS)
    else:
        (width, height) = img.size

    rotation_amount = compute_rotation_amount(tags, config)
    if rotation_amount: img = img.rotate(rotation_amount, Image.NEAREST)

    try :
        copyright_name = config['copyright_name'] 
        copyright_font = config['copyright_font']
    except KeyError:
        copyright_name = None
        copyright_font = None

    if copyright_name and copyright_font and width > 200 and height > 200 :
        if tags and tags.get('EXIF DateTimeOriginal'):
            dtstr = tags.get('EXIF DateTimeOriginal')
            dt = time.strptime(str(dtstr), '%Y:%m:%d %H:%M:%S')
            year = dt[0]
        else:
            year = 0 #use the ctime as a fallback
        copyright_string = '� ' + str(year) + ' ' + config['copyright_name']
        (imgwidth, imgheight) = img.size;
        font = ImageFont.truetype( copyright_font, int(round(imgheight * .02)) )

        draw = ImageDraw.Draw(img)
        draw.setfont(font)
        #outline_value = "#000000"
        (textwidth, textheight) = draw.textsize(copyright_string)

        winset = imgwidth * .01
        hinset = imgheight * .01
        textstartw = imgwidth - textwidth - winset;
        textstarth = imgheight - textheight - hinset

        #create a mask image for the insanity of computing the inverse color
        #for the copyright image.
        mask = Image.new( "1", (imgwidth, imgheight), 0 )
        maskdraw = ImageDraw.Draw(mask)
        maskdraw.rectangle( [(textstartw, textstarth), (textstartw + textwidth, textstarth + textheight)], fill=1 )
        del maskdraw

        stats = ImageStat.Stat(img, mask)
        sketchy_counter = 0
        for band in stats.median:
            if band > 100 : sketchy_counter = sketchy_counter + 1
            else : sketchy_counter = sketchy_counter - 1

        if sketchy_counter > 0:
            fill_value = "#000000"
            shadow_fill_value = "#ffffff"
        else :
            fill_value = "#ffffff"
            shadow_fill_value = "#000000"

        drop_shadow_offset = int(round(textheight * 0.03))
        if drop_shadow_offset < 1: drop_shadow_offset = 1

        draw.text( (textstartw+drop_shadow_offset, textstarth+drop_shadow_offset), copyright_string, fill=shadow_fill_value )
        draw.text( (textstartw, textstarth), copyright_string, fill=fill_value )
        del draw

    return img


def cache_img(req, fname, width, height, cachedir, cachefile, do_output, config):

    img = get_image_for_display(config['img_prefix'] + fname, config, width, height)

    buf = StringIO()
    img.save(buf, "JPEG", quality = 95)
    if do_output:
        req.write(buf.getvalue())
    if os.path.isdir(cachedir):
        makedirsfor(cachefile)
        fil = file(cachefile, 'wb')
        fil.write(buf.getvalue())
        fil.close()
    buf.close()
    return img.size

def max_ctime_for_files(fnames):
    max_ctime = 0
    for fname in fnames:
        ctime = lctime(fname)
        if ctime > max_ctime: max_ctime = ctime
    return max_ctime

