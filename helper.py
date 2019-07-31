import urllib
import re
from rdflib import URIRef
import markdown
import os
import time
import pickle
import logging
import errno
import _config as config

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def url_encode(s):
    try:
        return urllib.parse.quote(s)
    except:
        pass


def url_decode(s):
    try:
        return urllib.parse.unquote(s)
    except:
        pass


def make_title(s):
    # make title from URI
    title = ' '.join(s.split('#')[-1].split('/')[-1].split('_')).title()

    # replace dashes and periods with whitespace
    title = re.sub('[-\.]+', ' ', title).title()

    return title


def parse_markdown(s):
    return markdown.markdown(s)


def is_email(email):
    """
    Check if the email is a valid email.
    :param email: The email to be tested.
    :return: True if the email matches the static regular expression, else false.
    :rtype: bool
    """
    pattern = r"[a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
    return True if re.search(pattern, email) is not None else False


def strip_mailto(email):
    return email[7:]


def contains_mailto(email):
    if email[:7] == 'mailto:':
        return True
    return False


def is_url(url):
    """
    Check if the url is a valid url.
    :param url: The url to be tested.
    :type url: str
    :return: True if the url passes the validation, else false.
    :rtype: bool
    """
    if isinstance(url, URIRef):
        return True

    pattern = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return True if re.search(pattern, url) is not None else False

def cache_read(cache_file_name):
    '''
    Function to read object from cache if cache file is younger than cache_hours. Returns None on failure
    '''
    cache_seconds = config.VOCAB_CACHE_HOURS * 3600
    cache_file_path = os.path.join(config.VOCAB_CACHE_DIR, cache_file_name)
    
    if os.path.isfile(cache_file_path):
        # if the cache file is younger than cache_hours days, then try to read it
        cache_file_creation_time = os.stat(cache_file_path).st_mtime
        # if the VOCABS.pickle file is older than VOCAB_CACHE_DAYS days, delete it
        if cache_file_creation_time >= time.time() - cache_seconds:
            try:
                with open(cache_file_path, 'rb') as f:
                    cache_object = pickle.load(f)
                    f.close()
                if cache_object: # Ignore empty file
                    logging.debug('Reading cache file {}'.format(os.path.abspath(cache_file_path)))
                    return cache_object
            except Exception as e:
                logging.debug('Unable to read cache file {}: {}'.format(os.path.abspath(cache_file_path), e))
                pass
        
    return None

def cache_write(cache_object, cache_file_name):
    '''
    Function to write object to cache if cache file is older than cache_hours.
    '''
    cache_seconds = config.VOCAB_CACHE_HOURS * 3600
    cache_file_path = os.path.join(config.VOCAB_CACHE_DIR, cache_file_name)
    
    if os.path.isfile(cache_file_path):
        # if the VOCABS.pickle file is older than VOCAB_CACHE_DAYS days, delete it
        cache_file_creation_time = os.stat(cache_file_path).st_mtime
        # if the VOCABS.pickle file is older than VOCAB_CACHE_DAYS days, delete it
        if cache_seconds and cache_file_creation_time < time.time() - cache_seconds:
            os.remove(cache_file_path)
        else:
            return # Don't do anything - cache file is too young to die

    try:
        os.makedirs(config.VOCAB_CACHE_DIR)
        logging.debug('Cache directory {} created'.format(os.path.abspath(config.VOCAB_CACHE_DIR)))
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(config.VOCAB_CACHE_DIR):
            pass
        else:
            raise   
        
    if cache_object: # Don't write empty file
        with open(cache_file_path, 'wb') as cache_file:
            pickle.dump(cache_object, cache_file)
            cache_file.close()
        logging.debug('Cache file {} written'.format(cache_file_path))
    else:
        logging.debug('Empty object ignored')
         
