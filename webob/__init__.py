from webob.datetime_utils import *
from webob.request import *
from webob.response import *
from webob.util import html_escape

__all__ = [
    'Request', 'Response',
    'UTC', 'day', 'week', 'hour', 'minute', 'second', 'month', 'year',
    'html_escape'
]

BaseRequest.ResponseClass = Response
Response.RequestClass = BaseRequest #TODO: just use BaseRequest directly (1.2)

__version__ = '1.1.1'
