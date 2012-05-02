haps-hidserv
============

A Tor hidden service for anonymous file upload, using Apache and Python.
Developed for Ubuntu 10.04/Debian Squeeze, but should work (with minor modifications) on any Linux.

What is here?
-------------

1.  mkhonest-debian

    Install script that sets up everything but crypto keys

2.  hiddenservice.onion

    Apache virtualhost configuration file for hidden service

3.  htdocs/index.html

    Simple upload form. The upload is handled by the upload.py CGI script.

4.  htdocs/cgi-bin/qupload.py

    CGI script for handling submitted upload forms; puts jobs on beanstalkd queue

5.  qworker

    Listens (non-blocking) on beanstalkd queue and processes uploads. 

6.  logwrapper.py

    Wrapper for logging

7.  beanstalkd

    Configuration for /etc/default/beanstalkd

8.  honestfw

    Sets up highly restrictive firewall for a machine running only the hidden
    service. stop can be used to reset the firewall to (completely open) defaults
    for troubleshooting.

9.  suexec_www-data

    Configuration for Apache suexec module for running the cgi (and using gpg)

Setup The Easy Way
==================

Run mkhonest-debian as root. You will be asked to provide a password for the user that processes uploads.

After the script is finished running, you need to set up your cryptographic keys.

You need to generate two GPG keys - the client key and the server key. The client key is the key used to encrypt the files received by the hidden service. The server key only exists to sign the client public key. This is not really necessary but works the way GPG was intended to; it complains (and python-gnupg fails silently) if you try to encrypt a file with an untrusted public key.

You should have a computer that you intend to use to decrypt files. Ideally this would be a physical machine in a secured location that you can use to download files, then air gap for decryption and processing. You can also use a laptop or a virtual machine - just recognize the significance of this machine and secure it accordingly.

On this machine, generate a new GPG key.

    $ gpg gen-key

We recommend using 4096 bit RSA. Use a strong passphrase.

We recommend generating a revocation certificate and storing it in a secure location:

    $ gpg --armor --gen-revoke mykey > revoke.asc

We also recommend backing up the key, including the private key, to a secure and encrypted location.

    $ gpg --export-secret-keys --armor mykey > privatekey.asc
    $ gpg --export --armor mykey > publickey.asc

This is so you wont get locked out of your system in case of some catastrophic failure. Note that your private key is only as secure as the least secure medium it is transmitted over - we advise against sending it over any network.

Now you will need to generate the server key on your server. Log in to the server as the user who will be encrypting files (this is important - each user has their own GPG keyring) and `gpg --gen-key`. Same recommendations as before. Note that generating crypto keys on headless servers or VPS can be very difficult; there isnt much entropy to work with. Our install script installs the [haveged daemon] to mitigate this issue. 

Copy the exported client public key to the server and import it into your keyring.

    $ gpg --import publickey.asc

Now you need to use the server key to sign the imported client public key so you can use the client public key to encrypt documents.

    $ gpg --edit-key publickey
    > ...
    > fpr

To be super-safe, check the fingerprint against the fingerprint on the client machine. You can also get the fingerprint like this:

    $ gpg --fingerpint mykey

Back to the server. Once you've verified the fingerprints, go ahead and sign the client public key on the server:

    > sign

and follow the prompts. Exit the edit-key interface with `quit` or `Ctrl-D`. 

Your GPG keys are set up. The last thing you have to do is edit your settings.py file so it contains the client public keys keyid. We use the long key id, which you can get like this:

    $ gpg --list-keys --with-colon mykey

The long id is the fifth field. Make sure you have a line in your settings.py like this:

    PUBLIC_KEY_ID = 'longkeyid'

Finally you need to set up an Amazon AWS account. Once files are encrypted, they are uploaded to Amazon S3 for future access. You will need to find your AWS Access Key and AWS Secret Key. In the online AWS console, click your name in the upper right corner and select "Security Credentials". Keys are available in the Access Keys tab. Copy these to the following lines in settings.py:

    AWS_ACCESS_KEY = ''
    AWS_SECRET_KEY = ''

These 3 settings are the minimum required for a working hidden service. 

Python dependencies
-------------------

1.  [python-gnupg]
    gpg client library
2.  [beanstalkc]
    beanstalkd client library
3.  [boto]
    Amazon Web Services (AWS) library
4.  [python-daemon]
    Daemonizes python scripts

[beanstalkc]: https://github.com/earl/beanstalkc
[python-gnupg]: http://code.google.com/p/python-gnupg/
[boto]: http://code.google.com/p/boto/
[python-daemon]: http://pypi.python.org/pypi/python-daemon
[haveged daemon]: http://www.irisa.fr/caps/projects/hipsor/ 
