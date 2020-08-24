# -*- coding: utf-8 -*-
from simple_http_server.logger import get_logger
try:
    unicode("")
except NameError:
    # python 3 has no unicode type
    unicode = str
try:
    import http.cookies as cookies
except ImportError:
    import Cookie as cookies

name = "simple_http_server"


__request_mappings = []
__filters = []


__logger = None


def _log():
    global __logger
    if __logger is None:
        __logger = get_logger("simple_http_server.__init__")
    return __logger


def request_map(url, method=""):
    def map(ctrl_fun):
        if isinstance(method, list):
            mths = method
        else:
            mths = [method]
        for mth in mths:
            _log().debug("map url %s with method[%s] to function %s. " % (url, mth, str(ctrl_fun)))
            __request_mappings.append({
                "url": url,
                "method": mth,
                "func": ctrl_fun
            })
        # return the original function, so you can use a decoration chain
        return ctrl_fun
    return map


def filter_map(pattern):
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
        self.__cookies = Cookies()
        self.query_string = ""  # Query String
        self.path_values = {}
        self.path = ""  # Path
        self.__parameters = {}  # Parameters, key-value array, merged by query string and request body if the `Content-Type` in request header is `application/x-www-form-urlencoded` or `multipart/form-data`
        self.__parameter = {}  # Parameters, key-value, if more than one parameters with the same key, only the first one will be stored.
        self.body = ""  # Request body
        self.json = None  # A dictionary if the `Content-Type` in request header is `application/json`

    @property
    def cookies(self):
        return self.__cookies

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




class ParamStringValue(unicode):

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
        obj = super(ParamStringValue, cls).__new__(cls, default)
        return obj

class Parameter(ParamStringValue):
    pass

class PathValue(unicode):

    def __init__(self, name="", _value=""):
        self.__name = name

    @property
    def name(self):
        return self.__name

    def __new__(cls, name="", _value="", **kwargs):
        assert isinstance(_value, str) or isinstance(_value, unicode)
        if str != unicode:
            """
            " Python 2.7, chuange str to unicode
            """
            _value = _value.decode("utf-8")
        obj = super(PathValue, cls).__new__(cls, _value)
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


class Header(ParamStringValue):
    pass


class JSONBody(dict):
    pass


"""
" The folowing beans are used in Response
"""


class Response(object):
    """Response"""

    def __init__(self,
                 status_code=200,
                 headers=None,
                 body=""):
        self.status_code = status_code
        self.__headers = headers if headers is not None else {}
        self.__body = ""
        self.__cookies = Cookies()
        self.__set_body(body)

    @property
    def cookies(self):
        return self.__cookies

    @cookies.setter
    def cookies(self, val):
        assert isinstance(val, cookies.SimpleCookie)
        self.__cookies = val

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

    def add_header(self, key, value):
        if key not in self.__headers.keys():
            self.__headers[key] = value
            return
        if not isinstance(self.__headers[key], list):
            self.__headers[key] = [self.__headers[key]]
        if isinstance(value, list):
            self.__headers[key].extend(value)
        else:
            self.__headers[key].append(value)

    def add_headers(self, headers={}):
        if headers is not None:
            for k, v in headers.items():
                self.add_header(k, v)

    def send_error(self, status_code, message=""):
        """abstruct method"""
        raise Exception("Abstruct method, you cannot call this method directly.")

    def send_redirect(self, url):
        """abstruct method"""
        raise Exception("Abstruct method, you cannot call this method directly.")

    def send_response(self):
        """abstruct method"""
        raise Exception("Abstruct method, you cannot call this method directly.")


class HttpError(Exception):

    def __init__(self, code=400, message=""):
        super(HttpError, self).__init__("HTTP_ERROR[%d] %s" % (code, message))
        self.code = code
        self.message = message


class StaticFile(object):

    def __init__(self, file_path, content_type="application/octet-stream"):
        self.file_path = file_path
        self.content_type = content_type

class Redirect(object):

    def __init__(self, url):
        self.__url = url

    @property
    def url(self):
        return self.__url


"""
" Use both in request and response
"""


class Headers(dict):

    def __init__(self, headers={}):
        self.update(headers)


class Cookies(cookies.SimpleCookie):
    EXPIRE_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"


class Cookie(cookies.Morsel):

    def __init__(self, name="",
                 default="",
                 default_options={},
                 required=False):
        super(Cookie, self).__init__()
        self.__name = name
        self.__required = required
        if name is not None and name != "":
            self.set(name, default, default)
        self.update(default_options)

    @property
    def name(self):
        return self.__name

    @property
    def _required(self):
        return self.__required
