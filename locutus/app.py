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
from locutus.domain import *
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

        path = '/devices'
        mapper.connect('devices', path, controller=LocutusController,
                       action='get_devices',
                       conditions=dict(method=['GET']))

        requirements = {'switch_id': SWITCHID_PATTERN}
        path = '/devices/{switch_id}'
        mapper.connect('devices', path, controller=LocutusController,
                       requirements=requirements,
                       action='get_device',
                       conditions=dict(method=['GET']))

        requirements = {'switch_id': SWITCHID_PATTERN}
        path = '/devices/{switch_id}/policy'
        mapper.connect('devices', path, controller=LocutusController,
                       requirements=requirements,
                       action='get_device_policy',
                       conditions=dict(method=['GET']))
        mapper.connect('devices', path, controller=LocutusController,
                       requirements=requirements,
                       action='update_device_policy',
                       conditions=dict(method=['PUT']))
        mapper.connect('devices', path, controller=LocutusController,
                       requirements=requirements,
                       action='create_device_policy',
                       conditions=dict(method=['POST']))
        mapper.connect('devices', path, controller=LocutusController,
                       requirements=requirements,
                       action='delete_device_policy',
                       conditions=dict(method=['DELETE']))

        requirements = {'switch_id': SWITCHID_PATTERN}
        path = '/devices/{switch_id}/domains'
        mapper.connect('devices', path, controller=LocutusController,
                       requirements=requirements,
                       action='get_device_domains',
                       conditions=dict(method=['GET']))

        path = '/domains'
        mapper.connect('domains', path, controller=LocutusController,
                       action='get_domains',
                       conditions=dict(method=['GET']))
        mapper.connect('domains', path, controller=LocutusController,
                       action='create_domain',
                       conditions=dict(method=['POST']))

        path = '/domains/{domain_id}'
        mapper.connect('domains', path, controller=LocutusController,
                       action='get_domain',
                       conditions=dict(method=['GET']))
        mapper.connect('domains', path, controller=LocutusController,
                       action='update_domain',
                       conditions=dict(method=['PUT']))
        mapper.connect('domains', path, controller=LocutusController,
                       action='delete_domain',
                       conditions=dict(method=['DELETE']))

        path = '/domains/{domain_id}/rules'
        mapper.connect('domains', path, controller=LocutusController,
                       action='get_domain_rules',
                       conditions=dict(method=['GET']))
        mapper.connect('domains', path, controller=LocutusController,
                       action='create_domain_rule',
                       conditions=dict(method=['POST']))

        path = '/domains/{domain_id}/rules/{rule_id}'
        mapper.connect('domains', path, controller=LocutusController,
                       action='update_domain_rule',
                       conditions=dict(method=['PUT']))
        mapper.connect('domains', path, controller=LocutusController,
                       action='delete_domain_rule',
                       conditions=dict(method=['DELETE']))

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
            cls.unregister_device(dp)
            cls.register_device(dp, ports, waiters)

    @classmethod
    def packet_in_handler(cls, msg):
        dp_id = msg.datapath.id
        pass

    # GET /devices
    @rest_command
    def get_devices(self, req, **_kwargs):
        pass

    # GET /devices/{switch_id}
    @rest_command
    def get_device(self, req, switch_id, **_kwargs):
        pass

    # GET /devices/{switch_id}/policy
    @rest_command
    def get_device_policy(self, req, switch_id, **_kwargs):
        pass

    # PUT /devices/{switch_id}/policy
    @rest_command
    def update_device_policy(self, req, switch_id, **_kwargs):
        pass

    # POST /devices/{switch_id}/policy
    @rest_command
    def create_device_policy(self, req, switch_id, **_kwargs):
        pass

    # DELETE /devices/{switch_id}/policy
    @rest_command
    def delete_device_policy(self, req, switch_id, **_kwargs):
        pass

    # GET /devices/{switch_id}/domains
    @rest_command
    def get_device_domains(self, req, switch_id, **_kwargs):
        pass

    # GET /domains
    @rest_command
    def get_domains(self, req, **_kwargs):
        pass

    # POST /domains
    @rest_command
    def create_domain(self, req, **_kwargs):
        pass

    # GET /domains/{domain_id}
    @rest_command
    def get_domain(self, req, domain_id, **_kwargs):
        pass

    # PUT /domains/{domain_id}
    @rest_command
    def update_domain(self, req, domain_id, **_kwargs):
        pass

    # DELETE /domains/{domain_id}
    @rest_command
    def delete_domain(self, req, domain_id, **_kwargs):
        pass

    # GET /domains/{domain_id}/rules
    @rest_command
    def get_domain_rules(self, req, domain_id, **_kwargs):
        pass

    # POST /domains/{domain_id}/rules
    @rest_command
    def create_domain_rule(self, req, domain_id, **_kwargs):
        pass

    # PUT /domains/{domain_id}/rules/{rule_id}
    @rest_command
    def update_domain_rule(self, req, domain_id, rule_id, **_kwargs):
        pass

    # DELETE /domains/{domain_id}/rules/{rule_id}
    @rest_command
    def delete_domain_rule(self, req, switch_id, rule_id, **_kwargs):
        pass
