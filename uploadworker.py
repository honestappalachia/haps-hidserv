#!/usr/bin/env python
"""
An upload worker for Honest Appalachia

Processes uploaded files that are put on a beanstalkd queue by the upload.py
CGI script.
"""

import os
import sys
import subprocess
import json
import hashlib
from datetime import datetime
import zipfile
import random

import beanstalkc
import gnupg
from boto.s3.connection import S3Connection
from boto.s3.key import Key

import logwrapper as LOG

# Settings
# To store deployment settings, save them in a local file settings.py
# settings.py is in .gitignore, so you can safely use git
PUBLIC_KEY_ID = '' # public key to encrypt files, must be in GPG keyring
AWS_ACCESS_KEY = ''
AWS_SECRET_KEY = ''
AWS_BUCKET = 'haps-dev'
TEMPORARY_DIR = "/tmp"
MAX_NOISE_BYTES = 5 * (1024**2)
try:
    from settings import *
except ImportError:
    pass

# Make sure we have write access to TEMPORARY_DIR
try:
    testfn = os.path.join(TEMPORARY_DIR, "tempdirtest")
    f = open(testfn, "w")
    f.write("This is a test")
    f.close()
    os.remove(testfn)
except Exception, e:
    LOG.critical(
        "Failed performing file operations in TEMPORARY_DIR %s: %s"
         % (TEMPORARY_DIR, e)
    )
    sys.exit(1)

def sha256(path):
    """
    Returns the SHA256 sum of the file given by path
    """
    sha256 = hashlib.sha256()
    block_size = 8192
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(block_size), ''):
            sha256.update(chunk)
    return sha256.hexdigest()

def write_summary_file(job):
    """
    Writes a summary file of job
    Returns the path to the summary file
    """
    summary_filename = "%s-summary" % job['filename']
    sf_path = os.path.join(TEMPORARY_DIR, summary_filename)
    sf = open(sf_path, 'w')
    sf.write("Filename: %s\n" % job['filename'])
    sf.write("  SHA256: %s\n" % sha256(job['path']))
    sf.write(" Comment: %s\n" % job['comment'])
    sf.close()
    return sf_path

def write_noise_file():
    """
    Writes a NOISE file with a random amount of random bytes
    to obfuscate file size correlation
    """
    noise_path = os.path.join(TEMPORARY_DIR, "NOISE")
    num_bytes = random.randint(1, MAX_NOISE_BYTES)
    with open(noise_path, 'w') as f:
        for byte in xrange(num_bytes):
            f.write('%c' % random.randint(0, 255))
    return noise_path

def archive(*paths):
    """
    *paths is an arbitrary number of absolute paths to files
    Returns the path to the archive file
    """
    archive_name = datetime.now().strftime("%Y-%m-%dT%H%M%S") + ".zip"
    archive_path = os.path.join(TEMPORARY_DIR, archive_name)

    zf = zipfile.ZipFile(archive_path, mode='w')
    try:
        for p in paths:
            if os.path.isfile(p):
                zf.write(p, arcname=p.split("/")[-1])
            else:
                LOG.warning(
                    "Tried to archive %s, which is not a file. Skipping."
                    % p )
    except Exception, err:
        LOG.error("Error from archive(): %s", err)
    finally:
        zf.close()

    return archive_path

def encrypt(source_file,
    destination_dir=TEMPORARY_DIR, key=PUBLIC_KEY_ID):
    '''
    GPG-encrypts source_file with key, saving encrypted file to destination_dir

    source_file     --  absolute path of file to encrypt
    destination_dir --  absolute path of directory to save encrypted file in
    key             --  keyid of public key to use; must be in gpg keyring

    Returns path to the encrypted file
    '''
    # Init GPG
    gpg = gnupg.GPG() # Defaults to current user's $HOME/.gnupg
    public_keys = gpg.list_keys()
    assert key in [k['keyid'] for k in public_keys], \
        "Could not find PUBLIC_KEY_ID in keyring"

    # Build encrypted filename and path
    e_filename = source_file.split("/")[-1] + ".gpg"
    ef_path = os.path.join(destination_dir, e_filename)

    # Might be easier just to do this with subprocess
    # p = subprocess.Popen(
    #   ["gpg", "--output", ef_path, "--recipient", key, source_file],
    #   shell=False
    # )
    # if p.wait() == 0: ...
    # or use subprocess.call, .check_call, .check_output, etc

    try:
        fp = open(source_file, 'rb')
        encrypted_data = gpg.encrypt_file(
            fp,             # file object to encrypt
            key,            # public key of recipient
            output=ef_path  # path to encrypted file
        )
        fp.close()
    except IOError as e:
        LOG.error(e)

    # Hack - unfortunately, when GPG encrypts a file, it prints an error
    # message to the console but does not provide a specific error that
    # python-gnupg can use. So we need to double check.
    assert os.path.exists(ef_path), \
        "GPG encryption failed -- check the public key."

    LOG.info("Encrypted %s -> %s" % (source_file, ef_path))
    return ef_path

def upload_to_s3(local_file,
    bucket_name=AWS_BUCKET, key_name=None, acl='private'):
    '''
    Uploads local_file to bucket on Amazon S3
    key_name is the "filename" on Amazon S3, defaults to the local file's name
    '''
    # Connect to Amazon S3
    conn = S3Connection(AWS_ACCESS_KEY, AWS_SECRET_KEY)
    bucket = conn.create_bucket(bucket_name)
    k = Key(bucket)
    
    # Set key, defaulting to local file's name
    if key_name:
        k.key = key_name
    else:
        k.key = local_file.split("/")[-1]

    # encrypt_key=True for AES-256 encryption while at rest on Amazon's servers
    k.set_contents_from_filename(local_file, encrypt_key=True)
    k.set_acl(acl)

    LOG.info("Uploaded %s to S3 bucket %s" % (local_file, bucket_name))

def shred(f):
    '''
    Securely erases f with shred
    '''
    process = subprocess.Popen(['shred', '-fuz', f], shell=False)
    if process.wait() == 0: # wait for shred to complete, check return code
        LOG.info("Shredded %s" % f)
    else: # some kind of error occurred; log 
        LOG.error("shredding %s failed: shred returned %s"
            % (f, process.returncode))

def handle(body):
    """
    Handles an upload job from the queue
    """
    job = json.loads(body)

    # Write summary file
    sf_path = write_summary_file(job)

    # Write noise file
    nf_path = write_noise_file()
    
    # Archive upload, summary file, and NOISE file
    apath = archive(job['path'], sf_path, nf_path)

    # Encrypt archive
    epath = encrypt(apath)
    # Upload encrypted archive to S3
    upload_to_s3(epath)

    # Shred everything
    shred(job['path'])
    shred(sf_path)
    shred(nf_path)
    shred(apath)
    shred(epath)

# Start beanstalkd with: beanstalkd -l 127.0.0.1 -p 14711
# Optionally use -b to persist jobs
# Optionally use -d to run in background

# Open connection to beanstalkd
beanstalk = beanstalkc.Connection(host='localhost', port=14711)

# Handle jobs
try:
    while(True):
        # Option: implement interference with timeout=n
        # will this block in an annoying way?
        job = beanstalk.reserve() 
        try:
            # LOG.info("Handling %s" )
            handle(job.body)
            LOG.info("Handled %s" % json.loads(job.body)['filename'])
        except Exception, err:
            LOG.error("An error occurred handling %s: %s" % 
                (json.loads(job.body)['filename'], err)
            )
        job.delete()
except KeyboardInterrupt:
    pass
finally:
    beanstalk.close()
