#!/usr/bin/evn python
# -*- coding: utf-8 -*-


import json
from server.SimpleDispatcherHttpServer import MultipartFile


class Index:
    """Controller for /index"""

    def __init__(self):
        pass

    def index(self, req, res):
        print(req.parameters)
        params = {}
        for k, v in req.parameters.items():
            if len(v) == 1:
                val = v[0]
                if isinstance(val, MultipartFile):
                    params[k] = val.filename
                    print(k + "-> file content-type ->" + val.content_type)
                    print(k + "-> file content -> " + val.content)
                else:
                    params[k] = val
            else:
                params[k] = v
        res.body = json.dumps(params, ensure_ascii=False)

    def filter(self, ctx):
        if ctx.request.parameter("stop") == "true":
            ctx.response.statusCode = 403
            ctx.send_response()
            return
        ctx.request.parameters["filter-add"] = ["0001"]
        ctx.go_on()

    def f2(self, ctx):
        print("f2.......")
        ctx.request.parameters["f2"] = ["xxxxx"]
        ctx.go_on()
