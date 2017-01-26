#!/usr/bin/env python
# -*- coding: utf-8 -*-

from controller.Index import Index

from server.DispatcherHttpServer import RequestMapping, DispatcherHttpServer, FilterMapping

index = Index()
FilterMapping.filter("/.*$", index.filter)

# Map request to controllers
RequestMapping.map("/index", index.index)
RequestMapping.map("/post", index.index, "post")

# start the server
server = DispatcherHttpServer(('', 10087))
server.start()
