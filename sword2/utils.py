#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utility methods used within the module
"""

from sword2_logging import logging
utils_l = logging.getLogger(__name__)

from time import time
from datetime import datetime

from base64 import b64encode

try:
    from hashlib import md5
except ImportError:
    import md5

import mimetypes

NS = {}
NS['dcterms'] = "{http://purl.org/dc/terms/}%s"
NS['sword'] ="{http://purl.org/net/sword/terms/}%s"
NS['atom'] = "{http://www.w3.org/2005/Atom}%s"
NS['app'] = "{http://www.w3.org/2007/app}%s"

def get_text(parent, tag, plural = False):
    """Takes an `etree.Element` and a tag name to search for and retrieves the text attribute from any
    of the parent element's direct children.
    
    Returns a simple `str` if only a single element is found, or a list if multiple elements with the
    same tag. Ignores element attributes, returning only the text."""
    text = None
    for item in parent.findall(tag):
        t = item.text
        if not text:
            if plural:
                text = [t]
            else:
                text = t
        elif isinstance(text, list):
            text.append(t)
        else:
            text = [text, t]
    return text

def get_md5(data):
    """Takes either a `str` or a file-like object and passes back a tuple containing (md5sum, filesize)
    
    The file is streamed as 1Mb chunks so should work for large files. File-like object must support `seek()`
    """
    if hasattr(data, "read") and hasattr(data, 'seek'):
        m = md5()
        chunk = data.read(1024*1024)   # 1Mb
        f_size = 0
        while(chunk):
            f_size += len(chunk)
            m.update(chunk)
            chunk = data.read(1024*1024)
        data.seek(0)
        return m.hexdigest(), f_size
    else:       # normal str
        m = md5()
        f_size = len(data)
        m.update(data)
        return m.hexdigest(), f_size
        

class Timer(object):
    """Simple timer, providing a 'stopwatch' mechanism.
    
    Usage example:
        
    >>> from sword2.utils import Timer
    >>> from time import sleep
    >>> t = Timer()
    >>> t.get_timestamp()
    datetime.datetime(2011, 6, 7, 7, 40, 53, 87248)
    >>> t.get_loggable_timestamp()
    '2011-06-07T07:40:53.087516'

    >>> # Start a few timers
    ... t.start("kaylee", "river", "inara")
    >>> sleep(3)   # wait a little while
    >>> t.time_since_start("kaylee")
    (0, 3.0048139095306396)

    # tuple -> (index of the logged .duration, time since the .start method was called)
    # eg 't.duration['kaylee'][0]' would equal 3.00481.... 

    >>> sleep(2)
    >>> t.time_since_start("kaylee", "inara")
    [(1, 5.00858998298645), (0, 5.00858998298645)]
    >>> sleep(5)
    >>> t.time_since_start("kaylee", "river")
    [(2, 10.015379905700684), (0, 10.015379905700684)]
    >>> sleep(4)
    >>> t.time_since_start("kaylee", "inara", "river")
    [(3, 14.021538972854614), (1, 14.021538972854614), (1, 14.021538972854614)]
    
    # The order of the response is the same as the order of the names in the method call.
    
    >>> # report back
    ... t.duration['kaylee']
    [3.0048139095306396, 5.00858998298645, 10.015379905700684, 14.021538972854614]
    >>> t.duration['inara']
    [5.00858998298645, 14.021538972854614]
    >>> t.duration['river']
    [10.015379905700684, 14.021538972854614]
    >>> 
    """
    def __init__(self):
        self.reset_all()
        
    def reset_all(self):
        self.counts = {}    
        self.duration = {}
        self.stop = {}

    def reset(self, name):
        if name in self.counts:
            self.counts[name] = 0
    
    def read_raw(self, name):
        return self.counts.get(name, None)
    
    def read(self, name):
        if name in self.counts:
            return datetime.fromtimestamp(self.counts[name])
        else:
            return None

    def start(self, *args):
        st_time = time()
        for arg in args:
            self.counts[arg] = st_time

    def stop(self, *args):
        st_time = time()
        for arg in args:
            self.stop[arg] = st_time
    
    def get_timestamp(self):
        # Convenience function
        return datetime.now()
    
    def get_loggable_timestamp(self):
        """Human-readable by intent"""
        return datetime.now().isoformat()
        
    def time_since_start(self, *args):
        r = []
        st_time = time()
        for name in args:
            if name in self.counts:
                duration = st_time - self.counts[name]
                if not self.duration.has_key(name):
                    self.duration[name] = []
                self.duration[name].append(duration)
                r.append((len(self.duration[name]) - 1, duration))
            else:
                r.append((0, 0))
        if len(r) == 1:
            return r.pop()
        else:
            return r
            

def get_content_type(filename):
    # Does a simple .ext -> mimetype mapping.
    # Generally better to specify the mimetype upfront.
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

def create_multipart_related(payloads):
    """ Expected: list of dicts with keys 'key', 'type'='content type','filename'=optional,'data'=payload, 'headers'={} 
    
    TODO: More mem-efficient to spool this to disc rather than hold in RAM, but until Httplib2 bug gets fixed (issue 151)
    this might be in vain.
    
    Can handle more than just two files. 
    
    SWORD2 multipart POST/PUT expects two attachments - key = 'atom' w/ Atom Entry (metadata)
                                                        key = 'payload' (file)
    """

    from email.MIMEMultipart import MIMEMultipart
    from email.MIMEBase import MIMEBase
    from email import Encoders

    # Build multi-part message
    multipart = MIMEMultipart('related')
    for payload in payloads:
        # Create new part from its mimetype
        mimetype = payload.get('type')
        if mimetype is None:
            mimetype = get_content_type(payload.get("filename"))
        part = MIMEBase(*(mimetype.split('/')))

        # Set the name and filename of the payload
        if payload.get('filename', None):
            part.add_header('Content-Disposition', 'attachment',
                            name=payload['key'], filename=payload['filename'])
        else:
            part.add_header('Content-Disposition', 'attachment',
                            name=payload['key'])

        # Set additional headers
        if payload.has_key("headers"):
            for k, v in payload['headers'].iteritems():
                part.add_header(k, v)

        # Attach payload
        part.set_payload(payload['data'])
        if payload['key'] == 'payload':
            Encoders.encode_base64(part)

        multipart.attach(part)

    # Determine multi-part content type
    message_body = multipart.as_string(unixfrom=False)
    substr = 'content-type: '
    assert message_body[:len(substr)].lower() == substr.lower()
    stop = message_body.find('\n')
    content_type = message_body[len(substr):stop].strip()
    while content_type[-1] == ';':
        start = stop+1
        stop = message_body.find('\n', start)
        content_type += message_body[start:stop].strip()

    return content_type, message_body

def curl_request(http_object, uri, method='GET', body=None, headers=None, redirections=5, connection_type=None):
    """
    request(self, uri, method='GET', body=None, headers=None, redirections=5, connection_type=None)
        Performs a single HTTP request.
        The 'uri' is the URI of the HTTP resource and can begin 
        with either 'http' or 'https'. The value of 'uri' must be an absolute URI.
        
        The 'method' is the HTTP method to perform, such as GET, POST, DELETE, etc. 
        There is no restriction on the methods allowed.
        
        The 'body' is the entity body to be sent with the request. It is a string
        object.
        
        Any extra headers that are to be sent with the request should be provided in the
        'headers' dictionary.
        
        The maximum number of redirect to follow before raising an 
        exception is 'redirections. The default is 5.
        
        The return value is a tuple of (response, content), the first 
        being and instance of the 'Response' class, the second being 
        a string that contains the response entity body.
    """

    import pycurl, httplib2, StringIO

    iHttpObject = http_object
    iUri = uri
    iMethod = method
    iBody = body
    iHeaders = headers
    iRedirections = redirections
    iConnectionType = connection_type

    if (iMethod == 'GET') and (iBody is None):
        curl = pycurl.Curl()
        curl.setopt(curl.URL, str(iUri))
        curl.setopt(curl.HTTPGET, 1)
        curl.setopt(curl.VERBOSE, 0) # Change for verbose / debug output
        curl.setopt(curl.HTTPHEADER, [(k + ': ' + v) for k,v in iHeaders.iteritems()])
        
        # Create stream for response headers and data
        response_headers = StringIO.StringIO()
        curl.setopt(curl.HEADERFUNCTION, response_headers.write)
        response_data = StringIO.StringIO()
        curl.setopt(curl.WRITEFUNCTION, response_data.write)

        curl.perform()

        # Build response
        response_headers.seek(0)
        headers = response_headers.read().strip()
        if '\r\n' in headers:
            headers = headers.split('\r\n')
        else:
            headers = headers.split('\n')
        http_response = headers[0].split(None, 2)
        # MARVIN: FOR DEBUGGING:
        print "HTTP RESPONE ============================="
        print http_response
        print "=========================================="
        print "HEADERS =================================="
        print headers
        print "=========================================="        
        del headers[0]
        headers = [(x[0].lower(), x[1]) for x in [x.split(': ') for x in headers]]
        if http_response[0][:5].lower() != 'http/':
            raise ValueError, "Invalid http response from cURL."
        version = {'1.0': 10, '1.1': 11}[http_response[0][5:]]
        status = http_response[1]
        reason = http_response[2]
        headers.append(('status', status))
        return_headers = httplib2.Response(dict(headers))
        return_headers.version = version
        return_headers.status = int(status)
        return_headers.reason = reason

        response_data.seek(0)
        return_content = response_data.read()
        curl.close()

        return return_headers, return_content
    elif (iMethod == 'POST') and (iBody is not None):
        curl = pycurl.Curl()
        curl.setopt(curl.URL, str(iUri))
        curl.setopt(curl.POST, 1)

        # Create stream for transmission
        stream = StringIO.StringIO(iBody)
        curl.setopt(curl.READFUNCTION, stream.read)

        curl.setopt(curl.VERBOSE, 0) # Change for verbose / debug output
        curl.setopt(curl.HTTPHEADER, [(k + ': ' + v) for k,v in iHeaders.iteritems()])

        # Create stream for response headers and data
        response_headers = StringIO.StringIO()
        curl.setopt(curl.HEADERFUNCTION, response_headers.write)
        response_data = StringIO.StringIO()
        curl.setopt(curl.WRITEFUNCTION, response_data.write)

        curl.perform()

        # Build response
        response_headers.seek(0)
        headers = response_headers.read().strip()
        if '\r\n' in headers:
            headers = headers.split('\r\n')
        else:
            headers = headers.split('\n')
        http_response = headers[2].split(None, 2) # HOTFIX MARVIN 2012-01-26
        # MARVIN: FOR DEBUGGING:
        print "HTTP RESPONE ============================="
        print http_response
        print "=========================================="
        print "HEADERS =================================="
        print headers
        print "=========================================="
        del headers[0]
        del headers[0] # HOTFIX MARVIN 2012-01-26
        del headers[0] # HOTFIX MARVIN 2012-01-26
        headers = [(x[0].lower(), x[1]) for x in [x.split(': ') for x in headers]]
        if http_response[0][:5].lower() != 'http/':
            raise ValueError, "Invalid http response from cURL."
        version = {'1.0': 10, '1.1': 11}[http_response[0][5:]]
        status = http_response[1]
        reason = http_response[2]
        headers.append(('status', status))
        return_headers = httplib2.Response(dict(headers))
        return_headers.version = version
        return_headers.status = int(status)
        return_headers.reason = reason

        response_data.seek(0)
        return_content = response_data.read()
        curl.close()

        return return_headers, return_content
    else:
        return iHttpObject.request(iUri, method=iMethod, body=iBody, headers=iHeaders,
                                   redirections=iRedirections, connection_type=iConnectionType)
