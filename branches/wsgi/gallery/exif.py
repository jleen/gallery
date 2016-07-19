# vim:sw=4:ts=4

from exif import EXIF

def copyIfPresent(dst, dstKey, src, srcKey):
    if srcKey in src:
        dst[dstKey] = src[srcKey]

def safe_divide(numer, denom):
    if denom == 0: return 0
    return numer / denom

def fractionToDecimal(fraction):
    pieces = fraction.split('/')
    if len(pieces) == 2:
        computed = safe_divide(float(pieces[0]), float(pieces[1]))
        if computed < 0.25001 and computed > 0:
            return '1/%d' % int(0.5 + (1/computed))
        else:
            return str(safe_divide(float(pieces[0]), float(pieces[1])))
    else:
        return fraction

def fractionToEntity(fractionStr):
    if fractionStr == '1/3':
        return '&#8531'
    elif fractionStr == '2/3':
        return '&#8532'
    elif fractionStr == '1/2':
        return '&frac12'
    else:
        return fractionStr

def improperToProper(fraction):
    pieces = fraction.split('/')
    if len(pieces) == 2:
        rational = safe_divide(float(pieces[0]), float(pieces[1]))
        if rational < 0:
            isNegative = 1
            rational = rational * -1.0
        else:
            isNegative = 0

        whole = int(rational)
        rational = rational - whole
        rational = rational * 1.00001 #sketchy round off avoidance
        if not rational:
            fractional = ' '
        elif int(rational*2.0)/(rational*2.0) > 0.999:
            fractional = '%d/2' % int(rational * 2)
        elif int(rational*3.0)/(rational*3.0) > 0.999:
            fractional = '%d/3' % int(rational * 3)
        else:
            fractional = '.3g' % rational
        final = ''
        if isNegative:
            final = final + '-'
        if whole != 0:
            final = final + str(whole)
            if not fractional.startswith('.') :
                final = final + ' '
        final = final + fractionToEntity(fractional)
        return final
    else:
        return fraction

def exif_tags_raw(img_fname):
    try:
        f = open(img_fname, 'rb')
        tags = EXIF.process_file(f)
        f.close()
    except:
        tags = None
    return tags

def exif_tags(img_fname):
    tags = exif_tags_raw(img_fname)
    if tags == None: return ()

    processedTags = {}
    #copy some of the simple tags

    #light source and metering mode need mappings
    copyIfPresent(processedTags, 'Light Source', tags, 'EXIF LightSource')
    copyIfPresent(processedTags, 'Metering Mode', tags, 'EXIF MeteringMode')
    copyIfPresent(processedTags, 'Date Time', tags, 'EXIF DateTimeOriginal')
    copyIfPresent(processedTags, 'Image Optimization',
            tags, 'MakerNote Image Optimization')
    copyIfPresent(processedTags, 'Hue Adjustment',
            tags, 'MakerNote HueAdjustment')
    if 'EXIF ExposureTime' in tags:
        processedTags['Shutter Speed'] = fractionToDecimal(
                tags['EXIF ExposureTime'].printable)
    if 'EXIF ExposureBiasValue' in tags:
        processedTags['Exposure Compensation'] = improperToProper(
                tags['EXIF ExposureBiasValue'].printable)

    copyIfPresent(processedTags, 'Exposure Program',
            tags, 'EXIF ExposureProgram')
    copyIfPresent(processedTags, 'Focus Mode',
            tags, 'MakerNote FocusMode')

    copyIfPresent(processedTags, 'AutoFlashMode',
            tags, 'MakerNote AutoFlashMode')
    copyIfPresent(processedTags, 'Image Sharpening',
            tags, 'MakerNote ImageSharpening')
    copyIfPresent(processedTags, 'Tone Compensation',
            tags, 'MakerNote ToneCompensation')
    copyIfPresent(processedTags, 'Flash',
            tags, 'EXIF Flash')
    copyIfPresent(processedTags, 'Lighting Type',
            tags, 'MakerNote LightingType')
    copyIfPresent(processedTags, 'Noise Reduction',
            tags, 'MakerNote NoiseReduction')
    copyIfPresent(processedTags, 'Flash Setting',
            tags, 'MakerNote FlashSetting')
    copyIfPresent(processedTags, 'Bracketing Mode',
            tags, 'MakerNote BracketingMode')
    copyIfPresent(processedTags, 'ISO Setting',
            tags, 'MakerNote ISOSetting')
    copyIfPresent(processedTags, 'FlashBracketCompensationApplied',
            tags, 'MakerNote FlashBracketCompensationApplied')
    copyIfPresent(processedTags, 'SubSecTimeOriginal',
            tags, 'EXIF SubSecTimeOriginal')
    copyIfPresent(processedTags, 'AFFocusPosition',
            tags, 'MakerNote AFFocusPosition')
    copyIfPresent(processedTags, 'WhiteBalanceBias',
            tags, 'MakerNote WhiteBalanceBias')
    copyIfPresent(processedTags, 'Whitebalance',
            tags, 'MakerNote Whitebalance')


    # Map various exif data.

    # Fractional...

    if 'EXIF FNumber' in tags:
        processedTags['FNumber'] = fractionToDecimal(
                tags['EXIF FNumber'].printable)
    if 'EXIF FocalLength' in tags:
        processedTags['Focal Length'] = fractionToDecimal(
                tags['EXIF FocalLength'].printable)
    return processedTags
