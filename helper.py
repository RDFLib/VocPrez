import urllib


def url_encode(s):
    return urllib.parse.quote(s)


def make_title(s):
    # make title from URI
    title = ' '.join(s.split('#')[-1].split('/')[-1].split('_')).title()

    # replace dashes with whitespace
    if '-' in title:
        title = ' '.join(title.split('-')).title()

    # replace periods with whitespace
    if '.' in title:
        title = ' '.join(title.split('.')).title()

    return title
