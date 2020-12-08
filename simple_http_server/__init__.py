# -*- coding: utf-8 -*-
import http.cookies
from typing import Dict, List, Union, Callable
from simple_http_server.logger import get_logger

name = "simple_http_server"

__request_mappings = []
__filters = []


__logger = None


def _log():
    global __logger
    if __logger is None:
        __logger = get_logger("simple_http_server.__init__")
    return __logger


def request_map(url: str = "", method: Union[str, list] = "") -> Callable:
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


def filter_map(pattern: str = "") -> Callable:
    def map(filter_fun):
        __filters.append({"url_pattern": pattern, "func": filter_fun})
        return filter_fun
    return map


def _get_request_mappings():
    return __request_mappings


def _get_filters():
    return __filters


class Cookies(http.cookies.SimpleCookie):
    EXPIRE_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"


class Request:
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
    def cookies(self) -> Cookies:
        return self.__cookies

    @property
    def parameters(self) -> Dict[str, List[str]]:
        return self.__parameters

    @parameters.setter
    def parameters(self, val: Dict[str, List[str]]):
        self.__parameters = val
        self.__parameter = {}
        for k, v in self.__parameters.items():
            self.__parameter[k] = v[0]

    @property
    def parameter(self) -> Dict[str, str]:
        return self.__parameter

    def get_parameter(self, key: str, default: str = None) -> str:
        if key not in self.parameters.keys():
            return default
        else:
            return self.parameter[key]


class MultipartFile:
    """Multipart file"""

    def __init__(self, name: str = "",
                 required: bool = False,
                 filename: str = "",
                 content_type: str = "",
                 content: bytes = None):
        self.__name = name
        self.__required = required
        self.__filename = filename
        self.__content_type = content_type
        self.__content = content

    @property
    def name(self) -> str:
        return self.__name

    @property
    def _required(self) -> bool:
        return self.__required

    @property
    def filename(self) -> str:
        return self.__filename

    @property
    def content_type(self) -> str:
        return self.__content_type

    @property
    def content(self) -> bytes:
        return self.__content

    @property
    def is_empty(self) -> bool:
        return self.__content is None or len(self.__content) == 0

    def save_to_file(self, file_path: str) -> None:
        if self.__content is not None and len(self.__content) > 0:
            with open(file_path, "wb") as f:
                f.write(self.__content)


class ParamStringValue(str):

    def __init__(self, name: str = "",
                 default: str = "",
                 required: bool = False):
        self.__name = name
        self.__required = required

    @property
    def name(self) -> str:
        return self.__name

    @property
    def _required(self) -> bool:
        return self.__required

    def __new__(cls, name="", default="", **kwargs):
        assert isinstance(default, str)
        obj = super().__new__(cls, default)
        return obj


class Parameter(ParamStringValue):
    pass


class PathValue(str):

    def __init__(self, name: str = "", _value: str = ""):
        self.__name = name

    @property
    def name(self):
        return self.__name

    def __new__(cls, name: str = "", _value: str = "", **kwargs):
        assert isinstance(_value, str)
        obj = super().__new__(cls, _value)
        return obj


class Parameters(list):

    def __init__(self, name: str = "", default: List[str] = [], required: bool = False):
        self.__name = name
        self.__required = required

    @property
    def name(self) -> str:
        return self.__name

    @property
    def _required(self) -> bool:
        return self.__required

    def __new__(cls, name: str = "", default: List[str] = [], **kwargs):
        obj = super().__new__(cls)
        obj.extend(default)
        return obj


class Header(ParamStringValue):
    pass


class JSONBody(dict):
    pass


"""
" The folowing beans are used in Response
"""


class StaticFile:

    def __init__(self, file_path, content_type="application/octet-stream"):
        self.file_path = file_path
        self.content_type = content_type


class Response:
    """Response"""

    def __init__(self,
                 status_code: int = 200,
                 headers: Dict[str, str] = None,
                 body: Union[str, dict, StaticFile, bytes] = ""):
        self.status_code = status_code
        self.__headers = headers if headers is not None else {}
        self.__body = ""
        self.__cookies = Cookies()
        self.__set_body(body)

    @property
    def cookies(self) -> http.cookies.SimpleCookie:
        return self.__cookies

    @cookies.setter
    def cookies(self, val: http.cookies.SimpleCookie) -> None:
        assert isinstance(val, http.cookies.SimpleCookie)
        self.__cookies = val

    @property
    def body(self):
        return self.__body

    @body.setter
    def body(self, val: Union[str, dict, StaticFile, bytes]) -> None:
        self.__set_body(val)

    def __set_body(self, val):
        assert val is None or type(val) in (str, dict, StaticFile, bytes), "Body type is not supported."
        self.__body = val

    @property
    def headers(self) -> Dict[str, Union[list, str]]:
        return self.__headers

    def set_header(self, key: str, value: str) -> None:
        self.__headers[key] = value

    def add_header(self, key: str, value: Union[str, list]) -> None:
        if key not in self.__headers.keys():
            self.__headers[key] = value
            return
        if not isinstance(self.__headers[key], list):
            self.__headers[key] = [self.__headers[key]]
        if isinstance(value, list):
            self.__headers[key].extend(value)
        else:
            self.__headers[key].append(value)

    def add_headers(self, headers: Dict[str, Union[str, List[str]]] = {}) -> None:
        if headers is not None:
            for k, v in headers.items():
                self.add_header(k, v)

    def send_error(self, status_code: int, message: str = ""):
        """abstruct method"""
        raise Exception("Abstruct method, you cannot call this method directly.")

    def send_redirect(self, url: str):
        """abstruct method"""
        raise Exception("Abstruct method, you cannot call this method directly.")

    def send_response(self):
        """abstruct method"""
        raise Exception("Abstruct method, you cannot call this method directly.")


class HttpError(Exception):

    def __init__(self, code: int = 400, message: str = ""):
        super().__init__("HTTP_ERROR[%d] %s" % (code, message))
        self.code: int = code
        self.message: str = message


class Redirect:

    def __init__(self, url: str):
        self.__url = url

    @property
    def url(self) -> str:
        return self.__url


"""
" Use both in request and response
"""


class Headers(dict):

    def __init__(self, headers: Dict[str, Union[str, List[str]]] = {}):
        self.update(headers)


class Cookie(http.cookies.Morsel):

    def __init__(self,
                 name: str = "",
                 default: str = "",
                 default_options: Dict[str, str] = {},
                 required: bool = False):
        super().__init__()
        self.__name = name
        self.__required = required
        if name is not None and name != "":
            self.set(name, default, default)
        self.update(default_options)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def _required(self) -> bool:
        return self.__required
