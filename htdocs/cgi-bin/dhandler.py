#!/usr/bin/env python
"""
Script run by upload.py when a file is received. 

Given an uploaded file and its summary file, 

    1. Archives them
    2. Encrypts the archive
    3. Uploads the encrypted archive to S3
    4. Shreds everything
"""

import sys, os
import subprocess
import datetime

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

def encrypt_file(source_file, destination_dir, key):
    '''
    GPG-encrypts source_file with key, saving encrypted file to destination_dir

    source_file     --  absolute path of file to encrypt
    destination_dir --  absolute path of directory to save encrypted file in
    key             --  keyid of public key to use; must be saved in gpg keyring

    Returns path to the encrypted file
    '''
    # Init GPG
    gpg = gnupg.GPG("/home/anon/.gpg") # Defaults to current user's $HOME/.gpg
    public_keys = gpg.list_keys()
    assert key in [k['keyid'] for k in public_keys], \
        "Could not find the specified PUBLIC_KEY_ID in keyring"

    # Build encrypted filename and path
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
        LOG.error(e)

    LOG.info("Encrypted %s -> %s" % (source_file, ef_path))

    return ef_path

def upload_to_s3(local_file, bucket_name, key_name=None, acl='private'):
    '''
    Uploads local_file to bucket_name on Amazon S3

    key_name is the "filename" on Amazon S3, defaults to the local file's name
    '''
    # connect to Amazon S3
    conn = S3Connection(AWS_ACCESS_KEY, AWS_SECRET_KEY)
    bucket = conn.create_bucket(bucket_name)
    k = Key(bucket)
    
    if key_name:
        k.key = key_name
    else:
        k.key = local_file.split("/")[-1]

    # encrypt_key=True for AES-256 encryption while at rest on Amazon's servers
    k.set_contents_from_filename(local_file, encrypt_key=True)
    k.set_acl(acl)

    LOG.info("Uploaded %s to S3" % local_file)

def shred(f):
    '''
    Uses the *nix command shred to seriously erase f
    '''
    # check to see if we have shred installed; should this be an
    # assertionError, or a warning (and we default to rm)?
    assert whereis("shred") is not None, "Please install shred."
    process = subprocess.Popen(['shred', '-fuz', f], shell=False)
    if process.wait() == 0: # wait for shred to complete, check return code
        LOG.info("Shredded %s" % f)
    else: # some kind of error occurred; handle
        LOG.error("shredding the file failed: shred returned %s" % (process.returncode))

def archive(*files):
    '''
    *files is an arbitrary number of absolute paths to files
    Files are archived and timestamped
    '''
    paths = []
    filenames = []
    for f in files:
        if os.path.isfile(f):
            paths.append("/".join(f.split("/")[:-1]))
            filenames.append(f.split("/")[-1])

    # build arg list to tar
    # -C path filename for each file
    arg_list = []
    for x in zip(paths, filenames):
        arg_list.append("-C")
        arg_list.append(x[0])
        arg_list.append(x[1])

    # timestamp - could this be used against us?
    archive_name = datetime.datetime.now().strftime("%Y-%m-%dT%H%M%S") + ".tgz"
    archive_path = os.path.join(TEMPORARY_DIR, archive_name)

    tar_cmd = ['tar', 'czvf', archive_path]
    tar_cmd.extend(arg_list)
    process = subprocess.Popen(tar_cmd, shell=False)
    rc = process.wait()
    LOG.info(tar_cmd)
    assert rc == 0, "Archiving step failed with return code %s" % rc

    return archive_path

def main():
    '''
    Takes command line args as absolute paths to files to handle
    '''
    if len(sys.argv) < 2: # program name is first arg
        sys.exit("Must provide at least one file to process")

    filenames = sys.argv[1:]

    LOG.info("upload_handler enter")

    try:
        # Archive the files
        archive_path = archive(*filenames)
        # Encrypt the archive
        ea_path = encrypt_file(archive_path, TEMPORARY_DIR, PUBLIC_KEY_ID)
        # upload to S3
        upload_to_s3(ea_path, AWS_BUCKET)
        # shred everything
        for fn in filenames:
            shred(fn)
        shred(archive_path)
        shred(ea_path)
    except Exception, err:
        LOG.error(err)

    LOG.info("upload_handler exit")

if __name__ == "__main__": main()
