*Note:* if Tor is misbehaving, make sure you check the logs in ``/var/log/tor/``

Install and set up Apache for the hidden service:

Info from: http://library.linode.com/web-servers/apache/installation/ubuntu-10.04-lucid

Install necessary packages:

    # apt-get install apache2 apache2-doc apache2-utils
    # apt-get install libapache2-mod-python

Disable the default Apache virtual host:

    # a2dissite default

Each additional virtual host needs its own file in ``/etc/apache2/sites-available``
This repo includes an example configuration file: ``hiddenservice.onion``

** Setup hiddenservice directories **

Once that is done, enable the site:

    # a2ensite hiddenservice.onion

And restart Apache:

    # /etc/init.d/apache2 restart

Apache Documentation on CGI (with info on permissions): http://httpd.apache.org/docs/2.2/howto/cgi.html

Other changes to Apache configuration files?

ErrorDocument -> blank strings

Move NamedVirtualHost and Listen commands from ports.conf to hiddenservice.org
Why? Now we can just backup ports.conf, replace it with an empty file, and hiddenservice.org will take care of the rest. Nice that we can put almost all of the configuration in one file. The reamining default Apache configuration is minimal and fine (it is in ``/etc/apache2/apache2.conf``)

It appears that the default error configuration from Apache actually does *not* list the IP address of the server. This is in Apache 2 on Ubuntu 10.04 LTS. It lists the .onion name instead. That is cool, but we will still override the ErrorDocuments just in case. 
