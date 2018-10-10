# -*- coding: utf-8 -*-

import sys
import re
import json
import copy
import inspect
from collections import OrderedDict
from threading import Thread
try:
    import http.server as BaseHTTPServer
except ImportError:
    import BaseHTTPServer
try:
    from socketserver import ThreadingMixIn
except ImportError:
    from SocketServer import ThreadingMixIn
try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote

from simple_http_server.__logger__ import getLogger


_logger = getLogger("SimpleHttpServer")


class Request(object):
    """Request"""

    def __init__(self):
        self.method = ""  # GET, POST, PUT, DELETE, HEAD, etc.
        self.headers = {}  # Request headers
        self.query_string = ""  # Query String
        self.path = ""  # Path
        self.__parameters = {}  # Parameters, key-value array, merged by query string and request body if the `Content-Type` in request header is `application/x-www-form-urlencoded` or `multipart/form-data`
        self.__parameter = {}  # Parameters, key-value, if more than one parameters with the same key, only the first one will be stored.
        self.body = ""  # Request body
        self.json = None  # A dictionary if the `Content-Type` in request header is `application/json`

    @property
    def parameters(self):
        return self.__parameters

    @parameters.setter
    def parameters(self, val):
        self.__parameters = val
        self.__parameter = {}
        for k, v in self.__parameters.items():
            self.__parameter[k] = v[0]

    @property
    def parameter(self):
        return self.__parameter

    def get_parameter(self, key, default=None):
        if key not in self.parameters.keys():
            return default
        else:
            return self.parameter[key]


class MultipartFile(object):
    """Multipart file"""

    def __init__(self):
        self.filename = ""
        self.content_type = ""
        self.__content = None

    @property
    def content(self):
        return self.__content

    @content.setter
    def content(self, value):
        assert self.__content is None, "This field `content` cannot be set"
        self.__content = value

    def save_to_file(self, file_path):
        with open(file_path, "wb") as f:
            f.write(self.__content)


class Response(object):
    """Response"""

    def __init__(self,
                 status_code=200,
                 content_type="application/json; charset=utf8",
                 headers=None,
                 body=""):
        self.status_code = status_code
        self.content_type = content_type
        self.__headers = headers if headers is not None else {}
        self.body = ""

    @property
    def headers(self):
        return self.__headers

    def set_header(self, key, value):
        self.__headers[key] = value


class ResponseWrapper(object):
    """ """

    def __init__(self, handler,
                 status_code=200,
                 headers=None):
        self.status_code = status_code
        self.__headers = headers if headers is not None else {}
        self.__headers["Content-Type"] = "text/plain"
        self.__body = ""
        self.__req_handler = handler
        self.__is_sent = False

    @property
    def headers(self):
        return self.__headers

    @property
    def body(self):
        return self.__body

    @body.setter
    def body(self, body):
        assert not self.__is_sent, "This response has benn sent"
        # _logger.debug("body set:: %s" % body)
        self.__body = body

    @property
    def is_sent(self):
        return self.__is_sent

    def set_header(self, key, value):
        self.__headers[key] = value

    def send_redirect(self, url):
        self.status_code = 302
        self.set_header("Location", url)
        self.__body = ""
        self.send_response()

    def send_response(self):
        assert not self.__is_sent, "This response has benn sent"
        self.__is_sent = True
        _logger.debug("send response...")
        self.__req_handler._send_response({
            "status_code": self.status_code,
            "headers": self.__headers,
            "body": self.__body
        })


class FilterContex:
    """Context of a filter"""

    def __init__(self, req, res, controller, filters=None):
        self.request = req
        self.response = res
        self.__controller = controller
        self.__filters = filters if filters is not None else []

    def do_chain(self):
        if self.response.is_sent:
            return
        if len(self.__filters) == 0:
            defaults = _get_function_defaults(self.__controller)
            default_headers = defaults["headers"] if "headers" in defaults else None
            default_param = defaults["parameter"] if "parameter" in defaults else None
            default_params = defaults["parameters"] if "parameters" in defaults else None
            default_json = defaults["json"] if "json" in defaults else None
            default_data = defaults["data"] if "data" in defaults else None
            headers = self.__merge_default(self.request.headers, default_headers)
            # headers = self.request.headers
            param = self.__merge_default(self.request.parameter, default_param)
            params = self.__merge_default_to_list(self.request.parameters, default_params)
            json = self.__merge_default(self.request.json, default_json)
            json = self.__merge_default(json, default_data)
            ctr_res = self.__controller(request=self.request,
                                        response=self.response,
                                        headers=headers,
                                        parameter=param,
                                        parameters=params,
                                        body=self.request.body,
                                        json=json,
                                        data=json)
            if isinstance(ctr_res, dict):
                self.response.set_header("Content-Type", "application/json; charset=utf8")
                self.response.body = json.dumps(ctr_res, ensure_ascii=False)
            elif isinstance(ctr_res, Response):
                self.response.status_code = ctr_res.status_code
                self.response.body = ctr_res.body
                for k, v in ctr_res.headers.items():
                    self.response.set_header(k, v)
                if ctr_res.content_type is not None and ctr_res.content_type != "":
                    self.response.set_header("Content-Type", ctr_res.content_type)
            elif isinstance(ctr_res, str) or type(ctr_res).__name__ == "unicode":
                ctr_res = ctr_res.strip()
                self.response.body = ctr_res
                if ctr_res.startswith("<?xml") and ctr_res.endswith(">"):
                    self.response.set_header("Content-Type", "text/xml; charset=utf8")
                elif ctr_res.startswith("<!DOCTYPE html") and ctr_res.endswith(">"):
                    self.response.set_header("Content-Type", "text/html; charset=utf8")
                else:
                    self.response.set_header("Content-Type", "text/plain; charset=utf8")
            else:
                assert False, "Cannot reconize response type %s " % str(type(ctr_res))
            if self.request.method.upper() == "HEAD":
                self.response.body = ""
            if not self.response.is_sent:
                self.response.send_response()
        else:
            fun = self.__filters[0]
            self.__filters = self.__filters[1:]
            fun(self)

    def __merge_default(self, ori_dict, default_dict):
        ori_dict_c = copy.deepcopy(ori_dict) if ori_dict is not None else {}
        if default_dict is None:
            return ori_dict_c
        for k, v in default_dict.items():
            if k not in ori_dict_c:
                ori_dict_c[k] = v
        return ori_dict_c

    def __merge_default_to_list(self, ori_dict, default_dict):
        ori_dict_c = copy.deepcopy(ori_dict) if ori_dict is not None else {}
        if default_dict is None:
            return ori_dict_c
        for k, v in default_dict.items():
            if k not in ori_dict_c:
                if isinstance(v, list):
                    ori_dict_c[k] = v
                else:
                    ori_dict_c[k] = [v]
        return ori_dict_c


def _get_function_defaults(func):
    args = inspect.getargspec(func)
    if args is None or args.defaults is None:
        return {}
    else:
        return OrderedDict(zip(args.args[-len(args.defaults):], args.defaults))


class FilterMapping:
    """Filter Mapping"""

    __SORTED_KEYS = []
    __FILTER = {}

    def __init__(self):
        pass

    @staticmethod
    def map(key, ft):
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

        if mth in RequestMapping.SPECIFIC.keys() and path in RequestMapping.SPECIFIC[mth].keys():
            ctrl = RequestMapping.SPECIFIC[mth][path]
        elif path in RequestMapping.COMMON.keys():
            ctrl = RequestMapping.COMMON[path]
        else:
            ctrl = None

        res = ResponseWrapper(self)
        if ctrl is None:
            res.status_code = 404
            res.body = '{"error":"Cannot find controller for your path"}'
            res.send_response()
        else:
            filters = FilterMapping._get_matched_filters(path)
            ctx = FilterContex(req, res, ctrl, filters)
            try:
                ctx.do_chain()
            except Exception as e:
                _logger.exception("error occurs! returning 500")
                res.status_code = 500
                res.body = '{"error": "' + str(e) + '"}'
                res.send_response()

    def __prepare_request(self, method):
        path = self.__get_path(self.path)
        _logger.debug(path + " [" + method + "] is bing visited")
        req = Request()
        req.path = path
        headers = {}
        _headers_in_lowers = {}
        for k in self.headers.keys():
            headers[k] = self.headers[k]
            _headers_in_lowers[k.lower()] = self.headers[k]
        req.headers = headers

        _logger.debug("Headers: " + str(req.headers))
        req.method = method
        query_string = self.__get_query_string(self.path)
        _logger.debug("query string: " + query_string)
        req.parameters = self.__decode_query_string(query_string)

        if "content-length" in _headers_in_lowers.keys():
            data = self.rfile.read(int(_headers_in_lowers["content-length"])).decode("ISO-8859-1")
            self.rfile.close()
            req.body = data
            content_type = _headers_in_lowers["content-type"]
            if content_type.lower().startswith("application/x-www-form-urlencoded"):
                data_params = self.__decode_query_string(data)
            elif content_type.lower().startswith("multipart/form-data"):
                data_params = self.__decode_multipart(content_type, data)
            elif content_type.lower().startswith("application/json"):
                req.json = json.loads(data)
            else:
                data_params = {}
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
        _logger.debug("decode multipart...")
        boundary = "--" + content_type.split("; ")[1].split("=")[1]
        _logger.debug("data's type is %s " % type(data))
        fields = data.split(boundary)
        # ignore the first empty row and the last end symbol
        fields = fields[1: len(fields) - 1]
        params = {}
        for field in fields:
            # trim the first and the last empty row
            f = field[field.index("\r\n") + 2: field.rindex("\r\n")]
            key, val = self.__decode_multipart_field(f)
            self.__put_to(params, key, val)
        return params

    def __decode_multipart_field(self, field):
        # first line: Content-Disposition
        line, rest = self.__read_line(field)
        # _logger.debug("line::" + line)
        kvs = self.__decode_content_disposition(line)
        if len(kvs) == 1:
            # this is a string field, the second line is an empty line, the rest is the value
            val = self.__read_line(rest)[1].encode("ISO-8859-1").decode("UTF-8")
            _logger.debug("value is ::" + val)
        elif len(kvs) == 2:
            # this is a file field
            val = MultipartFile()
            val.filename = kvs["filename"]
            # the second line is Content-Type line
            ct_line, rest = self.__read_line(rest)
            val.content_type = ct_line.split(":")[1].strip()
            # the third line is an empty line, the rest is the value
            val.content = self.__read_line(rest)[1].encode("ISO-8859-1")
        else:
            val = "UNKNOWN"

        return kvs["name"], val

    def __decode_content_disposition(self, line):
        cont_dis = {}
        es = line.split(";")[1:]
        for e in es:
            k, v = self.__break(e.strip(), "=")
            cont_dis[k] = v[1: len(v) - 1]  # ignore the '"' symbol
        return cont_dis

    def __read_line(self, txt):
        # _logger.debug("txt is -> " + str(txt))
        return self.__break(txt, "\r\n")

    def __break(self, txt, separator):
        try:
            idx = txt.index(separator)
            return txt[0: idx], txt[idx + len(separator):]
        except ValueError:
            return txt, None

    def __decode_query_string(self, query_string):
        params = {}
        if not query_string:
            return params
        pairs = query_string.split("&")
        # _logger.debug("pairs: " + str(pairs))
        for item in pairs:
            key, val = self.__break(item, "=")
            if val is None:
                val = ""
            self.__put_to(params, key, unquote(val))

        return params

    def __put_to(self, params, key, val):
        if key not in params.keys():
            params[key] = [val]
        else:
            params[key].append(val)

    def _send_response(self, response):
        self.send_response(response["status_code"])
        self.send_header("Last-Modified", str(self.date_time_string()))
        for k, v in response["headers"].items():
            self.send_header(k, v)
        body = response["body"]
        self.send_header("Content-Length", len(body))

        self.end_headers()
        # _logger.debug("body::" + body)

        if body is not None and body != "":
            self.wfile.write(body.encode("utf8"))

    def do_method(self, method):
        self.__process(method)

    def do_GET(self):
        self.do_method("GET")

    def do_HEAD(self):
        self.do_method("HEAD")

    def do_POST(self):
        self.do_method("POST")

    def do_PUT(self):
        self.do_method("PUT")

    def do_DELETE(self):
        self.do_method("DELETE")

    # @override
    def log_message(self, format, *args):
        _logger.info("%s - - [%s] %s\n" %
                     (self.client_address[0],
                      self.log_date_time_string(),
                      format % args))


class SimpleDispatcherHttpServer:
    """Dispatcher Http server"""

    class __ThreadingServer(ThreadingMixIn, BaseHTTPServer.HTTPServer):
        pass

    def map_filter(self, pattern, filter_fun):
        FilterMapping.map(pattern, filter_fun)

    def map_request(self, url, fun, method=""):
        RequestMapping.map(url, fun, method)

    def __init__(self, host=('', 8888), multithread=True):
        self.host = host
        self.multithread = multithread
        if self.multithread:
            self.server = self.__ThreadingServer(
                self.host, SimpleDispatcherHttpRequestHandler)
        else:
            self.server = BaseHTTPServer.HTTPServer(
                self.host, SimpleDispatcherHttpRequestHandler)

    def start(self):
        _logger.info("Dispatcher Http Server starts. Listen to port [" + str(self.host[1]) + "]")
        self.server.serve_forever()

    def shutdown(self):
        # server must shutdown in a separate thread, or it will be deadlocking...WTF!
        t = Thread(target=self.server.shutdown)
        t.daemon = True
        t.start()
