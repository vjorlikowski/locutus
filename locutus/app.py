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

# Locutus controller application entry point/main program

import requests
import urllib3.contrib.pyopenssl

from ryu.app.wsgi import ControllerBase
from ryu.app.wsgi import WSGIApplication
from ryu.base import app_manager
from ryu.controller import dpset
from ryu.controller import ofp_event
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import MAIN_DISPATCHER
from ryu.exception import OFPUnknownVersion
from ryu.exception import RyuException
from ryu.lib import hub

from locutus import *
from locutus.device import *
from locutus.domains import *
from locutus.util import *


class Locutus(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_0.OFP_VERSION,
                    ofproto_v1_2.OFP_VERSION,
                    ofproto_v1_3.OFP_VERSION]

    _CONTEXTS = {'dpset': dpset.DPSet,
                 'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(Locutus, self).__init__(*args, **kwargs)

        # logger configure
        LocutusController.set_logger(self.logger)

        wsgi = kwargs['wsgi']
        self.waiters = {}
        self.data = {'waiters': self.waiters}

        mapper = wsgi.mapper
        wsgi.registory['LocutusController'] = self.data

        requirements = {'switch_id': SWITCHID_PATTERN}
        path = '/devices/{switch_id}'
        mapper.connect('devices', path, controller=LocutusController,
                       requirements=requirements,
                       action='get_data',
                       conditions=dict(method=['GET']))
        mapper.connect('devices', path, controller=LocutusController,
                       requirements=requirements,
                       action='set_data',
                       conditions=dict(method=['POST']))
        mapper.connect('devices', path, controller=LocutusController,
                       requirements=requirements,
                       action='delete_data',
                       conditions=dict(method=['DELETE']))

        requirements = {'domain_id': DOMAINID_PATTERN}
        path = '/domains/{domain_id}'
        mapper.connect('domains', path, controller=LocutusController,
                       requirements=requirements,
                       action='get_data',
                       conditions=dict(method=['GET']))
        mapper.connect('domains', path, controller=LocutusController,
                       requirements=requirements,
                       action='set_data',
                       conditions=dict(method=['POST']))
        mapper.connect('domains', path, controller=LocutusController,
                       requirements=requirements,
                       action='delete_data',
                       conditions=dict(method=['DELETE']))

        
# For API, the following is needed:
# 1) A means of retrieving the list of connected datapaths
# 2) A means of listing "slices" for a given datapath, or for *all* datapaths
# 3) A means of getting/setting/deleting data for any of those datapaths or slices
# 4) A means of blacklisting selected datapaths, or all datapaths that are unknown
# 5) As far as data is concerned - data to be set should correspond to how we want the switch to be sliced, and what the controller is for that slice
# 6) Which leads us to: we should be able to query the list of slices
# 7) Should we be able to assign a slice owner? How do we identify the slice owner? How do we validate their right to control the slice?
# 8) Nice to have - the ability to rate-limit packet-in forwarding to upstream controller
# 9) SSL cert validation for datapaths, and upstream controllers - plus sending client certificates.
        
    @set_ev_cls(dpset.EventDP, dpset.DPSET_EV_DISPATCHER)
    def datapath_handler(self, ev):
        if ev.enter:
            LocutusController.register_device(ev.dp, ev.ports, self.waiters)
        else:
            LocutusController.unregister_device(ev.dp)

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        datapath.n_tables = ev.msg.n_tables

    @set_ev_cls(dpset.EventDPReconnected, dpset.DPSET_EV_DISPATCHER)
    def datapath_change_handler(self, ev):
        LocutusController.reconnect_device(ev.dp, ev.ports, self.waiters)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        LocutusController.packet_in_handler(ev.msg)

    def _stats_reply_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath

        if (dp.id not in self.waiters
                or msg.xid not in self.waiters[dp.id]):
            return
        event, msgs = self.waiters[dp.id][msg.xid]
        msgs.append(msg)

        if ofproto_v1_3.OFP_VERSION == dp.ofproto.OFP_VERSION:
            more = dp.ofproto.OFPMPF_REPLY_MORE
        else:
            more = dp.ofproto.OFPSF_REPLY_MORE
        if msg.flags & more:
            return
        del self.waiters[dp.id][msg.xid]
        event.set()

    # for OpenFlow version1.0
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def stats_reply_handler_v1_0(self, ev):
        self._stats_reply_handler(ev)

    # for OpenFlow version1.2/1.3
    @set_ev_cls(ofp_event.EventOFPStatsReply, MAIN_DISPATCHER)
    def stats_reply_handler_v1_2(self, ev):
        self._stats_reply_handler(ev)

    #TODO: Update routing table when port status is changed.


class LocutusController(ControllerBase):
    _DEVICE_LIST = {}
    _DOMAIN_LIST = {}
    _LOGGER = None

    def __init__(self, req, link, data, **config):
        super(LocutusController, self).__init__(req, link, data, **config)
        self.waiters = data['waiters']

    @classmethod
    def set_logger(cls, logger):
        cls._LOGGER = logger

    @classmethod
    def register_device(cls, dp, ports, waiters):
        logger = DeviceLoggerAdapter(cls._LOGGER, {'sw_id': dpid_lib.dpid_to_str(dp.id)})
        logger.info('Device registered.')

    @classmethod
    def unregister_device(cls, dp):
        logger = DeviceLoggerAdapter(cls._LOGGER, {'sw_id': dpid_lib.dpid_to_str(dp.id)})
        logger.info('Device unregistered.')

    @classmethod
    def reconnect_device(cls, dp, ports, waiters):
        assert dp is not None
        if dp.id in cls._DEVICE_LIST:
            # Datapath changed, but router is still present.
            # Force re-creation of router object.
            cls.unregister_device(dp)
            cls.register_device(dp, ports, waiters)

    @classmethod
    def packet_in_handler(cls, msg):
        dp_id = msg.datapath.id
        # FIXME: Implement
