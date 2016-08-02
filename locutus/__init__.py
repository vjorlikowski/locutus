# Copyright (c) 2016 Duke University.
# This software is distributed under the terms of the MIT License,
# the text of which is included in this distribution within the file
# named LICENSE.
#
# Portions of this software are derived from the "rest_router" controller
# application included with Ryu (http://osrg.github.io/ryu/), which is:
# Copyright (C) 2013 Nippon Telegraph and Telephone Corporation.
#
# Modifications and additions were made to the original content by the
# following authors:
# Author: Victor J. Orlikowski <vjo@duke.edu>

# Common imports
import struct

from ryu import cfg
from ryu.lib import hub
from ryu.lib import dpid as dpid_lib
from ryu.lib import mac as mac_lib
from ryu.lib.packet import arp
from ryu.lib.packet import dhcp
from ryu.lib.packet import ethernet
from ryu.lib.packet import icmp
from ryu.lib.packet import ipv4
from ryu.lib.packet import packet
from ryu.lib.packet import tcp
from ryu.lib.packet import udp
from ryu.lib.packet import vlan
from ryu.ofproto import ether
from ryu.ofproto import inet
from ryu.ofproto import ofproto_v1_0
from ryu.ofproto import ofproto_v1_2
from ryu.ofproto import ofproto_v1_3

# Application constant definitions and configuration setup
__author__ = "Victor J. Orlikowski"
__copyright__ = "Copyright 2016, Duke University"
__credits__ = ["Victor J. Orlikowski", "Nippon Telegraph and Telephone Corporation"]
__license__ = "MIT"
__version__ = '0.1'
__maintainer__ = "Victor J. Orlikowski"
__email__ = "vjo@duke.edu"

UINT16_MAX = 0xffff
UINT32_MAX = 0xffffffff
UINT64_MAX = 0xffffffffffffffff

ETHERNET = ethernet.ethernet.__name__
VLAN = vlan.vlan.__name__
SVLAN = vlan.svlan.__name__
IPV4 = ipv4.ipv4.__name__
ARP = arp.arp.__name__
ICMP = icmp.icmp.__name__
TCP = tcp.tcp.__name__
UDP = udp.udp.__name__
DHCP = dhcp.dhcp.__name__

SWITCHID_PATTERN = dpid_lib.DPID_PATTERN + r'|all'
DOMAINID_PATTERN = r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}' + r'|all'

VLANID_NONE = 0
VLANID_MIN = 2
VLANID_MAX = 4094

INADDR_ANY_BASE = '0.0.0.0'
INADDR_ANY_MASK = '0'
INADDR_ANY = INADDR_ANY_BASE + '/' + INADDR_ANY_MASK

INADDR_BROADCAST_BASE = '255.255.255.255'
INADDR_BROADCAST_MASK = '32'
INADDR_BROADCAST = INADDR_BROADCAST_BASE + '/' + INADDR_BROADCAST_MASK

# FIXME:
# Implement idle and hard timeouts, for switches that don't do them right.
L2_IDLE_TIMEOUT = 90   # sec
L3_IDLE_TIMEOUT = 180  # sec
DEFAULT_TTL = 64

REST_COMMAND_RESULT = 'command_result'
REST_RESULT = 'result'
REST_DETAILS = 'details'
REST_OK = 'success'
REST_NG = 'failure'
REST_ALL = 'all'
REST_SWITCHID = 'switch_id'
REST_VLANID = 'vlan_id'
REST_NW = 'internal_network'
REST_ADDRESSID = 'address_id'
REST_ADDRESS = 'address'
REST_ROUTEID = 'route_id'
REST_ROUTE = 'route'
REST_DESTINATION = 'destination'
REST_DESTINATION_VLAN = 'destination_vlan'
REST_GATEWAY = 'gateway'
REST_GATEWAY_MAC = 'gateway_mac'
REST_SOURCE = 'source'
REST_BARE = 'bare'
REST_WIPE = 'wipe'
REST_DHCP = 'dhcp_servers'
