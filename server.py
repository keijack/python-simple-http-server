#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller.Index import Index

from server.DispatcherHttpServer import RequestMapping, FilterMapping, DispatcherHttpServer

index = Index()
FilterMapping.filter("/.*$", index.filter)
FilterMapping.filter("/index$", index.f2)

# Map request to controllers
RequestMapping.map("/index", index.index)
RequestMapping.map("/post", index.index, "post")

# start the server
server = DispatcherHttpServer(('', 10087))
server.start()
