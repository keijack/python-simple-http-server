#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller.Index import Index
from controller.RunCmdCtrl import run_cmd

from server.DispatcherHttpServer import RequestMapping, FilterMapping, DispatcherHttpServer

index = Index()
FilterMapping.filter("/.*$", index.filter)
FilterMapping.filter("/index$", index.f2)

# Map request to controllers
RequestMapping.map("/index", index.index)
RequestMapping.map("/post", index.index, "post")
RequestMapping.map("/run", run_cmd)

# start the server
server = DispatcherHttpServer(('', 10087))
server.start()
