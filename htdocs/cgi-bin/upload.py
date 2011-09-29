#!/usr/bin/env python
"""
This is the CGI script called by the upload form.

It receives the form contents as cgi.FieldStorage. Then it

    1. Gets the "file" field
    2. Checks that the filetype and filesize are allowed
    3. If so, uploads file and returns success page.
       Otherwise, returns error page.
"""

# TODO: check for exisiting file with the same name; use renaming scheme

import cgi
import cgitb; cgitb.enable()
import os, sys
import magic
import beanstalkc
from mylogging import debug, info, warning, error, critical

# thttpd(8) CGI :
# CGI scripts run with the directory they live in as their current working directory
UPLOAD_DIR = "../uploads/"

# Whitelist of allowed filetypes
# TODO: Complete list of useful filetypes to upload
ALLOWED_FILETYPES = set([
    # format: (extension, MIME type),
    ('.txt', 'text/plain'),
    ('.pdf', 'application/pdf'),
    ('.doc', 'application/msword'),
    ('.xls', 'application/vnd.ms-excel'),
])

MAX_FILESIZE = (1024**2)*500 # max file size is 500mb

INFO = {}   # Store metadata about the file being uploaded; primarily for debugging
MESSAGE = ""

def allowed_ft(f):
    '''
    Use python-magic to check the filetype of f (path relative to script)
    Return True if allowed
    '''
    m = magic.Magic(mime=True)

    # check MIME type
    mtype = m.from_buffer(f.read(1024))
    INFO['mime_type'] = mtype
    if mtype in [x[1] for x in ALLOWED_FILETYPES]:
        return True
    else:
        return False

def allowed_size(f):
    '''
    Returns true if the size of f is less than MAX_FILESIZE
    '''
    # Thanks to Trac developers, responding to the replacement of StringIO
    # (which supports len) with cStringIO (no len) in the cgi module in Python >= 2.5
    # for tip on getting filesize from cStringIO
    # http://trac.edgewall.org/ticket/4311
    f.seek(0, os.SEEK_END) # http://docs.python.org/library/stdtypes.html#file.seek
    fsize = f.tell()
    f.seek(0)

    INFO['size'] = fsize
    if fsize <= MAX_FILESIZE:
        return True
    else:
        return False
    
def span(text, c):
    ''' Wrap text in a span with class=c '''
    return '<span class="%s">%s</span>' % (c, text)

def fbuffer(f, chunk_size=10000):
    ''' Simple generator to read/write large files '''
    while True:
        chunk = f.read(chunk_size)
        if not chunk: break
        yield chunk

form = cgi.FieldStorage() # this should only be instantiated once
field = "file"

if field in form and form[field].filename:
    filefield = form[field]
    # strip leading name to avoid directory traversal attacks
    clean_fn = os.path.basename(filefield.filename)
    # check filetype
    if allowed_ft(filefield.file) and allowed_size(filefield.file):
        try:
            f = open(os.path.join(UPLOAD_DIR, clean_fn), 'wb')
            for chunk in fbuffer(filefield.file):
                f.write(chunk)
            MESSAGE = span("%s was successfully uploaded." % (clean_fn), "ok")
            beanstalk = beanstalkc.Connection(host='localhost', port=11300)
            # places job - absolute path to uploaded file
            beanstalk.put(os.path.abspath(os.path.join(UPLOAD_DIR, clean_fn)))
            debug("Enqueued %s" % os.path.abspath(os.path.join(UPLOAD_DIR, clean_fn)))
            beanstalk.close()
        except IOError:
            MESSAGE = span("An error occurred writing the file.", "error")
        finally:
            f.close()
    else:
	# TODO: make MESSAGE to user more useful
	MESSAGE = span("We do not allow users to upload files of this type and/or size", "error")
else:
    MESSAGE = span("You didn't specify a file.", "error")

print '''\
Content-type: text/html\n
<!DOCTYPE html>
<html>
<head>
<title>Upload Confirmation</title>
<style>
.error { background:#FFCFCF; border:2px solid #FF6B6B; padding:4px; }
.ok { background:#C4FFC9; border: 2px solid #73FF7E; padding:4px; }
</style>
</head>
<body>
<p>%s</p>
<a href="/">&laquo; Home</a>
</body>
</html>
''' % (MESSAGE, )
