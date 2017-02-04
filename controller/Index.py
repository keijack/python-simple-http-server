#!/usr/bin/evn python
# -*- coding: utf-8 -*-


import json


class Index:
    """Controller for /index"""

    def __init__(self):
        pass

    def index(self, req, res):
        print(req.parameters)
        params = {}
        for k, v in req.parameters.items():
            if len(v) == 1:
                params[k] = v[0]
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
