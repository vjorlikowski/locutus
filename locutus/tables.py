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
from locutus.util import *


class PortData(dict):
    def __init__(self, ports):
        super(PortData, self).__init__()
        for port in ports:
            self[port.port_no] = port

    def update(self, port):
        self[port.port_no] = port

    def delete(self, port):
        del self[port.port_no]
