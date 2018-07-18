#!/usr/bin/env python
# -*- coding: utf-8 -*-

from SimpleDispatcherHttpServer import SimpleDispatcherHttpServer
from controller.Demo import Filter, Index
from controller.RunCmdCtrl import run_cmd

filters = Filter()
index = Index()

server = SimpleDispatcherHttpServer(('', 10087))

# filter configuration
server.map_filter("/.*$", filters.filter1)
server.map_filter("/index$", filters.filter2)

# request mapping
server.map_request("/index", index.index)
server.map_request("/post", index.index, "post")
server.map_request("/run", run_cmd)

# start the server
server.start()
