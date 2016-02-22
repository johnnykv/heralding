# Parts of this code are taken from: https://gist.github.com/chris-hailstorm/4989643
# All credits go to the original author

import unicodedata


def _remove_accents(data):
    """
    Changes accented letters to non-accented approximation, like Nestle

    """
    return unicodedata.normalize('NFKD', data).encode('ascii', 'ignore')


def _asciify_list(data):
    """ Ascii-fies list values """
    ret = []
    for item in data:
        if isinstance(item, unicode):
            item = _remove_accents(item)
            item = item.encode('utf-8')
        elif isinstance(item, list):
            item = _asciify_list(item)
        elif isinstance(item, dict):
            item = _asciify_dict(item)
        ret.append(item)
    return ret


def _asciify_dict(data):
    """ Ascii-fies dict keys and values """
    ret = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = _remove_accents(key)
            key = key.encode('utf-8')
            # # note new if
        if isinstance(value, unicode):
            value = _remove_accents(value)
            value = value.encode('utf-8')
        elif isinstance(value, list):
            value = _asciify_list(value)
        elif isinstance(value, dict):
            value = _asciify_dict(value)
        ret[key] = value
    return ret


def asciify(data):
    if isinstance(data, list):
        return _asciify_list(data)
    elif isinstance(data, dict):
        return _asciify_dict(data)
    elif isinstance(data, unicode):
        data = _remove_accents(data)
        return data.encode('utf-8')
    elif isinstance(data, str):
        return data
    else:
        raise TypeError('Input must be dict, list, str or unicode')