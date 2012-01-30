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

import os
import sys
import cgi
# Enable cgitb for debugging. Do not use in production.
# import cgitb; cgitb.enable()
import re
import subprocess
import hashlib
import json

import beanstalkc

import logwrapper as LOG

ALLOWED_EXTENSIONS = set([
    'txt', 'rtf',
    'pdf',
    'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
    'odf', 'odt', 'ods', 'odp',
    'csv',
    'zip', 'tar', 'bz2', '7zip', 'rar', 'gz',
])

MAX_FILESIZE = (1024**2)*200 # max file size is 200mb
UPLOAD_DIR = "/tmp"

MESSAGE = ""
INFO = {}

_filename_ascii_strip_re = re.compile(r'[^A-Za-z0-9_.-]')

def allowed_file(filename):
    '''
    Check if file type of filename is allowed based on extension
    '''
    INFO['filetype'] = ext = filename.rsplit('.', 1)[1]
    return '.' in filename and ext in ALLOWED_EXTENSIONS

def allowed_size(f):
    '''
    Returns True if the size of f is less than or equal to MAX_FILESIZE
    '''
    # for tip on getting filesize from cStringIO
    # http://trac.edgewall.org/ticket/4311
    f.seek(0, os.SEEK_END) # http://docs.python.org/library/stdtypes.html#file.seek
    INFO['size'] = fsize = f.tell()
    f.seek(0)

    if fsize <= MAX_FILESIZE:
        return True
    
def span(text, c):
    ''' Wrap text in a span with class=c '''
    return '<span class="%s">%s</span>' % (c, text)

def fbuffer(f, chunk_size=10000):
    ''' Simple generator to read/write large files '''
    while True:
        chunk = f.read(chunk_size)
        if not chunk: break
        yield chunk

def secure_filename(filename):
    '''
    Given a filename, returns a secure version of it that is safe to
    pass to os.path.join on the server

    Thanks to Werkzeug Project
    https://github.com/mitsuhiko/werkzeug/
    '''
    if isinstance(filename, unicode):
        from unicodedata import normalize
        filename = normalize('NFKD', filename).encode('ascii', 'ignore')

    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, ' ')
    filename = str(_filename_ascii_strip_re.sub('', '_'.join(
                   filename.split()))).strip('._')

    return filename

def dict_as_ul(d):
    """
    Converts a dictionary into an HTML unordered list
    """
    html = []
    for k, v in d.items():
        html.append("<li>%s: %s</li>" % (k, v))
    html.insert(0, "<ul>")
    html.append("</ul>")
    return ''.join(html)

# cgi.FieldStorage should only be instantiated once
# keep_blank_values=True?
form = cgi.FieldStorage()
file_field_name = "file"

if file_field_name in form and form[file_field_name].filename:
    file_field = form[file_field_name]

    # Check if file is allowed to be uploaded
    if allowed_file(file_field.filename) and allowed_size(file_field.file):
        try:
            # Save uploaded file
            filename = secure_filename(file_field.filename)
            # is using abspath really what we want?
            upload_path = os.path.abspath(os.path.join(UPLOAD_DIR, filename))
            f = open(upload_path, 'wb')
            for chunk in fbuffer(file_field.file):
                f.write(chunk)
            # Set permissions on upload_path for uploadworker
            # Idea: create a group with the Apache user and the uploadworker user
            f.close()

            # Get comment, or say there wasn't one
            comment = form["comment"].value or "None"

            # Open connection to beanstalkd
            beanstalk = beanstalkc.Connection(host='localhost', port=11300)
            uinf = {
                'filename': filename,
                'path': upload_path,
                'comment': comment
                }
            # Enqueue upload job
            beanstalk.put(json.dumps(uinf))
            # Close connection to beanstalkd
            beanstalk.close()

            MESSAGE = span("%s was successfully uploaded. Thank you!" % (filename), "ok")
        except IOError:
            MESSAGE = span("An error occurred while writing the file.", "error")

    else:
        # Upload failed size or type check
        MESSAGE = span("We do not allow users to upload files of this type and/or size", "error")
else:
    MESSAGE = span("You didn't specify a file.", "error")

print '''\
Content-type: text/html\n
<!DOCTYPE html>
<html>
<head>
<title>Upload Confirmation</title>
<link rel="stylesheet" type="text/css" href="../base.css">
</head>
<body>
<p>%s</p>
<h2>Info:</h2>
%s
<p><a href="/">&laquo; Upload another file</a></p>
<p><a href="https://www.honestappalachia.org">&laquo; Back to Honest Appalachia</a></p>
</body>
</html>
''' % (MESSAGE, dict_as_ul(INFO), )
