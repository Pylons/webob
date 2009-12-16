:mod:`webob` -- Request/Response objects
========================================

.. automodule:: webob

Request
-------

.. autoclass:: Request

.. automodule:: webob.acceptparse
.. autoclass:: Accept
.. autoclass:: MIMEAccept

.. automodule:: webob.byterange
.. autoclass:: Range

.. automodule:: webob.cachecontrol
.. autoclass:: CacheControl

.. automodule:: webob.datastruct
.. autoclass:: EnvironHeaders

.. automodule:: webob.etag
.. autoclass:: ETagMatcher
.. autoclass:: IfRange


Response
--------

.. autoclass:: webob.Response

.. autoclass:: webob.byterange.ContentRange

.. autoclass:: webob.cachecontrol.CacheControl

.. automodule:: webob.headerdict
.. autoclass:: HeaderDict


Misc Functions
--------------

.. autofunction:: webob.html_escape

.. comment:
   not sure what to do with these constants; not autoclass
   .. autoclass:: webob.day
   .. autoclass:: webob.week
   .. autoclass:: webob.hour
   .. autoclass:: webob.minute
   .. autoclass:: webob.second
   .. autoclass:: webob.month
   .. autoclass:: webob.year

.. autoclass:: webob.response.AppIterRange

.. automodule:: webob.multidict
.. autoclass:: MultiDict
.. autoclass:: UnicodeMultiDict
.. autoclass:: NestedMultiDict
.. autoclass:: NoVars

.. automodule:: webob.updatedict
.. autoclass:: webob.updatedict.UpdateDict


Descriptors
-----------

.. autoclass:: webob.descriptors.environ_getter
.. autoclass:: webob.descriptors.header_getter
.. autoclass:: webob.descriptors.converter
.. autoclass:: webob.descriptors.deprecated_property
