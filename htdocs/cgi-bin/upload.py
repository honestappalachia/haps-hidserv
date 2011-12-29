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
# DO NOT USE cgitb in production
import cgitb; cgitb.enable()

import subprocess
import hashlib
import re

import mylogging as LOG

# TODO: Complete list of useful filetypes to upload
ALLOWED_EXTENSIONS = set([
    'txt', 'pdf',
    'doc', 'xls', 'ppt',
    'docx', 'xlsx', 'pptx',
])

MAX_FILESIZE = (1024**2)*200 # max file size is 200mb
UPLOAD_DIR = "/tmp"

MESSAGE = ""

def allowed_file(filename):
    '''
    Check if file type of filename is allowed based on extension
    '''
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def allowed_size(f):
    '''
    Returns True if the size of f is less than or equal to MAX_FILESIZE
    '''
    # for tip on getting filesize from cStringIO
    # http://trac.edgewall.org/ticket/4311
    f.seek(0, os.SEEK_END) # http://docs.python.org/library/stdtypes.html#file.seek
    fsize = f.tell()
    f.seek(0)

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

def secure_filename(filename):
    '''
    Given a filename, returns a secure version of it that is safe to
    pass to os.path.join on the server

    Thanks to Werkzeug Project for the Unicode escaping code
    https://github.com/mitsuhiko/werkzeug/
    '''
    if isinstance(filename, unicode):
        from unicodedata import normalize
        filename = normalize('NFKD', filename).encode('ascii', 'ignore')

    return '_'.join(os.path.basename(filename).split())

# cgi.FieldStorage should only be instantiated once
# keep_blank_values=True?
form = cgi.FieldStorage()

if "file" in form and form["file"].filename:
    file_field = form["file"]

    # Check if file is allowed to be uploaded
    if allowed_file(file_field.filename) and allowed_size(file_field.file):
        try:
            # Save uploaded file
            filename = secure_filename(file_field.filename)
            upload_path = os.path.abspath(
                os.path.join(UPLOAD_DIR, filename))
            f = open(upload_path, 'wb')
            for chunk in fbuffer(file_field.file):
                f.write(chunk)
            f.close()

            # Hash file for authentication
            sha256 = hashlib.sha256()
            block_size = 8192
            with open(upload_path, 'rb') as f:
                for chunk in iter(lambda: f.read(block_size), ''):
                    sha256.update(chunk)
            sha256digest = sha256.hexdigest()

            # Get comment, or say there wasn't one
            comment = form["comment"].value or "None"

            # Write summary to file
            summary_filename = "%s-summary" % filename
            summary_file = open(os.path.abspath(os.path.join(
                UPLOAD_DIR, summary_filename
            )), 'w')
            summary_file.write("filename: %s\n" % filename)
            summary_file.write("  SHA256: %s\n" % sha256digest)
            summary_file.write(" Comment: %s\n" % comment)
            summary_file.close()

            # Call upload handler
            pid = subprocess.Popen(
                ['python', 'upload_handler.py', filename, summary_filename]
            )

            MESSAGE = span("%s was successfully uploaded." % (filename), "ok")
        except IOError:
            MESSAGE = span("An error occurred writing the file.", "error")

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
<style>
.error { background:#FFCFCF; border:2px solid #FF6B6B; padding:4px; }
.ok { background:#C4FFC9; border: 2px solid #73FF7E; padding:4px; }
</style>
</head>
<body>
<p>%s</p>
<p><a href="/">&laquo; Upload another file</a></p>
<p><a href="https://www.honestappalachia.org">&laquo; Back to Honest Appalachia</a></p>
</body>
</html>
''' % (MESSAGE, )
