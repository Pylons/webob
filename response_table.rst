===========================
 Response Comparison Table
===========================

b=WebBob
z=Werkzeug
x=both

WEBOB NAME                         write  read  WERKZEUG NAME                      NOTES
=================================  =====  ====  =================================  ===========================================
default_content_type                 x      x   default_mimetype                   wb default: "text/html", wz: "text/plain"
default_charset                      b      b  	                                   wz uses class var default for charset
charset                              x      x   charset
unicode_errors                       b      b   
default_conditional_response         b      b
from_file() (classmethod)            b      b
copy                                 b      b
status (string)                      x      x   status
status_int                           x      x   status_code
                                            z   default_status
headers                              b      b
body                                 b      b   
unicode_body                         x      x   data 
body_file                                   b                                      File-like obj returned is writeable
app_iter                             b      x   iter_encoded()                     wz: encodes each element as consumed
allow                                b      b
vary              
content_length
content_encoding
content_language
content_location
content_md5
content_disposition
accept_ranges
content_range
date
expires
last_modified
etag
location
pragma
age
retry_after
server
www_authenticate

