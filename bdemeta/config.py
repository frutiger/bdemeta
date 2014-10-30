# bdemeta.config

import copy

def merge(source, extension):
    def key_present(dict, key):
        try:
            # this is due to 'defaultdict' returning false for 'key in dict'
            dict[key]
        except:
            pass
        return key in dict

    result = copy.copy(source)
    for k in source.keys():
        if key_present(extension, k):
            try:
                result[k] = merge(source[k], extension[k])
            except AttributeError:
                result[k] = copy.copy(source[k] + extension[k])

    for k in extension.keys():
        if key_present(source, k):
            try:
                result[k] = merge(source[k], extension[k])
            except AttributeError:
                result[k] = copy.copy(source[k] + extension[k])
        else:
            result[k] = copy.copy(extension[k])

    return result
