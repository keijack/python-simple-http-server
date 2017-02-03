#!/usr/bin/env python
# -*- coding: utf-8 -*-


import BaseHTTPServer
import re
from SocketServer import ThreadingMixIn
from urllib import unquote

from Logger import Logger


class FilterMapping:
    """Filter Mapping"""

    __SORTED_KEYS = []
    __FILTER = {}

    def __init__(self):
        pass

    @staticmethod
    def filter(key, ft):
        FilterMapping.__SORTED_KEYS.append(key)
        FilterMapping.__FILTER[key] = ft

    @staticmethod
    def _get_matched_filters(path):
        available_filters = []
        for key in FilterMapping.__SORTED_KEYS:
            if re.match(key, path):
                available_filters.append(FilterMapping.__FILTER[key])
        return available_filters


class RequestMapping:
    """Request Mapping"""

    COMMON = {}
    SPECIFIC = {}

    def __init__(self):
        pass

    @staticmethod
    def map(url, fun, method=""):
        if method is None or method == "":
            RequestMapping.COMMON[url] = fun
        else:
            mth = method.upper()
            if mth not in RequestMapping.SPECIFIC.keys():
                RequestMapping.SPECIFIC[mth] = {}
            RequestMapping.SPECIFIC[mth][url] = fun


class Request:
    """Request"""

    def __init__(self):
        self.method = ""
        self.headers = {}
        self.queryString = ""
        self.path = ""
        self.parameters = {}

    def parameter(self, key, default=None):
        if key not in self.parameters.keys():
            return default
        else:
            return self.parameters[key][0]


class Response:
    """Response"""

    def __init__(self):
        self.is_sent = False
        self.statusCode = 200
        self.contentType = "application/json; charset=utf8"
        self.headers = {}
        self.body = ""


class FilterContex:
    """Context of a filter"""

    def __init__(self, handler, req, res, controller):
        self.request = req
        self.response = res
        self.__req_handler = handler
        self.__controller = controller
        self.__filters = []

    def _add_filter(self, filter):
        self.__filters.append(filter)

    def send_response(self):
        self.__req_handler._send_response(self.response)

    def go_on(self):
        if self.response.is_sent:
            return
        if len(self.__filters) == 0:
            self.__controller(self.request, self.response)
        else:
            fun = self.__filters[0]
            self.__filters = self.__filters[1:]
            fun(self)


class DispatcherHttpRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """The Class will dispatch the request to the controller configured in RequestMapping"""

    def __process(self, method):
        mth = method.upper()

        req = self.__prepare_request(mth)
        path = req.path

        if mth == "HEAD":
            # seek controller from GET configuration
            mth = "GET"
        if mth in RequestMapping.SPECIFIC.keys() and path in RequestMapping.SPECIFIC[mth].keys():
            ctrl = RequestMapping.SPECIFIC[mth][path]
        elif path in RequestMapping.COMMON.keys():
            ctrl = RequestMapping.COMMON[path]
        else:
            ctrl = None

        res = Response()
        if ctrl is None:
            res.statusCode = 404
            res.body = '{"error":"Cannot find controller for your path"}'
        else:
            ctx = FilterContex(self, req, res, ctrl)
            filters = FilterMapping._get_matched_filters(path)
            for f in filters:
                ctx._add_filter(f)
            ctx.go_on()
        return req, res

    def __prepare_request(self, method):
        path = self.__get_path(self.path)
        Logger.debug(path + " [" + method + "] is bing visited")
        req = Request()
        req.path = path
        req.headers = self.headers
        Logger.debug("Headers: " + str(req.headers))
        req.method = method
        query_string = self.__get_query_string(self.path)
        Logger.debug("query string: " + query_string)
        req.parameters = self.__decode_query_string(query_string)
        if "content-length" in self.headers.keys():
            data = self.rfile.read(int(self.headers["content-length"]))
            self.rfile.close()
            data_params = self.__decode_query_string(data)
            req.parameters = self.__merge(data_params, req.parameters)
        return req

    def __decode_query_string(self, query_string):
        params = {}
        pairs = query_string.split("&")
        Logger.debug("pairs: " + str(pairs))
        for item in pairs:
            apair = item.split("=")
            if len(apair) == 0:
                continue
            key = apair[0]
            val = ""
            if len(apair) >= 2:
                val = self.__join(apair[1:], "=")
            val = unquote(val)

            if key not in params.keys():
                params[key] = [val]
            else:
                params[key].append(val)

        return params

    def __join(self, list, mid=""):
        joins = ""
        for item in list:
            if joins != "":
                joins += mid
            joins += str(item)
        return joins

    def _send_response(self, (request, response)):
        if response.is_sent:
            return
        response.is_sent = True
        self.send_response(response.statusCode)

        self.send_header("Content-Type", response.contentType)
        self.send_header("Last-Modified", str(self.date_time_string()))
        for (k, v) in response.headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", len(response.body))

        self.end_headers()
        Logger.debug("body::" + response.body)

        if request.method != "HEAD":
            self.wfile.write(response.body)
            self.wfile.close()

    def do_GET(self):
        self._send_response(self.__process("GET"))

    def do_HEAD(self):
        self._send_response(self.__process("HEAD"))

    def do_POST(self):
        self._send_response(self.__process("POST"))

    def do_PUT(self):
        self._send_response(self.__process("PUT"))

    def do_DELETE(self):
        self._send_response(self.__process("DELETE"))

    def __merge(self, dic0, dic1):
        """Merge tow dictionaries of which the structure is {k:[v1, v2]}"""
        dic = dic1
        for k, v in dic0.items():
            if k not in dic.keys():
                dic[k] = v
            else:
                for i in v:
                    dic[k].append(i)
        return dic

    def __get_query_string(self, oriPath):
        parts = oriPath.split('?')
        if len(parts) == 2:
            return parts[1]
        else:
            return ""

    def __get_path(self, oriPath):
        path = oriPath.split('?', 1)[0]
        path = path.split('#', 1)[0]
        return path


class DispatcherHttpServer:
    """Dispatcher Http server"""

    class __ThreadingServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
        pass

    def __init__(self, host=('', 8888), multithread=True):
        self.host = host
        self.multithread = multithread

    def start(self):
        if self.multithread:
            server = self.__ThreadingServer(self.host, DispatcherHttpRequestHandler)
        else:
            server = BaseHTTPServer.HTTPServer(self.host, DispatcherHttpRequestHandler)
        server.serve_forever()
