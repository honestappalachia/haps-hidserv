#!/bin/bash

# Run as root on fresh Ubuntu 10.04LTS instance

# What will the shell script do?
# Lock down access, set up firewall
# Install packages
# Set up hidden service
# Goal: achieve Debian/Ubuntu compat., start with Ubuntu 10.04 LTS

# mkhonest.sh -- this install script
# hiddenservice.onion -- Apache virtualhost config
# htdocs/ -- upload site document root
# honesttables.sh -- iptables rules (as shell script)

# Exit immediately if a simple command exits with a non-zero
# status, unless the command that fails is part of an until or
# while loop, part of an if statement, part of a && or || list,
# or if the command's return status is being inverted using !
set -e

erro() {
  echo "$@"
  exit 1
}

### PACKAGES ###

# Make sure we're up to date
apt-get update && apt-get upgrade

# Install Tor
# https://www.torproject.org/docs/debian#ubuntu
DISTRIBUTION=$(lsb_release -c | awk '{ print $2 }')
echo "deb http://deb.torproject.org/torproject.org $DISTRIBUTION main" >> /etc/apt/sources.list
gpg --keyserver keys.gnupg.net --recv 886DDD89
gpg --export A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89 | sudo apt-key add -
apt-get update
apt-get install tor tor-geoipdb

# Set up Tor Hidden service
echo "
### HONEST HIDDEN SERVICE CONFIGURATION ###
HiddenServiceDir /var/lib/tor/hidden_service/
HiddenServicePort 80 127.0.0.1:5222
" >> /etc/tor/torrc
/etc/init.d/tor restart

# Install Apache
# http://library.linode.com/web-servers/apache/installation/ubuntu-10.04-lucid
# TODO: Do I need to set the hostname?
# echo "bradley" > /etc/hostname
# hostname -F /etc/hostname
apt-get install apache2 apache2-doc apache2-utils
apt-get install libapache2-mod-python
# suexec support
# apt-get install apache2-suexec
# apache2-suexec-custom allows configuration through a file, not compiled in
apt-get install apache2-suexec-custom
a2enmod suexec
# Copy suexec config
cp suexec_www-data /etc/apache2/suexec/www-data
# Disable default site
a2dissite default
# Clear out default port configuration
cp /etc/apache2/ports.conf /etc/apache2/ports.conf.original
echo "" > /etc/apache2/ports.conf
# Copy and enable the hidden service vhost configuration
cp hiddenservice.onion /etc/apache2/sites-available/
a2ensite hiddenservice.onion
# Restart Apache to enable everything
/etc/init.d/apache2 restart

# Install beanstalkd
apt-get install beanstalkd
# TODO: Beanstalkd startup script

# Set up upload site
apt-get install python-setuptools
easy_install pip
# Install Python dependencies
pip install beanstalkc python-gnupg boto

# Transparent Tor proxy
# add at end so we don't have to install a bunch of software through Tor
echo "
### TRANSPARENT TOR PROXY ###
VirtualAddrNetwork 10.192.0.0/10
AutomapHostsOnResolve 1
TransPort 9040
DNSPort 53
" >> /etc/tor/torrc
/etc/init.d/tor restart

# Resolve DNS through Tor
cp /etc/resolv.conf /etc/resolv.conf.original
echo "nameserver 127.0.0.1" > /etc/resolv.conf

# Copy iptables rules to startup script and run it to set up firewall
cp honesttables /etc/init.d/honesttables
chmod a+x /etc/init.d/honesttables
/etc/init.d/honesttables

# Setting up users and permissions

# Adding the admin user
# Force them to do this, or just recommend it?
# Combined with SSH lockdown

# Adding the honest user
# -m creates a home directory for the user
useradd -m -s /bin/bash honest
echo "
Created user honest.
honest executes the upload CGI and handles the worker processes
Choose a strong password for the user honest:
"
passwd honest

# Set up honest home directory
cp -r htdocs/ /home/honest/
chown -R honest:honest /home/honest/
chmod -R 755 /home/honest # 700?

# Copy suexec config
cp suexec_www-data /etc/apache2/suexec/www-data

# Output results here:
HS_HOSTNAME = $(cat /var/lib/tor/hidden_service/hostname)
echo "The .onion address of the upload hidden service is $HS_HOSTNAME"