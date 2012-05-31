import urllib2

def open_http(url):
    """Tries to open an http url. Raises an error if the request fails."""
    res = open_http_raw(url)
    return ''.join(res.readlines()), res.geturl()

def open_http_raw(url):
    """Tries to open an http url. Raises an error if the request fails."""
    # url = urllib2.quote(url,':/') Don't use this. ADS does not handle equivalent URLs equivalently.
    # Can form POST requests and add headers here
    req = urllib2.Request(url)
    # Make request (request, data - do not use, timeout in seconds)
    result = urllib2.urlopen(req, None, 10)
    return result
    
