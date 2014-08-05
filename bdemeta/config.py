import copy

def merge(source, extension):
    result = copy.copy(source)
    for k in source.keys():
        if k in extension:
            try:
                result[k] = merge(source[k], extension[k])
            except AttributeError:
                result[k] = copy.copy(source[k] + extension[k])

    for k in extension.keys():
        if k not in source:
            result[k] = copy.copy(extension[k])

    return result
