#!/usr/bin/env python
import cgi
import cgitb; cgitb.enable()
import os, sys
import mimetypes

# implement:
# check filesize, disallow too-large filesizes
# check for existing file with same name; if exists, add _1...
# check filetype - whitelist?
# any kind of DoS mitigation? use URL throttling?

# thttpd(8) CGI sez: CGI programs run with the directory they live in as
# their current working directory
UPLOAD_DIR = "../uploads/"
# Whitelist of allowed filetypes
ALLOWED_EXTENSIONS = set([
    'txt', 'rtf',
    'pdf',
    'doc', 'docx', 'xls', 'ppt',
    'jpg', 'jpeg', 'png', 'png',
])
MAX_FILESIZE = (1024**2)*500 # max file size is 500mb
MESSAGE = ""

def span(text, c):
    ''' Wrap text in a span with class=c '''
    return '<span class="%s">%s</span>' % (c, text)

def fbuffer(f, chunk_size=10000):
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
    try:
	f = open(os.path.join(UPLOAD_DIR, clean_fn), 'wb')
	for chunk in fbuffer(filefield.file):
	    f.write(chunk)
    except IOError:
	MESSAGE = span("An error occurred writing the file.", "error")
    finally:
	f.close()
    MESSAGE = span("%s was successfully uploaded." % (clean_fn), "ok")
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
