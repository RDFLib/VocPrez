import urllib


def url_encode(s):
    return urllib.parse.quote(s)


def make_title(s):
    result = s.split('#')[-1].split('/')[-1]
    result = result.replace('_', ' ')
    return result.title()
