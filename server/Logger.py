#!/usr/bin/env python
# -*- coding: utf-8 -*-


class Logger:
    """Logger"""

    def __init__(self):
        pass

    def debug(self, msg):
        # print("[DEBUG] " + str(msg))
        pass

    def info(self, msg):
        print("[INFO] " + str(msg))

    def warn(self, msg):
        print("[WARN] " + str(msg))

    def error(self, msg):
        print("[ERROR]" + str(msg))
