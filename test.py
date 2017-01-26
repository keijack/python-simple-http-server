#!/usr/bin/env python
# -*- coding: utf-8 -*-


import re


def match(pattren, str):
    p = re.compile(pattren)
    m = p.match(str)

    if m:
        print(m.group())
    else:
        print("not found!")


match("/\d*", "aaa/a1")
