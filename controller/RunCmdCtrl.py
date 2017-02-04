#!/usr/bin/env python
# -*- coding: utf-8 -*-

import commands
import json


def run_cmd(req, res):
    jsonstr = req.parameter("json")
    print(jsonstr)
    obj = json.loads(jsonstr)
    cmd = obj["cmd"]
    s, txt = commands.getstatusoutput(cmd)
    result = {"status": s, "result": txt}
    res.body = json.dumps(result, ensure_ascii=False)
