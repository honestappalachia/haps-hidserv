#!/bin/sh

### HONESTTABLES ###
### FIREWALL RULES FOR HA HIDDEN SERVICE ###
### DRAFT 2 ###

### TRANSPARENT TOR PROXY ###

# This set of iptables rules transparently routes all outgoing traffic from
# this machine through Tor.

# First, setup Tor by adding the following to your torrc:
# VirtualAddrNetwork 10.192.0.0/10
# AutomapHostsOnResolve 1
# TransPort 9040
# DNSPort 53

# To prevent DNS leaks, we use Tor's DNSPort. You need to configure
# resolv.conf to use Tor's DNSPort on the loopback interface: 
# cp /etc/resolv.conf /etc/resolv.conf.orig
# echo "nameserver 127.0.0.1" > /etc/resolv.conf

# destinations you don't want routed through Tor
NON_TOR="192.168.1.0/24 192.168.0.0/24"

# the UID Tor runs as
# You may need to check this on your system. First find out what user Tor
# is running as. On Ubuntu 10.04 LTS, for example, this user is debian-tor.
# You can do this with the following command:
# TOR_UID = ps aux | grep /usr/sbin/tor | grep -v grep | awk '{ print $1 }'
# Or/Then get their user ID: id -u <username>
TOR_UID="debian-tor"

# Tor's TransPort
TRANS_PORT="9040"

# Flushes all rules in the default (filter) table
iptables -F
# Flushes all rules in the nat table
# This table is consulted when a packet that creates a new connection is encountered
iptables -t nat -F

### NAT RULES ###
### Redirect all outgoing traffic through Tor ###

# allow packets from Tor user
iptables -t nat -A OUTPUT -m owner --uid-owner $TOR_UID -j RETURN
# redirect UDP traffic to port 53, Tor's DNSPort
# Don't quite get this rule - are we just redirecting traffic that was bound for port 53 to port 53? That doesn't seem useful. Maybe this is why there is that additional /etc/resolv.conf hack.
iptables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-ports 53

# allow traffic to any NON_TOR IP and localhost 
# check on the meaning of this / notation
for NET in $NON_TOR 127.0.0.0/9 127.128.0.0/10; do
 iptables -t nat -A OUTPUT -d $NET -j RETURN
done

# redirect all tcp traffic to Tor TRANS_PORT
# the --syn flag only matches TCP packets with SYN bit set and the ACK,
# RST, and FIN bits cleared - a packet used to a request TCP connection
# initiation.
iptables -t nat -A OUTPUT -p tcp --syn -j REDIRECT --to-ports $TRANS_PORT

### END NAT RULES ###

### FILTER RULES ###
### Only allow Tor and established connections (important so we can still SSH)
### to go out.

# allow all established connections
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# allow connections out to NON_TOR and localhost
for NET in $NON_TOR 127.0.0.0/8; do
 iptables -A OUTPUT -d $NET -j ACCEPT
done

# allow Tor to connect out
iptables -A OUTPUT -m owner --uid-owner $TOR_UID -j ACCEPT

# reject all other outgoing connections
iptables -A OUTPUT -j REJECT

### END FILTER RULES ###

### END TRANSPARENT TOR PROXY ###

### LOCK DOWN ###

iptables -P INPUT DROP
iptables -P FORWARD DROP
# iptables -P OUTPUT ACCEPT

# loopback interface
iptables -I INPUT 1 -i lo -j ACCEPT

# SSH, Web server, Tor
# Might not need the Tor ports given the previous rules
iptables -A INPUT -p tcp -m multiport --destination-ports 22,80,9001,9030,9050

# allow established connections on INPUT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

### END LOCK DOWN ###
