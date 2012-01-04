haps-hidserv
============

A Tor hidden service for anonymous file upload, using Apache and Python.
Developed on Ubuntu 10.04, but should work (with minor modifications) on any *nix.

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

Setup
=====

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
2.  [boto]
    Amazon Web Services (AWS) library

[install tor]: https://www.torproject.org/docs/tor-doc-unix.html.en
[install apache2]: http://library.linode.com/web-servers/apache/installation/ubuntu-10.04-lucid
[set up a hidden service]: https://www.torproject.org/docs/tor-hidden-service.html.en
[python-magic]: https://github.com/ahupp/python-magic
[Install beanstalkd]: http://kr.github.com/beanstalkd/
[beanstalkc]: https://github.com/earl/beanstalkc
[Install gnupg]: http://www.gnupg.org/
[python-gnupg]: http://code.google.com/p/python-gnupg/
[boto]: http://code.google.com/p/boto/
