#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller.Index import Index
from controller.RunCmdCtrl import run_cmd

from server.SimpleDispatcherHttpServer import SimpleDispatcherHttpServer

index = Index()

server = SimpleDispatcherHttpServer(('', 10087))

# filter configuration
server.map_filter("/.*$", index.filter)
server.map_filter("/index$", index.f2)

# request mapping
server.map_request("/index", index.index)
server.map_request("/post", index.index, "post")
server.map_request("/run", run_cmd)

# start the server
server.start()
