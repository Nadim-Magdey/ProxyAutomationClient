from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from urllib.parse import quote

def parse_url_queries(url):
    """
    Parse the URL and return its components along with a dictionary of query parameters.
    """
    parsed = urlparse(url)
    query_dict = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    return parsed, query_dict

def rebuild_url(parsed, query_dict):
    """
    Rebuild the URL from its components and a dictionary of query parameters.
    """
    new_query = urlencode(query_dict)

    return urlunparse(parsed._replace(query=new_query))

def url_to_regex(url):
    """
    apply percentage encoding to non-ASCII characters in the URL
    :param url: string(any URL)
    """
    parts = url.split('/')
    encoded_parts = [quote(p) if any(ord(c) > 127 for c in p) else p for p in parts]
    return '/'.join(encoded_parts)
