#!/usr/bin/env python
"""
Bootstrap Hidden Service
"""

import sys, os
import subprocess

def running(program):
    '''
    Returns True if program is running
    '''
    process = subprocess.Popen(
        'ps aux | grep -v grep | grep -w "%s"' % program,
        shell=True,
        stdout=subprocess.PIPE
    )
    output = process.communicate()[0] # returns tuple (stdout, stderr)
    if output:
        return True
    else:
        return False

def run(program):
    '''
    Run program

    program --  string of shell command, including options
    '''
    process = subprocess.Popen(
        '%s' % program,
        shell=True
    )

def check_or_start(program, command):
    '''
    Checks to see if program is running;
    If not, runs command
    '''
    if not running(program):
        print "%s was not running. Starting %s..." % (program, program),
        run(command)
        print "%s is running." % (command)
    else:
        print "%s was running when we checked" % (program)

def kill(program):
    '''
    Sends kill signal to specified program
    '''
    print "Killing %s" % program
    process = subprocess.Popen(
        'killall %s' % program,
        shell=True
    )

def usage():
    print '''
    Usage: bootstrap.py [OPTIONS]

    Options:
        -s, start       Bootstrap up
        -k, kill        Bootstrap down
    
    If run with no arguments, defaults to start.
    '''
    sys.exit(1)

def parse_cmdline(args):
    '''
    Parse command line options
    Returns a string containting the command issued
    Prints usage and exits if things go awry
    '''
    if len(args) == 1:
        # program called without arguments; default start
        return "start"
    elif len(args) == 2:
        if args[1] == "start" or args[1] == "-s":
            return "start"
        elif args[1] == "kill" or args[1] == "-k":
            return "kill"
        else:
            usage()
    else:
        usage()

def main():
    check_dict = {
        "tor":          "tor --runasdaemon 1",
        "beanstalkd":   "beanstalkd -d",
        "thttpd":       "thttpd -C thttpd.conf",
    }
    cmd = parse_cmdline(sys.argv)
    for program, command in check_dict.items():
        if cmd == "start":
            check_or_start(program, command)
        elif cmd == "kill":
            kill(program)

if __name__ == "__main__": main()
