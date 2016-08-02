## Introduction

Locutus is an OpenFlow controller application developed at Duke University.

It makes use of the Ryu OpenFlow controller framework
(http://osrg.github.io/ryu/), and is, in part, derived from the
"rest_router" example application that is included with Ryu.

Locutus is an application that acts as a "transcoding proxy."
It interposes between an OpenFlow switch and one (or more) other
controllers, and performs the actions of: forwarding PacketIn
requests to other controllers on the basis of user-specified rules,
receiving those controllers' responses (FlowMods, etc.), and possibly
modifying those responses before finally delivering the responses to
the appropriate switch.

Locutus is at a very early stage of development, and will
obviously have bugs and missing features.
Development is ongoing, and contributions are welcomed.

## Building and Deploying Locutus

Locutus runs on Unix-like systems, due to relying on supervisord to
manage the Ryu controller framework.

Installing Locutus can be done by installing the correct set of
dependency packages using pip, and then running "python setup.py".

For ease of deployment, however, an RPM build process has been
provided, and a Dockerfile is being worked on. If demand exists, a
Debian/Ubuntu packaging infrastructure will be added as well.

Distribution of binary RPMs is planned in the near future, as is a
detailed description of the RPM build process.

## REST API Documentation

The following REST API description is based on the description
originally included with the "rest_router" example application,
and has been added to as new functions were integrated into
Locutus.

This API is still in flux; please expect changes, as we solidify
the set of core functions and abstractions.

