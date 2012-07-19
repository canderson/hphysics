import urllib2
import settings

def open_http(url):
    request = urllib2.Request(url)
    request.add_header('User-Agent', settings.user_agent)
    opener = urllib2.build_opener() 
    """Tries to open an http url. Raises an error if the request fails."""
    res = opener.open(request)
    return ''.join(res.readlines()), res.geturl()

def open_http_raw(url):
    """Tries to open an http url. Raises an error if the request fails."""
    # url = urllib2.quote(url,':/') Don't use this. ADS does not handle equivalent URLs equivalently.
    # Can form POST requests and add headers here
    req = urllib2.Request(url)
    # Make request (request, data - do not use, timeout in seconds)
    result = urllib2.urlopen(req, None, 10)
    return result        
    
