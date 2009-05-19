from webob import Request, Response
from webob.multidict import MultiDict
from webob import converter

def convert_multidict(prop):
    return converter(prop, _convert_getter, _convert_setter)

def _convert_getter(value):
    return DjangoMultiDictWrapper(value)

def _convert_setter(value):
    return value

class HttpRequest(Request):
    encoding = Request.charset
    @property
    def META(self):
        return self.environ
    # FIXME: no user
    # FIXME: no session
    raw_post_data = Request.body
    def __getitem__(self, item):
        return self.params[item]
    def is_secure(self):
        return self.scheme == 'https'
    GET = convert_multidict(Request.GET)
    POST = convert_multidict(Request.POST)
    REQUEST = convert_multidict(Request.params)
    FILES = convert_multidict(Request.POST) # FIXME: not quite right

class DjangoMultiDictWrapper(object):
    def __init__(self, m):
        self.m = m
    # FIXME: keys, items, values, iter* are somewhat different
    def getlist(self, key):
        return self.m.getall(key)
    def setlist(self, key, value):
        if key in self.m:
            del self.m[key]
        for item in value:
            self.m.add(key, item)
    def appendlist(self, key, value):
        self.m.add(key, value)
    def setlistdefault(self, key, default_list):
        if key not in self.m:
            self.setlist(key, default_list)
    def lists(self):
        return self.m.dict_of_lists()
    def __getattr__(self, attr):
        return getattr(self, m, attr)
    
class HttpResponse(Response):
    def __init__(self, body, mimetype=None, content_type=None):
        Response.__init__(body)
        if mimetype is not None:
            self.content_type = mimetype
        if content_type is not None:
            self.headers['content-type'] = content_type
    def __setitem__(self, key, value):
        self.headers[key] = value
    def __getitem__(self, key):
        return self.headers[key]
    def has_header(self, header):
        return header in self.headers
    def flush(self):
        pass
    # FIXME: tell

    content = Response.body

HttpRequest.ResponseClass = HttpResponse
HttpResponse.RequestClass = HttpRequest
