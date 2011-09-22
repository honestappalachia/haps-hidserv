haps-hidserv
------------

A Tor hidden service for anonymous file upload, using thttpd and Python.
Developed on Ubuntu 10.04, but is expected to work on any *nix.

Setup
-----

1.  [Install Tor]
2.  [Install thttpd]
3.  [Set Up a Hidden Service]
4.  Clone this repo

The directory structure of this repo is set up so everything should work "out of the box." All you will have to do is edit the following settings in thttpd.conf to match your local environment and installation directory: dir, user, data-dir, logfile, pidfile

To launch the website, `thttpd -C thttpd.conf`. To kill thttpd, `killall thttpd` or (slightly cooler)

    kill -9 `cat run/thttpd.pid`

If you're having trouble, try running with the debug flag: `thttpd -C thttpd.conf -D`. Note this will also prevent thttpd from running as a background daemon. This behavior can be useful, especially if you want to run thttpd from a script: see the man page for more information.

The site will be running at localhost:5222 (or whatever options you set for host and port in thttpd.conf). 

Notes
-----

The thttpd setup here is bare-bones and designed for development.

**IMPORTANT:** note the chroot option is disabled. If you enable it, none of the CGI scripts will work unless you hand-build a chroot environment to accompany them. Although this is not hard to do, it is not necessary for development and would waste a lot of space in the repo.

Also note that the permissions on the files are world-readable, which means you thttpd will allow you to index them. Try visiting localhost:5222/uploads to see what I mean. 

For these reasons among others, we do not recommend deploying this site as-is. Do so at your own risk.

[install tor]: https://www.torproject.org/docs/tor-doc-unix.html.en
[install thttpd]: http://acme.com/software/thttpd/
[set up a hidden service]: https://www.torproject.org/docs/tor-hidden-service.html.en
