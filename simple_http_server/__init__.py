# -*- coding: utf-8 -*-

"""
Copyright (c) 2018 Keijack Wu

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from abc import abstractmethod
from collections import OrderedDict
import sys
import http.cookies
import inspect
import time
from typing import Any, Dict, List, Tuple, Type, Union, Callable
from .logger import get_logger

name = "simple_http_server"
version = "0.14.13"

DEFAULT_ENCODING: str = "UTF-8"

SESSION_COOKIE_NAME: str = "PY_SIM_HTTP_SER_SESSION_ID"

_logger = get_logger("simple_http_server.__init__")


class Session:

    def __init__(self):
        self.max_inactive_interval: int = 30 * 60

    @property
    def id(self) -> str:
        return ""

    @property
    def creation_time(self) -> float:
        return 0

    @property
    def last_accessed_time(self) -> float:
        return 0

    @property
    def attribute_names(self) -> Tuple:
        return ()

    @property
    def is_new(self) -> bool:
        return False

    @property
    def is_valid(self) -> bool:
        return time.time() - self.last_accessed_time < self.max_inactive_interval

    def get_attribute(self, name: str) -> Any:
        return None

    def set_attribute(self, name: str, value: str) -> None:
        pass

    def invalidate(self) -> None:
        pass


class SessionFactory:

    def get_session(self, session_id: str, create: bool = False) -> Session:
        return None


class Cookies(http.cookies.SimpleCookie):
    EXPIRE_DATE_FORMAT = "%a, %d %b %Y %H:%M:%S GMT"


class RequestBodyReader:

    async def read(self, n: int = -1) -> bytes:
        pass


class Request:
    """Request"""

    def __init__(self):
        self.method: str = ""  # GET, POST, PUT, DELETE, HEAD, etc.
        self.headers: Dict[str, str] = {}  # Request headers
        self.__cookies = Cookies()
        self.query_string: str = ""  # Query String
        self.path_values: Dict[str, str] = {}
        self.reg_groups = ()  # If controller is matched via regexp, then ,all groups are save here
        self.path: str = ""  # Path
        self.__parameters = {}  # Parameters, key-value array, merged by query string and request body if the `Content-Type` in request header is `application/x-www-form-urlencoded` or `multipart/form-data`
        self.__parameter = {}  # Parameters, key-value, if more than one parameters with the same key, only the first one will be stored.
        self._body: bytes = b""  # Request body
        self.json: Dict[str, Any] = None  # A dictionary if the `Content-Type` in request header is `application/json`
        self.environment = {}
        self.reader: RequestBodyReader = None  # A stream reader

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

    @property
    def host(self) -> str:
        if "Host" not in self.headers:
            return ""
        else:
            return self.headers["Host"]

    @property
    def content_type(self) -> str:
        if "Content-Type" not in self.headers:
            return ""
        else:
            return self.headers["Content-Type"]

    @property
    def content_length(self) -> int:
        if "Content-Length" not in self.headers:
            return None
        else:
            return int(self.headers["Content-Length"])

    def get_parameter(self, key: str, default: str = None) -> str:
        if key not in self.parameters.keys():
            return default
        else:
            return self.parameter[key]

    @abstractmethod
    def get_session(self, create: bool = False) -> Session:
        # This is abstract method
        return None


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


class ModelDict(dict):
    pass


class Environment(dict):
    pass


class RegGroups(tuple):
    pass


class RegGroup(str):

    def __init__(self, group=0, **kwargs):
        self._group = group

    @property
    def group(self) -> int:
        return self._group

    def __new__(cls, group=0, **kwargs):
        if "_value" not in kwargs:
            val = ""
        else:
            val = kwargs["_value"]
        obj = super().__new__(cls, val)
        return obj


class Header(ParamStringValue):
    pass


class JSONBody(dict):
    pass


class BytesBody(bytes):
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
        assert val is None \
            or isinstance(val, str) \
            or isinstance(val, dict) \
            or isinstance(val, StaticFile) \
            or isinstance(val, bytes), \
            "Body type is not supported."
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

    def __init__(self, code: int = 400, message: str = "", explain: str = ""):
        super().__init__("HTTP_ERROR[%d] %s" % (code, message))
        self.code: int = code
        self.message: str = message
        self.explain: str = explain


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


class FilterContex:

    @property
    def request(self) -> Request:
        return None

    @property
    def response(self) -> Response:
        return None

    @abstractmethod
    def do_chain(self):
        pass


class WebsocketRequest:

    def __init__(self):
        self.headers: Dict[str, str] = {}  # Request headers
        self.__cookies = Cookies()
        self.query_string: str = ""  # Query String
        self.path_values: Dict[str, str] = {}
        self.path: str = ""  # Path
        self.__parameters = {}  # Parameters, key-value array, merged by query string and request body if the `Content-Type` in request header is `application/x-www-form-urlencoded` or `multipart/form-data`
        self.__parameter = {}  # Parameters, key-value, if more than one parameters with the same key, only the first one will be stored.

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


class WebsocketSession:

    @property
    def id(self) -> str:
        return ""

    @property
    def request(self) -> WebsocketRequest:
        return None

    @property
    def is_closed(self) -> bool:
        return False

    def send(self, message: str):
        pass

    def send_pone(self, message: str):
        pass

    def send_ping(self, message: str):
        pass

    def close(self, reason: str):
        pass


class WebsocketHandler:

    def on_handshake(self, request: WebsocketRequest = None):
        return None

    def on_open(self, session: WebsocketSession = None):
        pass

    def on_message(self, session: WebsocketSession = None, message_type: str = "", message: Any = None):
        pass

    def on_text_message(self, session: WebsocketSession = None, message: str = ""):
        pass

    def on_close(self, session: WebsocketSession = None, reason: str = ""):
        pass


def _get_class_of_method(method_defind):
    vals = vars(sys.modules[method_defind.__module__])
    for attr in method_defind.__qualname__.split('.')[:-1]:
        if attr in vals:
            vals = vals[attr]
            if not isinstance(vals, dict):
                break
    if inspect.isclass(vals):
        return vals


def _create_object(clz, args=[], kwargs={}):

    if clz is None:
        return None
    elif args and kwargs:
        return clz(*args, **kwargs)
    elif args:
        return clz(*args)
    elif kwargs:
        return clz(**kwargs)
    else:
        return clz()


class ControllerFunction:

    def __init__(self, url: str = "",
                 regexp: str = "",
                 method: str = "",
                 ctr_obj: object = None,
                 func: Callable = None) -> None:
        self.__url: str = url
        self.__regexp = regexp
        self.__method: str = method
        self.singletion: bool = False
        self.ctr_obj_init_args = None
        self.ctr_obj_init_kwargs = None
        self.__ctr_obj: object = ctr_obj
        self.__func: Callable = func
        self.__clz = False

    @property
    def _is_config_ok(self):
        try:
            assert self.url or self.regexp, "you should set one of url and regexp"
            assert not (self.url and self.regexp), "you can only set one of url and regexp, not both"
            assert self.func is not None and (inspect.isfunction(self.func) or inspect.ismethod(self.func))
            return True
        except AssertionError as ae:
            _logger.warn(f"[{self._url}|{self.regexp}] => {self.func} configurate error: {ae}")
            return False

    @property
    def url(self) -> str:
        return self.__url

    @property
    def regexp(self) -> str:
        return self.__regexp

    @property
    def method(self) -> str:
        return self.__method

    @property
    def clz(self) -> str:
        if self.__clz != False:
            return self.__clz
        if inspect.isfunction(self.func):
            self.__clz = _get_class_of_method(self.func)
        else:
            self.__clz = None
        return self.__clz

    @property
    def ctrl_object(self) -> object:
        if not self.singletion:
            obj = self._create_ctrl_obj()
            _logger.debug(f"singleton: create a object -> {obj}")
            return obj

        if self.__ctr_obj is None:
            self.__ctr_obj = self._create_ctrl_obj()
            _logger.debug(f"object does not exist, create one -> {self.__ctr_obj} ")
        else:
            _logger.debug(f"object[{self.__ctr_obj}] exists, return. ")
        return self.__ctr_obj

    def _create_ctrl_obj(self) -> object:
        return _create_object(self.clz, self.ctr_obj_init_args, self.ctr_obj_init_kwargs)

    @ctrl_object.setter
    def ctrl_object(self, val) -> None:
        self.__ctr_obj = val

    @property
    def func(self) -> Callable:
        return self.__func


_request_mappings: List[ControllerFunction] = []
_request_clz_mapping: Dict[Any, Tuple[str, Union[str, list]]] = {}

_filters = []

_ctrls = {}
_ctrl_singletons = {}

_ws_handlers = {}

_error_page = OrderedDict()

_session_facory: SessionFactory = None


def controller(*anno_args, singleton: bool = True, args: List[Any] = [], kwargs: Dict[str, Any] = {}):
    def map(ctr_obj_class):
        _logger.debug(f"map controller[{ctr_obj_class}]({singleton}) with args: {args}, and kwargs: {kwargs})")
        _ctrls[ctr_obj_class] = (singleton, args, kwargs)
        return ctr_obj_class
    if len(anno_args) == 1 and inspect.isclass(anno_args[0]):
        return map(anno_args[0])
    return map


def request_map(*anno_args, url: str = "", regexp: str = "", method: Union[str, list, tuple] = "") -> Callable:
    _url = url
    len_args = len(anno_args)
    assert len_args <= 1

    arg_ctrl = None
    if len_args == 1:
        if isinstance(anno_args[0], str):
            assert not url and not regexp
            _url = anno_args[0]
        elif callable(anno_args[0]):
            arg_ctrl = anno_args[0]

    def map(ctrl):
        if isinstance(method, list):
            mths = method
        elif isinstance(method, tuple):
            mths = list(method)
        else:
            mths = [m.strip() for m in method.split(',')]

        if inspect.isclass(ctrl):
            _request_clz_mapping[ctrl] = (_url, mths)
            return ctrl

        for mth in mths:
            _logger.debug(f"map url {_url} with method[{mth}] to function {ctrl}. ")
            _request_mappings.append(ControllerFunction(url=_url, regexp=regexp, method=mth, func=ctrl))
        # return the original function, so you can use a decoration chain
        return ctrl

    if arg_ctrl:
        return map(arg_ctrl)
    else:
        return map


route = request_map


def request_filter(path: str = "", regexp: str = ""):
    p = path
    r = regexp
    assert (p and not r) or (not p and r)

    def map(filter_fun):
        _filters.append({"path": p, "url_pattern": r, "func": filter_fun})
        return filter_fun
    return map


def filter_map(regexp: str = "", filter_function: Callable = None) -> Callable:
    """ deprecated, plese request_filter instead. """
    def map(filter_fun):
        _filters.append({"url_pattern": regexp, "func": filter_fun})
        return filter_fun
    if filter_function:
        map(filter_function)
    return map


def set_session_factory(session_factory: SessionFactory):
    global _session_facory
    _session_facory = session_factory


def _get_singletion(clz, args, kwargs):
    if clz not in _ctrl_singletons:
        _ctrl_singletons[clz] = _create_object(clz, args, kwargs)
    return _ctrl_singletons[clz]


def websocket_handler(endpoint=""):
    def map(ws_class):
        _ws_handlers[endpoint] = ws_class
        return ws_class

    return map


def error_message(*anno_args):
    len_args = len(anno_args)
    arg_func = None

    if len_args == 1:
        if callable(anno_args[0]):
            arg_func = anno_args[0]

    if not arg_func:
        if anno_args:
            args = [it for it in anno_args]
        else:
            args = [""]
    else:
        args = [""]

    def map(func):
        for arg in args:
            _error_page[arg] = func
        return func

    if arg_func:
        return map(arg_func)
    else:
        return map


def _get_request_mappings():
    mappings: List[ControllerFunction] = []

    for ctr_fun in _request_mappings:
        clz = ctr_fun.clz
        if clz is not None and clz in _request_clz_mapping:
            clz_url, methods = _request_clz_mapping[clz]

            if ctr_fun.regexp:
                full_url = ctr_fun.url
            else:
                fun_url = ctr_fun.url
                if fun_url:
                    if not clz_url.endswith("/"):
                        clz_url = clz_url + "/"
                    if fun_url.startswith("/"):
                        fun_url = fun_url[1:]
                    full_url = f"{clz_url}{fun_url}"
                else:
                    full_url = clz_url

            if not ctr_fun.method and methods:
                for mth in methods:
                    _logger.debug(f"map url {full_url} included [{clz_url}] with method[{mth}] to function {ctr_fun.func}. ")
                    mappings.append(ControllerFunction(url=full_url, regexp=ctr_fun.regexp, method=mth, func=ctr_fun.func))
            else:
                _logger.debug(f"map url {full_url} included [{clz_url}] with method[{ctr_fun.method}] to function {ctr_fun.func}. ")
                mappings.append(ControllerFunction(url=full_url, regexp=ctr_fun.regexp, method=ctr_fun.method, func=ctr_fun.func))
        else:
            mappings.append(ctr_fun)

    for ctr_fun in mappings:
        if not ctr_fun._is_config_ok:
            continue
        clz = ctr_fun.clz
        if clz is not None and clz in _ctrls:
            singleton, args, kwargs = _ctrls[clz]
            ctr_fun.singletion = singleton
            ctr_fun.ctr_obj_init_args = args
            ctr_fun.ctr_obj_init_kwargs = kwargs
            if singleton:
                ctr_fun.ctrl_object = _get_singletion(clz, args, kwargs)

    return mappings


def _get_filters():
    return _filters


def _get_session_factory() -> SessionFactory:
    return _session_facory


def _get_websocket_handlers() -> Dict[str, Type]:
    return _ws_handlers


def _get_error_pages() -> Dict[str, Callable]:
    _logger.debug(f"error pages:: {_error_page}")
    return _error_page
