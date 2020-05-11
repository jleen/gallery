# vim:sw=4:ts=4

import email.utils
import io
import os
import stat
import time

from PIL import Image, ImageDraw, ImageFont, ImageStat

from gallery import exif, paths


class NotModifiedException(Exception):
    pass


def scriptdir(fname):
    return os.path.join(os.path.split(__file__)[0], fname)


def normalize_date(date):
    if date is None:
        return None
    return time.asctime(time.gmtime(
            email.utils.mktime_tz(email.utils.parsedate_tz(date))))


def add_cache_headers(headers, server_date):
    if not server_date:
        return headers
    else:
        return headers + [('Last-Modified', server_date),
                          ('ETag', server_date)]


def check_client_cache(environ, ctime, config):
    # TODO(jleen): Factor in the template change time. Maybe just remember
    # when the app booted.
    if not config.get('ignore_client_cache', 0):
        client_date = None
        client_etag = None
        if 'HTTP_IF_MODIFIED_SINCE' in environ:
            client_date = environ['HTTP_IF_MODIFIED_SINCE'].strip()
            client_date = normalize_date(client_date)
        if 'HTTP_IF_NONE_MATCH' in environ:
            client_etag = environ['HTTP_IF_NONE_MATCH'].strip()

        server_date = time.asctime(time.gmtime(ctime))
        if (client_date == server_date and client_etag == server_date
                or client_date is None and client_etag == server_date
                or client_etag is None and client_date == server_date):
            raise NotModifiedException
        else:
            return server_date
    return None


def img_size(rel_image, max_size, config):
    abs_cachedir = os.path.join(config['cache_prefix'], "%d" % max_size)
    abs_cachefile = os.path.join(abs_cachedir, rel_image)
    abs_raw_image = paths.rel_to_abs(rel_image, config)
    try:
        if is_cached(abs_raw_image, abs_cachefile, config):
            cache_image = Image.open(abs_cachefile)
            return cache_image.size
        else:
            raw_image = Image.open(abs_raw_image)

            rotation_amount = 0
            if config.getboolean('apply_rotation', fallback=False):
                rotation_amount = compute_rotation_amount(
                        exif.exif_tags_raw(abs_raw_image), config)
            if (rotation_amount and
                    (rotation_amount == 90 or rotation_amount == -90)):
                (height, width) = raw_image.size  # swap them
            else:
                (width, height) = raw_image.size

            if width < max_size and height < max_size:
                return width, height
            if width > height:
                return max_size, (max_size * height) // width
            else:
                return (max_size * width) // height, max_size
    except IOError:
        return 50, 50


def is_cached(srcfile, cachefile, config):
    if not os.path.isfile(cachefile):
        return 0

    # In the config, we define the date at which we last manually expired the
    # cache.  If our cached copy is older than this, it's invalid.  Note that
    # the date format is that returned by /bin/date.

    fmt = '%a %b %d %H:%M:%S %Z %Y'
    exp_date = time.mktime(time.strptime(config['cache_expired'], fmt))
    if lctime(cachefile) < exp_date:
        return 0

    # And of course, if the source image has been changed more recently than
    # the cached copy, then the cache is stale.

    if lctime(cachefile) < lctime(srcfile):
        return 0

    return 1


def lctime(fname):
    return os.lstat(fname)[stat.ST_CTIME]


def makedirsfor(fname):
    dirname = os.path.split(fname)[0]
    if not os.path.isdir(dirname):
        os.makedirs(dirname)


def compute_rotation_amount(tags, config):
    rotation_amount = 0
    if config.getboolean('apply_rotation', fallback=False) and tags:
        orientation_tag = tags.get('Image Orientation')
        if orientation_tag is None:
            orientation_tag = ''
        else:
            orientation_tag = orientation_tag.printable

        if orientation_tag.startswith("Rotated 90 CW"):
            rotation_amount = -90
        elif orientation_tag.startswith("Rotated 90 CCW"):
            rotation_amount = 90
    return rotation_amount


def get_image_for_display(fname, config, width=0, height=0):
    img = Image.open(fname)
    tags = exif.exif_tags_raw(fname)

    if width > 0 and height > 0:
        img.thumbnail((width, height), Image.ANTIALIAS)
    else:
        (width, height) = img.size

    rotation_amount = compute_rotation_amount(tags, config)
    if rotation_amount:
        img = img.rotate(rotation_amount, Image.NEAREST, expand=True)

    try:
        copyright_name = config['copyright_name']
        copyright_font = config['copyright_font']
    except KeyError:
        copyright_name = None
        copyright_font = None

    if copyright_name and copyright_font and width > 200 and height > 200:
        if tags and tags.get('EXIF DateTimeOriginal'):
            dtstr = tags.get('EXIF DateTimeOriginal')
            dt = time.strptime(str(dtstr), '%Y:%m:%d %H:%M:%S')
            year = dt[0]
        else:
            year = 0  # use the ctime as a fallback
        copyright_string = '\N{COPYRIGHT SIGN} ' + str(year) + ' ' + config[
            'copyright_name']
        (imgwidth, imgheight) = img.size
        font = ImageFont.truetype(copyright_font, int(round(imgheight * .02)))

        draw = ImageDraw.Draw(img)
        # outline_value = "#000000"
        (textwidth, textheight) = draw.textsize(copyright_string, font=font)

        winset = imgwidth * .01
        hinset = imgheight * .01
        textstartw = imgwidth - textwidth - winset
        textstarth = imgheight - textheight - hinset

        # Create a mask image for the insanity of computing the inverse color
        # for the copyright image.
        mask = Image.new("1", (imgwidth, imgheight), 0)
        maskdraw = ImageDraw.Draw(mask)
        maskdraw.rectangle([
            (textstartw, textstarth),
            (textstartw + textwidth, textstarth + textheight)],
                fill=1)
        del maskdraw

        stats = ImageStat.Stat(img, mask)
        sketchy_counter = 0
        for band in stats.median:
            if band > 100:
                sketchy_counter += 1
            else:
                sketchy_counter -= 1

        if sketchy_counter > 0:
            fill_value = "#000000"
            shadow_fill_value = "#ffffff"
        else:
            fill_value = "#ffffff"
            shadow_fill_value = "#000000"

        drop_shadow_offset = int(round(textheight * 0.03))
        if drop_shadow_offset < 1:
            drop_shadow_offset = 1

        draw.text((
            textstartw + drop_shadow_offset,
            textstarth + drop_shadow_offset),
                copyright_string,
                fill=shadow_fill_value,
                font=font)
        draw.text(
                (textstartw, textstarth),
                copyright_string,
                fill=fill_value,
                font=font)
        del draw

    return img


def cache_img(rel, size, config):
    width = 0
    height = 0
    if size != "full":
        dims = size.split("x")
        width = int(dims[0])
        if len(dims) > 1:
            height = int(dims[1])
        else:
            height = width
    abs_cachedir = os.path.join(config['cache_prefix'], size)
    abs_cachefile = os.path.join(abs_cachedir, rel)
    abs_img = paths.rel_to_abs(rel, config)
    img = get_image_for_display(abs_img, config, width, height)

    with io.BytesIO() as buf:
        img.save(buf, "JPEG", quality=95)
        if os.path.isdir(abs_cachedir):
            makedirsfor(abs_cachefile)
            with open(abs_cachefile, 'wb') as fil:
                fil.write(buf.getvalue())
        return buf.getvalue()


def max_ctime_for_files(fnames):
    max_ctime = 0
    for fname in fnames:
        ctime = lctime(fname)
        if ctime > max_ctime:
            max_ctime = ctime
    return max_ctime
