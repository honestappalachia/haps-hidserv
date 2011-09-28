#!/usr/bin/env python
import sys, os
import subprocess
import beanstalkc
import gnupg

from boto.s3.connection import S3Connection
from boto.s3.key import Key

### SETTINGS ###
PUBLIC_KEY_ID = ''  # public key to use to encrypt files
		    # stored in gpg keyring
AWS_ACCESS_KEY = ''
AWS_SECRET_KEY = ''
BUCKET_NAME = ''

TEMP_DIR = "/tmp"

try:
    from settings import *
except:
    pass

def whereis(program):
    '''
    Returns the path to program on a user's path, if it exists
    Returns None if it does not
    '''
    for path in os.environ.get('PATH', '').split(':'):
        if os.path.exists(os.path.join(path, program)) and \
           not os.path.isdir(os.path.join(path, program)):
            return os.path.join(path, program)
    return None

# Open connection to beanstalkd
beanstalk = beanstalkc.Connection(host='localhost', port=11300)

# infinite loop, handle jobs as they come
while(True):
    # is there something in the queue?
    if beanstalk.peek_ready():
	job = beanstalk.reserve(timeout=0)
	# job should be an absolute path to a file
	assert os.path.isfile(job), "job does not reference a file: %s" % job

	# init gpg
	gpg = gnupg.GPG() # use default - current user's home
	public_keys = gpg.list_keys()
	assert PUBLIC_KEY_ID in [key['keyid'] for key in public_keys], \
	    "Could not find the specified PUBLIC_KEY_ID in keyring"

	source_file = job.body	# needs to be an absolute path to a file - assert?
	enc_filename = source_file.split("/")[-1] + ".gpg"
	enc_file_path = os.path.join(TEMP_DIR, enc_filename)
	try:
	    fp = open(source_file, 'rb')
	    encrypted_data = gpg.encrypt_file(
		fp, # file object to encrypt
		PUBLIC_KEY_ID, # encrypt for this recipient's public key
		# TODO: where to store encrypted files
		output = enc_file_path # path to encrypted file
	    )

	    # upload to s3
	    conn = S3Connection(AWS_ACCESS_KEY, AWS_SECRET_KEY)
	    bucket = conn.create_bucket(BUCKET_NAME) # returns bucket if it already exists
	    k = Key(bucket)
	    k.key = enc_filename
	    k.set_contents_from_filename(enc_file_path)
	    k.set_acl('private')

	    # shred
	    # check to see if we have shred installed; should this be an
	    # assertionError, or a warning (and we default to rm)?
	    assert whereis("shred") is not None, "Please install shred."
	    process = subprocess.Popen(['shred', '-fuz', source_file], shell=False)
	    if process.wait() == 0: # wait for shred to complete, check return code
		pass
	    else: # some kind of error occurred; handle
		print "An error occurred in shredding the file: shred returned %s" % (process.returncode)
	    
	except IOError as e:
	    print e

    time.sleep(10)  # how often to check and handle a job
