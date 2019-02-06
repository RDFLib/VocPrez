import urllib


def url_encode(s):
    return urllib.parse.quote(s)


def make_title(s):
    return ' '.join(s.split('#')[-1].split('/')[-1].split('_')).title()
