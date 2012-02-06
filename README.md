haps-hidserv
============

A Tor hidden service for anonymous file upload, using Apache and Python.
Developed for Ubuntu 10.04/Debian Squeeze, but should work (with minor modifications) on any Linux.

What is here?
-------------

1.  hiddenservice.onion

    Apache virtualhost configuration file for hidden service

2.  htdocs/index.html

    Simple upload form. The upload is handled by the upload.py CGI script.

3.  htdocs/cgi-bin/upload.py

    CGI script that handles file uploads.

4.  htdocs/cgi-bin/upload_handler.py

    Process file uploads.

5.  htdocs/cgi-bin/mylogging.py

    Wrapper for logging

Setup The Easy Way
==================

Run mkhonest-debian (or mkhoenst-ubuntu10.04) as root. You will be prompted to make a password for the user that process uploads.

After the script is finished running, you need to set up your cryptographic keys.

You need to generate two GPG keys. We will call them the client key and the server key. The client key is the key used to encrypt the files received by the hidden service. The server key only exists to sign the client public key. This is not really necessary but works the way GPG was intended to; it complains (and python-gnupg fails silently) if you try to encrypt a file with an untrusted public key.

You should have a computer that you intend to use to decrypt files. Ideally this would be a physical machine in a secured location that you can use to download files, then air gap for decryption and processing. You can also use a laptop or a virtual machine - just recognize the importance of this machine and secure it accordingly.

On this machine, generate a new GPG key.

    $ gpg gen-key

We recommend using 4096 bit RSA. Use a strong passphrase.

We recommend generating a revocation certificate and storing it in a secure location:

    $ gpg --armor --gen-revoke mykey > revoke.asc

We also recommend backing up the key, including the private key, to a secure and encrypted location.

    $ gpg --export-secret-keys --armor mykey > privatekey.asc
    $ gpg --export --armor mykey > publickey.asc

This is so you wont get locked out of your system in case of some catastrophic failure.

Now you will need to generate the server key on your server. Log in to the server as the user who will be encrypting files (this is important - each user has their own GPG keyring) and `gpg --gen-key`. Same recommendations as before. Note that generating crypto keys on headless servers or VPS can be very difficult; there isnt much entropy to work with. Our install script installs the [haveged daemon] to mitigate this issue. 

Copy the exported client public key to the server and import it into your keyring.

    $ gpg --import publickey.asc

Now you need to use the server key to sign the imported client public key so you can use the client public key to encrypt documents.

    $ gpg --edit-key publickey
    > ...
    > fpr

To be super-safe, check the fingerprint against the fingerprint on the client machine. You can also get the fingerprint like this:

    $ gpg --fingerpint mykey

Back to the server. Once youve verified the fingerprints, go ahead and sign the client public key on the server:

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

Setup The Hard Way
==================

**Warning: Out of date**

You will need to run these commands as root or use sudo.

1.  [Install Tor]
2.  [Install Apache]
    `apt-get install apache2 apache2-doc apache2-utils`
    `apt-get install libapache2-mod-python`
3.  [Set Up a Hidden Service]
4.  Clone this repo
5.  [Install gnupg]
    `apt-get install gnupg`
6.  [Install beanstalkd]
    `apt-get install beanstalkd`
6.  Install Python dependencies. We recommend using pip. To install pip
    1.	`apt-get install python-setuptools`
    2.	`easy_install pip`
    3.	Now, to install <packagename>: `pip install <packagename>`

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

[install tor]: https://www.torproject.org/docs/tor-doc-unix.html.en
[Install Apache]: http://library.linode.com/web-servers/apache/installation/ubuntu-10.04-lucid
[set up a hidden service]: https://www.torproject.org/docs/tor-hidden-service.html.en
[python-magic]: https://github.com/ahupp/python-magic
[Install beanstalkd]: http://kr.github.com/beanstalkd/
[beanstalkc]: https://github.com/earl/beanstalkc
[Install gnupg]: http://www.gnupg.org/
[python-gnupg]: http://code.google.com/p/python-gnupg/
[boto]: http://code.google.com/p/boto/
[python-daemon]: http://pypi.python.org/pypi/python-daemon
[haveged daemon]: http://www.irisa.fr/caps/projects/hipsor/ 
