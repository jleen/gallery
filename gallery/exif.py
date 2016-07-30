# vim:sw=4:ts=4

import exifread


def copy_if_present(dst, dst_key, src, src_key):
    if src_key in src:
        dst[dst_key] = src[src_key]


def safe_divide(numer, denom):
    if denom == 0:
        return 0
    return numer / denom


def fraction_to_decimal(fraction):
    pieces = fraction.split('/')
    if len(pieces) == 2:
        computed = safe_divide(float(pieces[0]), float(pieces[1]))
        if 0.25001 > computed > 0:
            return '1/%d' % int(0.5 + (1 / computed))
        else:
            return str(safe_divide(float(pieces[0]), float(pieces[1])))
    else:
        return fraction


def fraction_to_entity(fraction_str):
    if fraction_str == '1/3':
        return '&#8531'
    elif fraction_str == '2/3':
        return '&#8532'
    elif fraction_str == '1/2':
        return '&frac12'
    else:
        return fraction_str


def improper_to_proper(fraction):
    pieces = fraction.split('/')
    if len(pieces) == 2:
        rational = safe_divide(float(pieces[0]), float(pieces[1]))
        if rational < 0:
            is_negative = 1
            rational *= -1.0
        else:
            is_negative = 0

        whole = int(rational)
        rational -= whole
        rational *= 1.00001  # sketchy round off avoidance
        if not rational:
            fractional = ' '
        elif int(rational * 2.0) / (rational * 2.0) > 0.999:
            fractional = '%d/2' % int(rational * 2)
        elif int(rational * 3.0) / (rational * 3.0) > 0.999:
            fractional = '%d/3' % int(rational * 3)
        else:
            fractional = '%.3g' % rational
        final = ''
        if is_negative:
            final += '-'
        if whole != 0:
            final += str(whole)
            if not fractional.startswith('.'):
                final += ' '
        final += fraction_to_entity(fractional)
        return final
    else:
        return fraction


def exif_tags_raw(img_fname):
    try:
        with open(img_fname, 'rb') as f:
            tags = exifread.process_file(f)
    except IOError:
        tags = None
    return tags


def exif_tags(img_fname):
    tags = exif_tags_raw(img_fname)
    if tags is None:
        return ()

    processed_tags = {}
    # copy some of the simple tags

    # light source and metering mode need mappings
    copy_if_present(processed_tags, 'Light Source', tags, 'EXIF LightSource')
    copy_if_present(processed_tags, 'Metering Mode', tags, 'EXIF MeteringMode')
    copy_if_present(processed_tags, 'Date Time', tags, 'EXIF DateTimeOriginal')
    copy_if_present(processed_tags, 'Image Optimization',
                    tags, 'MakerNote Image Optimization')
    copy_if_present(processed_tags, 'Hue Adjustment',
                    tags, 'MakerNote HueAdjustment')
    if 'EXIF ExposureTime' in tags:
        processed_tags['Shutter Speed'] = fraction_to_decimal(
                tags['EXIF ExposureTime'].printable)
    if 'EXIF ExposureBiasValue' in tags:
        processed_tags['Exposure Compensation'] = improper_to_proper(
                tags['EXIF ExposureBiasValue'].printable)

    copy_if_present(processed_tags, 'Exposure Program',
                    tags, 'EXIF ExposureProgram')
    copy_if_present(processed_tags, 'Focus Mode',
                    tags, 'MakerNote FocusMode')

    copy_if_present(processed_tags, 'AutoFlashMode',
                    tags, 'MakerNote AutoFlashMode')
    copy_if_present(processed_tags, 'Image Sharpening',
                    tags, 'MakerNote ImageSharpening')
    copy_if_present(processed_tags, 'Tone Compensation',
                    tags, 'MakerNote ToneCompensation')
    copy_if_present(processed_tags, 'Flash',
                    tags, 'EXIF Flash')
    copy_if_present(processed_tags, 'Lighting Type',
                    tags, 'MakerNote LightingType')
    copy_if_present(processed_tags, 'Noise Reduction',
                    tags, 'MakerNote NoiseReduction')
    copy_if_present(processed_tags, 'Flash Setting',
                    tags, 'MakerNote FlashSetting')
    copy_if_present(processed_tags, 'Bracketing Mode',
                    tags, 'MakerNote BracketingMode')
    copy_if_present(processed_tags, 'ISO Setting',
                    tags, 'MakerNote ISOSetting')
    copy_if_present(processed_tags, 'FlashBracketCompensationApplied',
                    tags, 'MakerNote FlashBracketCompensationApplied')
    copy_if_present(processed_tags, 'SubSecTimeOriginal',
                    tags, 'EXIF SubSecTimeOriginal')
    copy_if_present(processed_tags, 'AFFocusPosition',
                    tags, 'MakerNote AFFocusPosition')
    copy_if_present(processed_tags, 'WhiteBalanceBias',
                    tags, 'MakerNote WhiteBalanceBias')
    copy_if_present(processed_tags, 'Whitebalance',
                    tags, 'MakerNote Whitebalance')

    # Map various exif data.

    # Fractional...

    if 'EXIF FNumber' in tags:
        processed_tags['FNumber'] = fraction_to_decimal(
                tags['EXIF FNumber'].printable)
    if 'EXIF FocalLength' in tags:
        processed_tags['Focal Length'] = fraction_to_decimal(
                tags['EXIF FocalLength'].printable)
    return processed_tags
