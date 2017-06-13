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


from locutus import *
from locutus.ofctl import *
from locutus.tables import *
from locutus.util import *


# Note to self:
# OfCtl currently handles the multiple device types.
# Better to split OfCtl out? Maybe...
# Keep this as a subclass of dict? We need to know what domains are associated.
# Thing is - what will we use as the key for a domain?
# We're going to want to do fast lookups against domains, to move packets along.
class Device(dict):
    def __init__(self, dp, ports, waiters, logger):
        super(Device, self).__init__()
        self.dp = dp
        self.waiters = waiters
        self.logger = logger
        self.dpid_str = dpid_lib.dpid_to_str(dp.id)
        self.sw_id = {'sw_id': self.dpid_str}
        # FIXME: Figure out what else to maintain here, to answer a FeaturesRequest

        self.port_data = PortData(ports)
        self.logger.info('Known ports at switch connect time:')
        for port in self.port_data.keys():
            self.logger.info('\t%s', port)
        self.logger.info('Done listing known ports.')

        ofctl = OfCtl.factory(dp, logger)
        cookie = COOKIE_DEFAULT_ID

        # For now, clear all existing flows.
        ofctl.clear_flows()
        self.logger.info('Clearing pre-existing flows [cookie=0x%x]', cookie)

        # Device is connected, and awaiting being added to a domain.
        self.logger.info('Device initialization complete.')

    # FIXME: Ensure that port update gets pushed to all associated domains.
    # This will mean looping over the domains, and sending an update to all
    # those for which this port is/was defined.
    def port_update_handler(self, port):
        self.logger.info('Updating port data for port [%s].', port.port_no)
        self.port_data.update(port)

    # FIXME: Ensure that port update gets pushed to all associated domains.
    # This will mean looping over the domains, and sending an update to all
    # those for which this port is/was defined.
    def port_delete_handler(self, port):
        self.logger.info('Deleting port data for port [%s].', port.port_no)
        self.port_data.delete(port)

    def packet_in_handler(self, msg):
        pkt = None

        try:
            pkt = packet.Packet(msg.data)
        except:
            return None

        header_list = dict((p.protocol_name, p)
                           for p in pkt.protocols if type(p) != str)

        try:
            if header_list:
                # FIXME: This is where a fair amount of "meat and potatoes" is going to happen,
                # w.r.t. forwarding things to the appropriate domain, and then onward to the
                # appropriate controller.
                # We will need to find the "best-match" domain for this packet, and ensure that
                # the packet is injected into that domain.
                # At first cut, we will do slicing by VLANs only -
                # but we will get more complex soon.
                self.logger.debug('Domain selection unimplemented; dropping packet-in.')
        except:
            self.logger.exception('Exception encountered during packet-in processing. '
                                  'This may be a result of external datapath changes '
                                  'causing internal state inconsistency. '
                                  'Internal state should regain consistency shortly.')
