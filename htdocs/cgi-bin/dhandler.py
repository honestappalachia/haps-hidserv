#!/usr/bin/env python
"""
Script run by upload.py when a file is received. 

Given an uploaded file and its summary file, 

    1. Archives them
    2. Encrypts the archive
    3. Uploads the encrypted archive to S3
    4. Shreds everything
"""

import os
import sys
import subprocess
import hashlib
from datetime import datetime
import zipfile
import random

import gnupg
from boto.s3.connection import S3Connection
from boto.s3.key import Key

import logwrapper as LOG

# Settings
# To store deployment settings, save them in a local file settings.py
# settings.py is in .gitignore, so you can safely use git
PUBLIC_KEY_ID = '' # public key to encrypt files, must be in gpg keyring
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

def write_summary_file(upload, comment):
    """
    Upload and comment are paths to the uploaded file and the comment file
    Returns the path to the summary file
    """
    # Extract filename from upload file path
    filename = upload.split("/")[-1]
    # Get comment
    with open(comment, 'r') as f:
        comment = f.read()
    summary_filename = "%s-summary" % filename
    sf_path = os.path.join(TEMPORARY_DIR, summary_filename)
    sf = open(sf_path, 'w')
    sf.write("Filename: %s\n" % filename)
    sf.write("  SHA256: %s\n" % sha256(upload))
    sf.write(" Comment: %s\n" % comment)
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
    # Name based on the SHA256 sum of the first file
    sha = sha256(paths[0])
    archive_name = sha[:16] + ".zip"
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
        LOG.error("Shredding %s failed: shred returned %s"
            % (f, process.returncode))

def main():
    '''
    Takes command line args as absolute paths to files to handle
    '''
    if len(sys.argv) < 2: # program name is first arg
        sys.exit("Must provide at least one file to process")

    filenames = sys.argv[1:]

    try:

        # Write summary file
        sf_path = write_summary_file(filenames[0], filenames[1])

        # Write noise file
        nf_path = write_noise_file()
    
        # Archive the files
        archive_path = archive(filenames[0], sf_path, nf_path)

        # Encrypt the archive
        ea_path = encrypt(archive_path)

        # Upload to S3
        upload_to_s3(ea_path)

        # Shred everything
        for fn in filenames:
            shred(fn)
        shred(sf_path)
        shred(nf_path)
        shred(archive_path)
        shred(ea_path)

    except Exception, err:
        LOG.error(err)

if __name__ == "__main__": main()
