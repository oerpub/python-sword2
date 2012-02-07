class HttpResponse(object):
    def __init__(self, *args, **kwargs):
        pass
        
    def __getitem__(self, att):
        # needs to behave like a dictionary
        # we need to be able to look up at least:
        
        # content-type
        # status (as an integer)
        # location
        pass
        
    def get(self, att, default=None):
        # same as __getattr__ but with default return
        pass
        
    def keys(self):
        pass
    

class HttpLayer(object):
    def __init__(self, *args, **kwargs): pass
    def add_credentials(self, username, password): pass
    def request(self, uri, method, headers=None, body=None): 
        # should return a tuple of an HttpResponse object and the content
        pass
        
################################################################################
# Default httplib2 implementation
################################################################################

import httplib2

class HttpLib2Response(HttpResponse):
    def __init__(self, response):
        self.resp = response
        self.status = int(self.resp.status)
        
    def __getitem__(self, att):
        return self.resp[att]
    
    def get(self, att, default=None):
        return self.resp.get(att, default)
        
    def keys(self):
        return self.resp.keys()

class HttpLib2Layer(HttpLayer):
    def __init__(self, cache_dir, timeout=30):
        self.h = httplib2.Http(".cache", timeout=30.0)
        self.credentials = self.h.credentials
        
    def add_credentials(self, username, password):
        self.h.add_credentials(username, password)
        
    def request(self, uri, method, headers=None, body=None):
        print "uri: " + uri
        print "method: " + method
        resp, content = self.h.request(uri, method, headers=headers, body=body)
        print "Marvin:"
        print resp
        print "==================="
        print content
        return (HttpLib2Response(resp), content)

################################################################################    
# Guest urllib2 implementation
################################################################################

import urllib2, base64

class PreemptiveBasicAuthHandler(urllib2.HTTPBasicAuthHandler):
    def __init__(self, username, password):
        self.username = username
        self.password = password
    
    def http_request(self, request):
        request.add_header(self.auth_header, 'Basic %s' % base64.b64encode(self.username + ':' + self.password))
        return request
    
    https_request = http_request

class UrlLib2Response(HttpResponse):
    def __init__(self, response):
        self.response = response
        print response
        self.headers = dict(response.info())
        self.status = int(self.response.code)
    
    def __getitem__(self, att):
        # needs to behave like a dictionary
        # we need to be able to look up at least:
        
        # content-type
        # status
        # location
        if att == "status":
            return self.status
        return self.headers[att]
        
    def get(self, att, default=None):
        # same as __getattr__ but with default return
        if att == "status":
            return self.status
        return self.headers.get(att, default)
        
    def keys(self):
        return self.headers.keys() + ["status"]
    
class UrlLib2Layer(HttpLayer):
    def __init__(self, opener=None):
        self.opener = opener
        if self.opener is None:
            self.opener = urllib2.build_opener()
    
    def add_credentials(self, username, password):
        auth_handler = PreemptiveBasicAuthHandler(username, password)
        current_handlers = self.opener.handlers
        new_handlers = current_handlers + [auth_handler]
        self.opener = urllib2.build_opener(*new_handlers)
    
    def request(self, uri, method, headers=None, body=None): 
        # should return a tuple of an HttpResponse object and the content
        try:
            if method == "GET":
                req = urllib2.Request(uri, None, headers)
                response = self.opener.open(req)
                return UrlLib2Response(response), response.read()
            elif method == "POST":
                # FIXME: this approach doesn't scale, we need to fix this here and
                # in the python sword2 client itself
                req = urllib2.Request(uri, body, headers)
                response = self.opener.open(req)
                return UrlLib2Response(response), response.read()
            elif method == "PUT":
                # FIXME: this approach doesn't scale, we need to fix this here and
                # in the python sword2 client itself
                req = urllib2.Request(uri, body, headers)
                # monkey-patch the request method (which seems to be the fastest
                # way to do this)
                req.get_method = lambda: 'PUT'
                response = self.opener.open(req)
                return UrlLib2Response(response), response.read()
            elif method == "DELETE":
                req = urllib2.Request(uri, None, headers)
                # monkey-patch the request method (which seems to be the fastest
                # way to do this)
                req.get_method = lambda: 'DELETE'
                response = self.opener.open(req)
                return UrlLib2Response(response), response.read()
            else:
                raise NotImplementedError()
        except urllib2.HTTPError as e:
            try:
                # treat it like a normal response
                return UrlLib2Response(e), e.read()
            except Exception as e:
                # unable to read()
                return UrlLib2Response(e), None
				
################################################################################    
# Guest pycurl implementation
################################################################################

import pycurl, httplib, StringIO

class PycURL2Response(HttpResponse):
    def __init__(self, response):
        self.resp = response
        self.status = int(self.resp.status)
        
    def __getitem__(self, att):
        return self.resp[att]
    
    def get(self, att, default=None):
        return self.resp.get(att, default)
        
    def keys(self):
        return self.resp.keys()

class PycURL2Layer(HttpLayer):
    def __init__(self, timeout=30):
        self.h = httplib2.Http(".cache", timeout=30.0)
        self.credentials = self.h.credentials
        
    def add_credentials(self, username, password):
        self.h.add_credentials(username, password)
        
    #def curl_request(uri, method='GET', body=None, headers=None, redirections=5, connection_type=None):
	def request(self, uri, method, headers=None, body=None):
		"""
		request(self, uri, method='GET', body=None, headers=None)
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

		iHttpObject = self.h
		iUri = uri
		iMethod = method
		iBody = body
		iHeaders = headers
		iRedirections = 5
		iConnectionType = None

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
			print('HEADERS IS '+str(headers))
			http_response = headers[0].split(None, 2)
			del headers[0]
			if(http_response[1] == '100'):
				del headers[0]
				http_response=headers[0].split(None,2)
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

			return (PycURL2Response(return_headers), return_content)
		else:
			return PycURL2Response(iHttpObject.request(iUri, method=iMethod, body=iBody, headers=iHeaders,
						redirections=iRedirections, connection_type=iConnectionType))
		



