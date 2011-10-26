#!/usr/bin/env python
"""
This beanstalk worker processes file uploads to the hidden service.

When it receives a file, the web process copies it to a temporary directory and
puts a job on the running beanstalk process storing the file's absolute path.

The worker process regularly checks the beanstalk queue for jobs to process.
If it finds one, it

    1. Encrypts the file using the PUBLIC_KEY_ID public key
    2. Copies it to Amazon S3
    3. shreds the original file
"""

import sys, os
import subprocess
import time
import beanstalkc
import gnupg
from mylogging import debug, info, warning, error, critical

from boto.s3.connection import S3Connection
from boto.s3.key import Key

### SETTINGS ###
PUBLIC_KEY_ID = ''  # public key to use to encrypt files
                    # stored in gpg keyring
AWS_ACCESS_KEY = ''
AWS_SECRET_KEY = ''

BUCKET_NAME = 'haps-dev'
TEMP_DIR = "/tmp"

try:
    from settings import *
except ImportError:
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

def run(program):
    '''
    Run program

    program --  string of shell command, including options
    returns the processes' return code
    '''
    process = subprocess.Popen(
        '%s' % program,
        shell=True
    )
    rc = process.wait() # wait to terminate
    return rc

def encrypt_file(source_file, destination_dir, key):
    '''
    GPG-encrypts source_file with key, saving encrypted file to destination_dir

    f   --  absolute path to the file to encrypt
    destination_dir --  absolute path to directory to save encrypted file in
    key --  keyid of public key to use; must be saved in gpg keyring

    Returns path to the encrypted file
    '''
    # init gpg
    gpg = gnupg.GPG() # use default - current user's $HOME/.gpg
    public_keys = gpg.list_keys()
    assert key in [k['keyid'] for k in public_keys], \
        "Could not find the specified PUBLIC_KEY_ID in keyring"

    # build encrypted filename and path
    e_filename = source_file.split("/")[-1] + ".gpg"
    ef_path = os.path.join(destination_dir, e_filename)

    try:
        fp = open(source_file, 'rb')
        encrypted_data = gpg.encrypt_file(
            fp,             # file object to encrypt
            key,            # public key of recipient
            output=ef_path  # path to encrypted file
        )
        fp.close()
    except IOError as e:
        error(e)

    debug("Encrypted %s -> %s" % (source_file, ef_path))

    return ef_path

def upload_to_s3(local_file, bucket_name, key_name=None, acl='private'):
    '''
    Uploads local_file to bucket_name on Amazon S3

    key_name is the "filename" on Amazon S3. We'll default to the local file's name if
    no alternative key_name is specified.
    '''
    # connect to Amazon S3
    conn = S3Connection(AWS_ACCESS_KEY, AWS_SECRET_KEY)
    bucket = conn.create_bucket(bucket_name)
    k = Key(bucket)
    
    if key_name:
        k.key = key_name
    else:
        k.key = local_file.split("/")[-1]

    k.set_contents_from_filename(local_file)
    k.set_acl(acl)

    debug("Uploaded %s to S3" % local_file)

def shred(f):
    '''
    Uses the *nix command shred to seriously erase f
    '''
    # check to see if we have shred installed; should this be an
    # assertionError, or a warning (and we default to rm)?
    assert whereis("shred") is not None, "Please install shred."
    process = subprocess.Popen(['shred', '-fuz', f], shell=False)
    if process.wait() == 0: # wait for shred to complete, check return code
        debug("Shredded %s" % f)
    else: # some kind of error occurred; handle
        error("shredding the file failed: shred returned %s" % (process.returncode))

def main():

    # Open connection to beanstalkd
    beanstalk = beanstalkc.Connection(host='localhost', port=11300)

    # infinite loop, handle jobs as they come
    while(True):

        if beanstalk.peek_ready():  # is there something in the queue?
            job = beanstalk.reserve(timeout=0)
            # job.body should be an absolute path to a file
            assert os.path.isfile(job.body), \
            "job.body does not reference a file: %s" % job.body

            info("Processing %s" % job.body)

            # encrypt file
            ef_path = encrypt_file(job.body, TEMP_DIR, PUBLIC_KEY_ID)
            # upload to s3
            upload_to_s3(ef_path, BUCKET_NAME)
            # shred encrypted and original file
            shred(job.body)
            shred(ef_path)

            # we handled that job; remove it from the queue
            job.delete()
        else:
            # debug("No job found")
            pass

        time.sleep(5)  # how often to check and handle a job

if __name__ == "__main__": main()
