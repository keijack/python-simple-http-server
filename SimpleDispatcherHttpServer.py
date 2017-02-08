#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import BaseHTTPServer
import re
from SocketServer import ThreadingMixIn
from urllib import unquote

import logging

logger = logging.getLogger("SimpleDispatcherHttpServer")
logger.setLevel("INFO")
logger.addHandler(logging.StreamHandler(sys.stdout))


class Request:
    """Request"""

    def __init__(self):
        self.method = ""
        self.headers = {}
        self.query_string = ""
        self.path = ""
        self.parameters = {}

    def parameter(self, key, default=None):
        if key not in self.parameters.keys():
            return default
        else:
            return self.parameters[key][0]


class MultipartFile:
    """Multipart file"""

    def __init__(self):
        self.filename = ""
        self.content_type = ""
        self.content = ""


class Response:
    """Response"""

    def __init__(self):
        self.is_sent = False
        self.status_code = 200
        self.content_type = "application/json; charset=utf8"
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


class SimpleDispatcherHttpRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
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
            res.status_code = 404
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
        logger.debug(path + " [" + method + "] is bing visited")
        req = Request()
        req.path = path
        req.headers = self.headers
        logger.debug("Headers: " + str(req.headers))
        req.method = method
        query_string = self.__get_query_string(self.path)
        logger.debug("query string: " + query_string)
        req.parameters = self.__decode_query_string(query_string)

        if "content-length" in self.headers.keys():
            data = self.rfile.read(int(self.headers["content-length"]))
            self.rfile.close()
            content_type = self.headers["content-type"]
            if content_type.lower().startswith("multipart/form-data"):
                data_params = self.__decode_multipart(content_type, data)
            else:
                data_params = self.__decode_query_string(data)
            req.parameters = self.__merge(data_params, req.parameters)
        return req

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

    def __decode_multipart(self, content_type, data):
        boundary = "--" + content_type.split("; ")[1].split("=")[1]
        fields = data.split(boundary)
        fields = fields[1: len(fields) - 1]  # ignore the first empty row and the last end symbol
        params = {}
        for field in fields:
            key, val = self.__decode_multipart_field(field.strip())
            self.__put_to(params, key, val)
        return params

    def __decode_multipart_field(self, field):
        # first line: Content-Disposition
        line, rest = self.__read_line(field)
        logger.debug("line::" + line)
        kvs = self.__decode_content_disposition(line)
        if len(kvs) == 1:
            # this is a string field, the second line is an empty line, the rest is the value
            empty_line, val = self.__read_line(rest)
        elif len(kvs) == 2:
            # this is a file field
            val = MultipartFile()
            val.filename = kvs["filename"]
            # the second line is Content-Type line
            ct_line, rest = self.__read_line(rest)
            val.content_type = ct_line.split(":")[1].strip()
            # the third line is an empty line, the rest is the value
            empty_line, val.content = self.__read_line(rest)
        else:
            val = "UNKNOWN"

        return kvs["name"], val

    def __decode_content_disposition(self, line):
        cont_dis = {}
        es = line.split(";")[1:]
        for e in es:
            e = e.strip()
            kv = e.split("=")
            k = kv[0]
            v = kv[1]
            v = v[1: len(v) - 1]  # ignore the '"' symbol
            cont_dis[k] = v
        return cont_dis

    def __read_line(self, txt, line_breaker="\r\n"):
        try:
            idx = txt.index(line_breaker)
            return txt[0: idx], txt[idx + 2:]
        except ValueError:
            return txt, None

    def __decode_query_string(self, query_string):
        params = {}
        pairs = query_string.split("&")
        logger.debug("pairs: " + str(pairs))
        for item in pairs:
            apair = item.split("=")
            if len(apair) == 0:
                continue
            key = apair[0]
            val = ""
            if len(apair) >= 2:
                # join back, there may be some parameters like a=b=c
                val = self.__join(apair[1:], "=")
            val = unquote(val)

            self.__put_to(params, key, val)

        return params

    def __put_to(self, params, key, val):
        if key not in params.keys():
            params[key] = [val]
        else:
            params[key].append(val)

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
        self.send_response(response.status_code)

        self.send_header("Content-Type", response.content_type)
        self.send_header("Last-Modified", str(self.date_time_string()))
        for (k, v) in response.headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", len(response.body))

        self.end_headers()
        logger.debug("body::" + response.body)

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


class SimpleDispatcherHttpServer:
    """Dispatcher Http server"""

    class __ThreadingServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
        pass

    def map_filter(self, pattern, filter_fun):
        FilterMapping.filter(pattern, filter_fun)

    def map_request(self, url, fun, method=""):
        RequestMapping.map(url, fun, method)

    def __init__(self, host=('', 8888), multithread=True):
        self.host = host
        self.multithread = multithread

    def start(self):
        if self.multithread:
            server = self.__ThreadingServer(self.host, SimpleDispatcherHttpRequestHandler)
        else:
            server = BaseHTTPServer.HTTPServer(self.host, SimpleDispatcherHttpRequestHandler)
        logger.info("Dispatcher Http Server starts. Listen to port [" + str(self.host[1]) + "]")
        server.serve_forever()
