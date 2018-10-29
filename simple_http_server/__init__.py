# -*- coding: utf-8 -*-
from simple_http_server.__logger__ import getLogger
try:
    unicode("")
except NameError:
    # python 3 has no unicode type
    unicode = str

name = "simple_http_server"


__request_mappings = []
__filters = []


__logger = None


def __log():
    global __logger
    if __logger is None:
        __logger = getLogger("simple_http_server")
    return __logger


def request_map(url, method=""):
    def map(ctrl_fun):
        if isinstance(method, list):
            mths = method
        else:
            mths = [method]
        for mth in mths:
            __log().info("map url %s with method[%s] to function %s. " % (url, mth, str(ctrl_fun)))
            __request_mappings.append({
                "url": url,
                "method": mth,
                "func": ctrl_fun
            })
        # return the original function, so you can use a decoration chain
        return ctrl_fun
    return map


def filter(pattern):
    def map(filter_fun):
        __filters.append({"url_pattern": pattern, "func": filter_fun})
        return filter_fun
    return map


def _get_request_mappings():
    return __request_mappings


def _get_filters():
    return __filters


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

    def __init__(self, name="", required=False, filename="", content_type="", content=None):
        self.__name = name
        self.__required = required
        self.__filename = filename
        self.__content_type = content_type
        self.__content = content

    @property
    def name(self):
        return self.__name

    @property
    def _required(self):
        return self.__required

    @property
    def filename(self):
        return self.__filename

    @property
    def content_type(self):
        return self.__content_type

    @property
    def content(self):
        return self.__content

    @property
    def is_empty(self):
        return self.__content is None or len(self.__content) == 0

    def save_to_file(self, file_path):
        if self.__content is not None and len(self.__content) > 0:
            with open(file_path, "wb") as f:
                f.write(self.__content)


class Response(object):
    """Response"""

    def __init__(self,
                 status_code=200,
                 headers=None,
                 body=""):
        self.status_code = status_code
        self.__headers = headers if headers is not None else {}
        self.__body = ""
        self.__set_body(body)

    @property
    def body(self):
        return self.__body

    @body.setter
    def body(self, val):
        self.__set_body(val)

    def __set_body(self, val):
        assert val is None or type(val) in (str, unicode, dict, StaticFile, bytes), "Body type is not supported."
        self.__body = val

    @property
    def headers(self):
        return self.__headers

    def set_header(self, key, value):
        self.__headers[key] = value

    def send_redirect(self, url):
        """abstruct method"""
        raise Exception("Abstruct method, you cannot call this method directly.")

    def send_response(self):
        """abstruct method"""
        raise Exception("Abstruct method, you cannot call this method directly.")


class StaticFile(object):

    def __init__(self, file_path, content_type="application/octet-stream"):
        self.file_path = file_path
        self.content_type = content_type


class HttpError(Exception):

    def __init__(self, code=400, message=""):
        super(HttpError, self).__init__("HTTP_ERROR[%d] %s" % (code, message))
        self.code = code
        self.message = message


class Parameter(unicode):

    def __init__(self, name="", default="", required=False):
        self.__name = name
        self.__required = required

    @property
    def name(self):
        return self.__name

    @property
    def _required(self):
        return self.__required

    def __new__(cls, name="", default="", **kwargs):
        assert isinstance(default, str) or isinstance(default, unicode)
        if str != unicode:
            """
            " Python 2.7, chuange str to unicode
            """
            default = default.decode("utf-8")
        obj = super(Parameter, cls).__new__(cls, default)
        return obj


class Parameters(list):

    def __init__(self, name="", default=[], required=False):
        self.__name = name
        self.__required = required

    @property
    def name(self):
        return self.__name

    @property
    def _required(self):
        return self.__required

    def __new__(cls, name="", default=[], **kwargs):
        obj = super(Parameters, cls).__new__(cls)
        obj.extend(default)
        return obj


class Header(Parameter):
    pass


class JSONBody(dict):
    pass
