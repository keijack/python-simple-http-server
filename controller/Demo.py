#!/usr/bin/evn python
# -*- coding: utf-8 -*-


import json

from SimpleDispatcherHttpServer import MultipartFile


class Filter:
    """Filter Demod"""

    def __init__(self):
        pass

    def filter1(self, ctx):
        if ctx.request.parameter("to403") == "true":
            ctx.response.statusCode = 403
            ctx.send_response()
            return
        ctx.request.parameters["filter-add"] = ["0001"]
        ctx.go_on()

    def filter2(self, ctx):
        ctx.request.parameters["filter2"] = ["xxxxx"]
        ctx.go_on()


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
