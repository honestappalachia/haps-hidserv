cgi-bin
-------

There are two sets of upload scripts, corresponding to how they handle processing received uploads.

There are two CGI scripts: `qupload.py` and `dupload.py`. `qupload.py` puts the receieved file in a beanstalkd job queue for later processing. The beanstalkd worker is `qworker.py` and is in the root level of this repository. It needs to be running as a daemon to process jobs. `dupload.py` *directly* calls an upload handler process called `dhandler.py`.

Why? The dupload method is easier to set up. qupload is more flexible and allows us to further customize the upload process and easily add obfuscation to the upload flow.

All upload scripts must be run by the `honest` user. 

Make sure the correct CGI script is set in the upload form's "action" parameter in `index.html`.
