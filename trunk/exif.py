def copyIfPresent(dst, dstKey, src, srcKey):
    if src.has_key(srcKey):
        dst[dstKey] = src[srcKey]

def fractionToDecimal(fraction):
    pieces = fraction.split('/')
    if len(pieces) == 2:
        return str(float(pieces[0]) / float(pieces[1]))
    else:
        return fraction
    

def exif_tags(img_fname):
    f = open(img_fname, 'rb')
    tags = EXIF.process_file(f)
    f.close();

    processedTags = {}
    #copy some of the simple tags

    #light source and metering mode need mappings
    copyIfPresent(processedTags, 'Light Source', tags, 'EXIF LightSource')
    copyIfPresent(processedTags, 'Metering Mode', tags, 'EXIF MeteringMode')
    copyIfPresent(processedTags, 'Date Time', tags, 'EXIF DateTimeOriginal')
    copyIfPresent(processedTags, 'Image Optimization', tags, 'MakerNote Image Optimization')
    copyIfPresent(processedTags, 'Hue Adjustment', tags, 'MakerNote HueAdjustment')
    copyIfPresent(processedTags, 'Exposure Time', tags, 'EXIF ExposureTime')
    copyIfPresent(processedTags, 'Exposure Program', tags, 'EXIF ExposureProgram')
    copyIfPresent(processedTags, 'Focus Mode', tags, 'MakerNote FocusMode')

    copyIfPresent(processedTags, 'AutoFlashMode', tags, 'MakerNote AutoFlashMode')
    copyIfPresent(processedTags, 'Image Sharpening', tags, 'MakerNote ImageSharpening')
    copyIfPresent(processedTags, 'Tone Compensation', tags, 'MakerNote ToneCompensation')
    copyIfPresent(processedTags, 'Flash', tags, 'EXIF Flash')
    copyIfPresent(processedTags, 'Lighting Type', tags, 'MakerNote LightingType')
    copyIfPresent(processedTags, 'Noise Reduction', tags, 'MakerNote NoiseReduction')
    copyIfPresent(processedTags, 'Flash Setting', tags, 'MakerNote FlashSetting')
    copyIfPresent(processedTags, 'Bracketing Mode', tags, 'MakerNote BracketingMode')
    copyIfPresent(processedTags, 'ISO Setting', tags, 'MakerNote ISOSetting')
    copyIfPresent(processedTags, 'FlashBracketCompensationApplied', tags, 'MakerNote FlashBracketCompensationApplied')
    copyIfPresent(processedTags, 'SubSecTimeOriginal', tags, 'EXIF SubSecTimeOriginal')
    copyIfPresent(processedTags, 'AFFocusPosition', tags, 'MakerNote AFFocusPosition')
    copyIfPresent(processedTags, 'WhiteBalanceBias', tags, 'MakerNote WhiteBalanceBias')
    copyIfPresent(processedTags, 'ExposureBiasValue', tags, 'EXIF ExposureBiasValue')
    copyIfPresent(processedTags, 'Whitebalance', tags, 'MakerNote Whitebalance')


    #Map various exif data

    #fractional
    if tags.has_key('EXIF FNumber'):
        processedTags['FNumber'] = fractionToDecimal(tags['EXIF FNumber'].printable)
    if tags.has_key('EXIF FocalLength'):
        processedTags['Focal Length'] = fractionToDecimal(tags['EXIF FocalLength'].printable)
