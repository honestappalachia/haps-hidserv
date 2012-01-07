#!/bin/sh

# Firewall rules for Honest Appalachia Hidden Service

# Transparent Tor Proxy
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

# Tor's username 
# You may need to check this on your system. 
TOR_UNAME="debian-tor"

# Tor's TransPort
TRANS_PORT="9040"

# Flushes all rules in the default (filter) table and the nat table
# The nat table is consulted when a packet that creates a new connection is encountered
iptables -F
iptables -t nat -F

# NAT table rules
# allow packets from Tor user
iptables -t nat -A OUTPUT -m owner --uid-owner $TOR_UNAME -j RETURN
# redirect UDP traffic to port 53, Tor's DNSPort
iptables -t nat -A OUTPUT -p udp --dport 53 -j REDIRECT --to-ports 53

# allow traffic to any NON_TOR IP and localhost 
# check on the meaning of this / notation
for NET in $NON_TOR 127.0.0.0/9 127.128.0.0/10; do
 iptables -t nat -A OUTPUT -d $NET -j RETURN
done

# Redirect all tcp traffic to Tor TRANS_PORT
# The --syn flag only matches TCP packets with SYN bit set and the ACK, RST,
# and FIN bits cleared - a packet used to a request TCP connection initiation.
iptables -t nat -A OUTPUT -p tcp --syn -j REDIRECT --to-ports $TRANS_PORT

# Filter table rules
# Only allow Tor and established connections (important so we can still SSH) to go out.

# allow all established connections
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# allow connections out to NON_TOR and localhost
for NET in $NON_TOR 127.0.0.0/8; do
 iptables -A OUTPUT -d $NET -j ACCEPT
done

# allow Tor to connect out
iptables -A OUTPUT -m owner --uid-owner $TOR_UNAME -j ACCEPT

# reject all other outgoing connections
iptables -A OUTPUT -j REJECT

# General Firewall rules

# Drop packets unless explicitly allowed
iptables -P INPUT DROP
iptables -P FORWARD DROP
# iptables -P OUTPUT ACCEPT

# loopback interface
iptables -I INPUT -i lo -j ACCEPT

# SSH, Web server, Tor
# Might not need the Tor ports given the previous rules
iptables -A INPUT -p tcp -m multiport --destination-ports 22,80,9001,9030,9050

# allow established connections on INPUT
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
