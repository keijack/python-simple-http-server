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

import sys
import inspect
import asyncio
import base64
from typing import Any, Dict, List, Type, Union, Callable

from .models.basic_models import Headers, SessionFactory, WebsocketHandler
from .models.basic_models import WEBSOCKET_MESSAGE_BINARY, WEBSOCKET_MESSAGE_BINARY_FRAME, WEBSOCKET_MESSAGE_PING, WEBSOCKET_MESSAGE_PONG, WEBSOCKET_MESSAGE_TEXT
from .models.model_bindings import ModelBindingConf
from .utils.logger import get_logger

_logger = get_logger("naja_atra.app_conf")


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


def _to_str_list(obj: Union[str, list, tuple]):
    if isinstance(obj, list) or isinstance(obj, tuple):
        return [str(it) for it in obj]
    else:
        return [str(obj)]


class ControllerFunction:

    def __init__(self, url: str = "",
                 regexp: str = "",
                 method: str = "",
                 headers: List[str] = [],
                 match_all_headers_expressions: bool = None,
                 params: List[str] = [],
                 match_all_params_expressions: bool = None,
                 func: Callable = None) -> None:
        self.__url: str = url
        self.__regexp = regexp
        self.__method: str = method
        self.singleton: bool = False
        self.ctr_obj_init_args = None
        self.ctr_obj_init_kwargs = None
        self.__ctr_obj: object = None
        self.__func: Callable = func
        self.__clz = False
        self.headers: List[str] = headers if isinstance(headers, list) else [
            headers]
        self._match_all_headers_expressions: bool = match_all_headers_expressions
        self.params: List[str] = params if isinstance(params, list) else [
            params]
        self._match_all_params_expressions: bool = match_all_params_expressions

    @property
    def match_all_headers_expressions(self):
        return self._match_all_headers_expressions if self._match_all_headers_expressions is not None else True

    @property
    def match_all_params_expressions(self):
        return self._match_all_params_expressions if self._match_all_params_expressions is not None else True

    @property
    def _is_config_ok(self):
        try:
            assert self.url or self.regexp, "you should set one of url and regexp"
            assert not (
                self.url and self.regexp), "you can only set one of url and regexp, not both"
            assert self.func is not None and (inspect.isfunction(
                self.func) or inspect.ismethod(self.func))
            return True
        except AssertionError as ae:
            _logger.warn(
                f"[{self.__url}|{self.regexp}] => {self.func} configurate error: {ae}")
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
        if not self.singleton:
            obj = self._create_ctrl_obj()
            _logger.debug(f"singleton: create a object -> {obj}")
            return obj

        if self.__ctr_obj is None:
            self.__ctr_obj = self._create_ctrl_obj()
            _logger.debug(
                f"object does not exist, create one -> {self.__ctr_obj} ")
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


class WebsocketHandlerProxy(WebsocketHandler):

    def __init__(self) -> None:
        self.handshake: Callable = None
        self.open: Callable = None
        self.close: Callable = None
        self.ping: Callable = None
        self.pong: Callable = None
        self.text: Callable = None
        self.binary: Callable = None
        self.binary_frame: Callable = None

    async def await_func(self, obj):
        if asyncio.iscoroutine(obj):
            return await obj
        return obj

    async def on_handshake(self, *args, **kwargs):
        if self.handshake:
            return await self.await_func(self.handshake(*args, **kwargs))
        return None

    async def on_open(self, *args, **kwargs):
        if self.open:
            await self.await_func(self.open(*args, **kwargs))

    async def on_close(self, *args, **kwargs):
        if self.close:
            await self.await_func(self.close(*args, **kwargs))

    async def on_ping_message(self, *args, **kwargs):
        if self.ping:
            await self.await_func(self.ping(*args, **kwargs))
        else:
            return super().on_ping_message()

    async def on_pong_message(self, *args, **kwargs):
        if self.pong:
            await self.await_func(self.pong(*args, **kwargs))

    async def on_text_message(self, *args, **kwargs):
        if self.text:
            await self.await_func(self.text(*args, **kwargs))

    async def on_binary_message(self, *args, **kwargs):
        if self.binary:
            await self.await_func(self.binary(*args, **kwargs))

    async def on_binary_frame(self, *args, **kwargs):
        if self.binary_frame:
            return await self.await_func(self.binary_frame(*args, **kwargs))
        return super().on_binary_frame()


class WebsocketHandlerClass:

    def __init__(self, url: str = "",
                 cls: Callable = None,
                 regexp: str = "",
                 singleton: bool = True
                 ) -> None:
        self.__url: str = url
        self.__regexp = regexp
        self.singleton: bool = singleton
        self.ctr_obj_init_args = None
        self.ctr_obj_init_kwargs = None
        self.__ctr_obj: object = None
        self.__cls: Callable = cls

    @property
    def _is_config_ok(self):
        try:
            assert self.url or self.regexp, "you should set one of url and regexp"
            assert not (
                self.url and self.regexp), "you can only set one of url and regexp, not both"
            assert self.cls is not None and inspect.isclass(self.cls)
            return True
        except AssertionError as ae:
            _logger.warn(
                f"[{self.__url}|{self.regexp}] => {self.cls} configurate error: {ae}")
            return False

    @property
    def url(self) -> str:
        return self.__url

    @property
    def regexp(self) -> str:
        return self.__regexp

    @property
    def cls(self) -> str:
        return self.__cls

    @property
    def ctrl_object(self) -> object:
        if not self.cls:
            return self.__ctr_obj
        if not self.singleton:
            obj = self._create_ctrl_obj()
            _logger.debug(f"singleton: create a object -> {obj}")
            return obj

        if self.__ctr_obj is None:
            self.__ctr_obj = self._create_ctrl_obj()
            _logger.debug(
                f"object does not exist, create one -> {self.__ctr_obj} ")
        else:
            _logger.debug(f"object[{self.__ctr_obj}] exists, return. ")
        return self.__ctr_obj

    def _create_ctrl_obj(self) -> object:
        return _create_object(self.cls, self.ctr_obj_init_args, self.ctr_obj_init_kwargs)

    @ctrl_object.setter
    def ctrl_object(self, val) -> None:
        self.__ctr_obj = val


__favicon = base64.b64decode(
    b'AAABAAEAICAAAAEAIACoEAAAFgAAACgAAAAgAAAAQAAAAAEAIAAAAAAAABAAAMMOAADDDgAAAAAAAAAAAAD/////7+/v/4uLjP8qKiz/AwMD/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8A' +
    b'AAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/AAAA/wAAAP8AAAD/IyMk/319f//o6Oj//////+/v7/9jY2X/BwcI/yEhIv9NTU//VFRV/1RUVf9UVFX/U1NU/1RUVf9TU1X/U1NV/1VVVv9TU1X/VVVW/1RUVv9UVFX/U1NV/1NTVP9TU1T/' +
    b'U1NV/1NTVf9UVFX/U1NU/1NTVP9UVFX/VFRV/05OUP8lJSb/BQUG/1paW//p6en/ioqL/wgICf9TU1T/19fX/+bm5v/09PT/8PDw//Ly8v/8/Pz/9fX1//r6+v/29vb/4uLi//j4+P/V1dX/4+Pj//T09P/6+vr/+/v7//v7+//5+fn/9/f4' +
    b'/+np6v/7+/v//Pz8/+rq6v/y8vL/9vb2/9zc3P9eXl//BgYG/319f/8xMTL/HR0e/9TU1P/5+fn/ZmZo/7+/wP+CgoP/gYGC//Pz8/+Ghof/n5+g/6amp/8uLjD/u7u8/6+vsP+EhIX/fX1+/7Cwsf//////6Ojo/4+PkP+9vb3/Q0NF/5eX' +
    b'mP+kpKX/PT1A/5ubnP92dnf/4uLi/97e3/8mJij/IyMl/w0ND/9DQ0X/9vb2//b29v9OTk7/S0tM/0RERf9BQUH/eHh5/3l5ev8ODhD/QkJE/y0tLv+cnJz/kJCR/1xcXP9zc3X/MTEz/9/f3/+Dg4T/IyMl/52dnv9KSkv/Dg4Q/w4OD/86' +
    b'Ojv/mJiZ/zw8Pv/T09P//Pz8/09PUP8AAAD/AAAA/0pKTP/5+fn/9fX1/09PUf84ODn/VVVW/zU1N/9VVVX/enp7/wUFBv+AgIH/UlJU/4GBgv+vr7D/oaGi/+zs7P9GRkj/aWlq/y4uL/+Pj5D/mJiZ/x0dH/8MDA7/DAwO/x4eIf+QkJH/' +
    b'tra3//Dw8P/7+/v/U1NV/wAAAP8AAAD/SkpM//v7+//R0dL/Kysu/1tbXf9HR0n/NDQ2/3NzdP9CQkP/KCgq/ywsLv8HBwr/Ghod/87Oz////////////56en/8LCw3/Ozs8/+zs7P/R0dH/XFxe/1VVV/9kZGX/eHh5/7+/wP9zc3X/5+fn' +
    b'//z8/P9TU1T/AAAA/wAAAP9KSkz//Pz9/6+vr/8RERP/aWlr/2lpa/8yMjT/fHx+/1paXP84ODr/SUlL/zQ0Nv9OTk//6Ojo////////////zc3N/xEREv+FhYb//////9jY2P85OTv/Dw8R/xUVGP80NDf/urq6/0tLTP/Z2dn//f39/1NT' +
    b'VP8AAAD/AAAA/0pKTP/6+vv/2trb/ysrLf8zMzX/GRkb/w8PEP86Ojr/LS0v/wAAAv9cXF7/cHBx/1RUVf/4+Pj////////////a2tr/IyMl/7m5uf//////yMjI/0BAQf8EBAb/BAQF/zo6PP+lpab/MzM1/8zMzP/9/f3/U1NU/wAAAP8A' +
    b'AAD/SkpM//n5+f/9/f3/ZGRl/0dHSf8eHh//Q0NF/3x8fv9tbW7/PT0+/2JiZP8MDA7/Li4v/+rq6v///////////93d3f8vLy//ycnJ///////ExMX/Hx8g/x8fIP8hISL/IiIj/6OjpP85OTv/y8vM//39/f9TU1T/AAAA/wAAAP9KSkz/' +
    b'+fn5///////Ly8v/u7u7/6Kio//k5OT//////8/Pz/+np6f/zs7P/4mJi/+goKH/9fX1////////////7Ozs/4uLjP/i4uL///////j4+P+vr7D/oqKj/6Skpf+vr6//8PDx/87Ozv/y8vP/+/v8/1NTVP8AAAD/AAAA/0lJSv/z8/T/+vr6' +
    b'//v7+//8/Pz//Pz9//v7///6+v7/+vr+//v7///7+/3//f3+//39///6+v7/+vr+//r6/v/6+v7/+/v///r6/v/5+fr/+vr6//z8/P/7+/v/+/v7//z8/P/6+vr//Pz8//r6+v/19fX/UlJT/wAAAP8AAAL/FxcY/01NS/9PT03/Tk9N/05O' +
    b'Tf9QUFj/XlzG/2Vi9f9kYvL/ZWL1/11bt/9SUWX/YV/c/2Vi8/9kYvL/ZGLy/2Vi8/9lYvX/X13N/1BQWf9OT03/Tk9N/09PTf9PT03/Tk9N/05PTf9OT03/T09N/01NTP8aGhv/AAAC/wEBA/8BARD/BAMx/wQDMv8EAzL/BAMy/wEBGP8H' +
    b'BkL/HRnZ/yAc7v8gHe//GRa+/wMCGv8VEqH/IB3w/yAc7P8gHOz/HRnY/x8b5/8SD4j/AAAK/wMDLv8EAzL/BAMy/wQDMv8EAzL/BAMy/wQDMv8EAzL/BAMx/wEBEv8BAQP/AQEA/woJQ/8hHdv/Ih7f/yIe3/8iHuH/Ghix/wQEHf8QDmr/' +
    b'Ix/p/yQg7v8iH+T/CQg8/w8NYv8kIO3/JCDt/yQg7P8YFqL/HhvI/wsKS/8KCUb/IR3a/yIe3/8iHt//Ih7f/yIe3/8iHt//Ih7f/yIe3/8hHtz/CwpL/wEBAP8BAQD/CglI/yMf6f8kIO7/JCDu/yQg7f8kIO//FhSU/wMDF/8WFJX/Ix/o' +
    b'/yEe3P8SEHf/BgYt/yEd2f8kIO7/JCDt/yMg7P8eG8n/BAQe/xQSif8kIfL/JCHx/yQg7/8kIO7/JCDu/yQg7v8kIO7/JCDu/yMg6/8MClD/AQEA/wEBAP8KCUf/Ix/o/yQg7f8kIO3/Ix/p/xoXq/8RD3H/BAMa/wUFJP8bGLT/GRal/xoY' +
    b'sP8DAxf/Gher/yQg8P8kIOz/JCHx/xYUlf8EAxr/HRrA/yEe3f8cGbv/IBzT/yQg7/8kIO3/JCDs/yQg7P8kIO3/Ix/q/wwKT/8BAQD/AQEA/woJR/8jH+j/JCDt/yQg7f8kIPD/IR3a/xMRg/8EAxr/BQQh/x8czv8jIOz/IR3b/wcGLv8R' +
    b'D27/JCHy/yQg7v8hHt3/DAtR/wMDFP8MC1H/BwYx/wUEIf8JCD//FxSa/yIf5f8kIO7/JCDt/yQg7f8jH+r/DApP/wEBAP8BAQD/CglH/yMf6P8kIO7/Ih7i/xsYs/8ZFqf/GRao/wgHOf8MCk//Ix/p/yQg7f8kIO3/Dw1m/wcGLv8XFZr/' +
    b'EA5r/wgHNv8DAhT/BgUn/wwLU/8VEov/HRq//xoXrv8KCUn/DApW/x8c0P8kIO7/JCDt/yMf6v8MCk//AQEA/wEBAP8KCUf/Ix/o/yQg7f8jH+j/Ghes/woJQ/8BAQz/AAAF/xUTjf8kIfH/JCDt/yQh8f8XFZv/AQEF/wAABP8AAAD/CglF' +
    b'/xsYsP8hHdn/Ih7k/x4bz/8XFJ//EA5o/w8OM/8VFRT/EhB1/yQg7v8kIO3/Ix/q/wwKT/8BAQD/AQEA/woJR/8jH+j/JCDt/yMg6v8jIOv/IR3Z/xEPdP8EBB3/HRm+/yIf5P8kIO7/IR3a/wsKSv8HBjD/Dgxe/wwKT/8HBi//FROM/xQR' +
    b'hv8REFH/Gxs1/zExNf9OTkv/ZWVi/2NjXv8QDz7/IR7e/yQg7v8jH+r/DApP/wEBAP8BAQD/CglH/yMf6P8kIO7/IB3W/xMRff8MC1P/CQg8/wcGMv8dGb3/FxWc/yQg7/8VE4//CAc2/xMQfP8RD2//EQ9w/xAOa/8CAQ3/AAAA/ygoJv9q' +
    b'amf/Xl5i/0hHXP8vLmH/Hhx5/w8NW/8gHdT/JCDu/yMf6v8MCk//AQEA/wEBAP8KCUf/Ix/o/yQg7f8kIOz/HxzR/xEPc/8DAxj/AgIP/xoXrf8jH+b/JCDv/xEPbv8PDWH/EQ9w/yEd2f8bGLH/FxSZ/wYFJf8CAhH/ERBB/yEfef8ZF53/' +
    b'GxjE/x8c2v8eG8z/ExB9/yAc0/8kIO7/Ix/q/wwKT/8BAQD/AQEA/woJR/8jH+j/JCDt/yMf5/8eG8r/HRrA/xYTkv8GBSn/Dw1i/yQg7P8kIPD/FROM/w4MXv8cGbr/JCDt/yQh8f8dGsP/CwpL/xsYtv8iHuP/Ix/t/yQh8v8lIfT/IBzS' +
    b'/wsJSP8ODF3/Ih7f/yQg7v8jH+r/DApP/wEBAP8BAQD/CglH/yMf6P8kIO3/Ix/n/xkWpv8KCUP/AwMY/wEBC/8FBSP/HBm4/xkWp/8gHNT/Dg1g/xgVoP8hHdj/HhvK/xUSiv8bGLT/HRq3/x8cyv8jH+j/HxzR/xgVoP8ODWD/CQg6/xwZ' +
    b'uf8kIO7/JCDt/yMf6v8MCk//AQEA/wEBAP8KCUf/Ix/o/yQg7f8kIO3/JCDu/yAc1P8TEHz/BQQg/wAAA/8QDmz/HhrF/yQg8P8gHNT/FhOR/xQSiP8XFJj/HRrE/xQSdf8bGyj/FRRe/xEPdv8KCUT/Dw1j/xcVnP8gHdX/JCDu/yQg7f8k' +
    b'IO3/Ix/q/wwKT/8BAQD/AAAA/wsJSP8jH+j/JCDt/yQg7f8kIO3/JCDu/yQg7v8eG8f/Dw1l/wQDG/8MCk7/HBm8/yQg7/8gHNP/Ih7f/yEe3/8fHNH/HRrA/xkXk/8ODFr/CglF/x0awf8jIOz/JCDw/yQg7v8kIO3/JCDt/yQg7f8jH+r/' +
    b'DApQ/wEBAP8QEQ//CQhA/yIf5f8kIO3/JCDt/yQg7f8kIO3/JCDt/yQg7/8jIOv/Gxi0/wsKTP8FBCP/EhB5/xYTj/8aF6v/ExB9/wYGLP8PDWf/EA5r/wsJSP8eG8n/JCDw/yQg7f8kIO3/JCDt/yQg7f8kIO3/JCDt/yMf6f8LCkv/AQEA' +
    b'/zs7Ov8CAhr/HhrF/yQh8f8kIO3/JCDt/yQg7f8kIO3/JCDt/yQg7f8kIPD/Ih/l/xgVnv8JCD3/CAc3/wsKS/8PDWT/FhOQ/xgVnv8TEX3/HhvJ/yQg8P8kIO3/JCDt/yQg7f8kIO3/JCDt/yQg7f8kIfD/HxzO/wQDI/8mJib/j4+Q/wkJ' +
    b'Cv8LCUz/HhvH/yMf5/8jH+j/Ix/o/yMf6P8jH+j/Ix/o/yMf6P8jH+n/JCDr/yAd1v8cGbn/IB3U/yMf5/8kIOz/JCDs/yMg6/8jIOn/Ix/o/yMf6P8jH+j/Ix/o/yMf6P8jH+j/Ix/n/x8bzP8MC1b/BgYH/4iIif/y8vL/cnJz/wgICf8C' +
    b'Ah3/CQhD/wsJSP8KCUf/CglH/woJR/8KCUf/CglH/woJR/8KCUf/CwlI/wsKSv8LCUj/CglH/woJR/8KCUf/CglH/woJR/8KCUf/CglH/woJR/8KCUf/CglH/wsJR/8KCUT/AwMg/wQEBv9aWlz/6enp///////y8vL/i4uM/zAwMP8JCQn/' +
    b'AAAA/wEBAP8BAQD/AQEA/wEBAP8BAQD/AQEA/wEBAP8BAQD/AQEA/wEBAP8BAQD/AQEA/wEBAP8BAQD/AQEA/wEBAP8BAQD/AQEA/wEBAP8BAQD/AAAA/wQEA/8sLCz/h4eJ/+np6f//////AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA' +
    b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
)


def _favicon():
    return Headers({"Content-Type": "image/x-icon"}), __favicon


class AppConf:

    def __init__(self) -> None:
        self._request_mappings: List[ControllerFunction] = []
        self._request_clz_mapping: Dict[Any, ControllerFunction] = {}

        self._filters = []

        self._ctrls = {}
        self._ctrl_singletons = {}

        self._ws_handlers: Dict[str, WebsocketHandlerClass] = {}

        self._error_page = {}

        self.session_factory: SessionFactory = None

        self.request_map("/favicon.ico")(_favicon)
        self.route = self.request_map
        self.model_binding_conf = ModelBindingConf()

    def model_binding(self, arg_type: Type):
        def map(model_binding_type):
            self.model_binding_conf.model_bingding_types[arg_type] = model_binding_type
            return model_binding_type
        return map

    def default_model_binding(self, *anno_args):
        def map(model_binding_type):
            self.model_binding_conf.default_model_binding_type = model_binding_type
            return model_binding_type
        if len(anno_args) == 1 and inspect.isclass(anno_args[0]):
            return map(anno_args[0])
        return map

    def controller(self, *anno_args, singleton: bool = True, args: List[Any] = [], kwargs: Dict[str, Any] = {}):
        def map(ctr_obj_class):
            _logger.debug(
                f"map controller[{ctr_obj_class}]({singleton}) with args: {args}, and kwargs: {kwargs})")
            self._ctrls[ctr_obj_class] = (singleton, args, kwargs)
            return ctr_obj_class
        if len(anno_args) == 1 and inspect.isclass(anno_args[0]):
            return map(anno_args[0])
        return map

    def request_map(self, *anno_args,
                    url: str = "",
                    regexp: str = "",
                    method: Union[str, list, tuple] = "",
                    headers: Union[str, list, tuple] = "",
                    match_all_headers_expressions: bool = None,
                    params: Union[str, list, tuple] = "",
                    match_all_params_expressions: bool = None) -> Callable:
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

            hs = _to_str_list(headers)
            ps = _to_str_list(params)

            if inspect.isclass(ctrl):
                self._request_clz_mapping[ctrl] = ControllerFunction(url=_url,
                                                                     regexp=regexp,
                                                                     method=mths,
                                                                     headers=hs,
                                                                     match_all_headers_expressions=match_all_headers_expressions,
                                                                     params=ps,
                                                                     match_all_params_expressions=match_all_params_expressions,
                                                                     func=ctrl)

                return ctrl

            for mth in mths:
                cf = ControllerFunction(url=_url,
                                        regexp=regexp,
                                        method=mth,
                                        headers=hs,
                                        match_all_headers_expressions=match_all_headers_expressions,
                                        params=ps,
                                        match_all_params_expressions=match_all_params_expressions,
                                        func=ctrl)
                _logger.debug(
                    f"map url {_url} with method[{mth}] to function {ctrl}. with headers {cf.headers} and params {cf.params}")
                self._request_mappings.append(cf)
            # return the original function, so you can use a decoration chain
            return ctrl

        if arg_ctrl:
            return map(arg_ctrl)
        else:
            return map

    def request_filter(self, path: str = "", regexp: str = ""):
        p = path
        r = regexp
        assert (p and not r) or (not p and r)

        def map(filter_fun):
            self._filters.append(
                {"path": p, "url_pattern": r, "func": filter_fun})
            return filter_fun
        return map

    def filter_map(self, regexp: str = "", filter_function: Callable = None) -> Callable:
        """ deprecated, plese request_filter instead. """
        def map(filter_fun):
            self._filters.append({"url_pattern": regexp, "func": filter_fun})
            return filter_fun
        if filter_function:
            map(filter_function)
        return map

    def _get_singletion(self, clz, args, kwargs):
        if clz not in self._ctrl_singletons:
            self._ctrl_singletons[clz] = _create_object(clz, args, kwargs)
        return self._ctrl_singletons[clz]

    def websocket_handler(self, endpoint: str = "", regexp: str = "", singleton: bool = True) -> Callable:
        def map(ws_class):
            self._ws_handlers[endpoint + ":::" + regexp] = WebsocketHandlerClass(
                url=endpoint, regexp=regexp, cls=ws_class, singleton=singleton)
            return ws_class

        return map

    def websocket_handshake(self, endpoint: str = "", regexp: str = "") -> Callable:
        def map(ctrl):
            k = endpoint + ":::" + regexp
            if k not in self._ws_handlers:
                handler = WebsocketHandlerClass(url=endpoint, regexp=regexp)
                handler.ctrl_object = WebsocketHandlerProxy()
                handler.ctrl_object.handshake = ctrl
                self._ws_handlers[k] = handler
            else:
                handler = self._ws_handlers[k]
                if not handler.cls and isinstance(handler.ctrl_object, WebsocketHandlerProxy):
                    handler.ctrl_object.handshake = ctrl
            return ctrl
        return map

    def websocket_open(self, endpoint: str = "", regexp: str = "") -> Callable:
        def map(ctrl):
            k = endpoint + ":::" + regexp
            if k not in self._ws_handlers:
                handler = WebsocketHandlerClass(url=endpoint, regexp=regexp)
                handler.ctrl_object = WebsocketHandlerProxy()
                handler.ctrl_object.open = ctrl
                self._ws_handlers[k] = handler
            else:
                handler = self._ws_handlers[k]
                if not handler.cls and isinstance(handler.ctrl_object, WebsocketHandlerProxy):
                    handler.ctrl_object.open = ctrl
            return ctrl
        return map

    def websocket_close(self, endpoint: str = "", regexp: str = "") -> Callable:
        def map(ctrl):
            k = endpoint + ":::" + regexp
            if k not in self._ws_handlers:
                handler = WebsocketHandlerClass(url=endpoint, regexp=regexp)
                handler.ctrl_object = WebsocketHandlerProxy()
                handler.ctrl_object.close = ctrl
                self._ws_handlers[k] = handler
            else:
                handler = self._ws_handlers[k]
                if not handler.cls and isinstance(handler.ctrl_object, WebsocketHandlerProxy):
                    handler.ctrl_object.close = ctrl
            return ctrl
        return map

    def websocket_message(self, endpoint: str = "", regexp: str = "", message_type: str = WEBSOCKET_MESSAGE_TEXT) -> Callable:
        def map(ctrl):
            k = endpoint + ":::" + regexp
            if k not in self._ws_handlers:
                handler = WebsocketHandlerClass(url=endpoint, regexp=regexp)
                handler.ctrl_object = WebsocketHandlerProxy()
                self._ws_handlers[k] = handler

            handler = self._ws_handlers[k]
            if not handler.cls and isinstance(handler.ctrl_object, WebsocketHandlerProxy):
                if message_type == WEBSOCKET_MESSAGE_TEXT:
                    handler.ctrl_object.text = ctrl
                elif message_type == WEBSOCKET_MESSAGE_BINARY:
                    handler.ctrl_object.binary = ctrl
                elif message_type == WEBSOCKET_MESSAGE_BINARY_FRAME:
                    handler.ctrl_object.binary_frame = ctrl
                elif message_type == WEBSOCKET_MESSAGE_PING:
                    handler.ctrl_object.ping = ctrl
                elif message_type == WEBSOCKET_MESSAGE_PONG:
                    handler.ctrl_object.pong = ctrl
                else:
                    _logger.error(
                        f"Cannot match message type: [{message_type}]!")
            return ctrl
        return map

    def error_message(self, *anno_args):
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
                self._error_page[arg] = func
            return func

        if arg_func:
            return map(arg_func)
        else:
            return map

    def _get_request_mappings(self) -> List[ControllerFunction]:
        mappings: List[ControllerFunction] = []

        for ctr_fun in self._request_mappings:
            clz = ctr_fun.clz
            if clz is not None and clz in self._request_clz_mapping:
                clz_ctrl = self._request_clz_mapping[clz]
                clz_url = clz_ctrl.url
                methods = clz_ctrl.method

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

                hs = ctr_fun.headers + clz_ctrl.headers
                mhs = ctr_fun._match_all_headers_expressions if ctr_fun._match_all_headers_expressions is not None else clz_ctrl._match_all_headers_expressions
                ps = ctr_fun.params + clz_ctrl.params
                mps = ctr_fun._match_all_params_expressions if ctr_fun._match_all_params_expressions is not None else clz_ctrl._match_all_params_expressions
                if not ctr_fun.method and methods:
                    for mth in methods:
                        _logger.debug(
                            f"map url {full_url} included [{clz_url}] with method[{mth}] to function {ctr_fun.func}. ")
                        mappings.append(ControllerFunction(url=full_url,
                                                           regexp=ctr_fun.regexp,
                                                           method=mth,
                                                           func=ctr_fun.func,
                                                           headers=hs,
                                                           match_all_headers_expressions=mhs,
                                                           params=ps,
                                                           match_all_params_expressions=mps))
                else:
                    _logger.debug(
                        f"map url {full_url} included [{clz_url}] with method[{ctr_fun.method}] to function {ctr_fun.func}. ")
                    mappings.append(ControllerFunction(url=full_url,
                                                       regexp=ctr_fun.regexp,
                                                       method=ctr_fun.method,
                                                       func=ctr_fun.func,
                                                       headers=hs,
                                                       match_all_headers_expressions=mhs,
                                                       params=ps,
                                                       match_all_params_expressions=mps))
            else:
                mappings.append(ctr_fun)

        for ctr_fun in mappings:
            if not ctr_fun._is_config_ok:
                continue
            clz = ctr_fun.clz
            if clz is not None and clz in self._ctrls:
                singleton, args, kwargs = self._ctrls[clz]
                ctr_fun.singleton = singleton
                ctr_fun.ctr_obj_init_args = args
                ctr_fun.ctr_obj_init_kwargs = kwargs
                if singleton:
                    ctr_fun.ctrl_object = self._get_singletion(
                        clz, args, kwargs)

        return mappings

    def _get_filters(self):
        return self._filters

    def _get_websocket_handlers(self) -> List[WebsocketHandlerClass]:
        return list(self._ws_handlers.values())

    def _get_error_pages(self) -> Dict[str, Callable]:
        return self._error_page


_default_app_conf = AppConf()
_app_confs: Dict[str, AppConf] = {}


def controller(*anno_args, singleton: bool = True, args: List[Any] = [], kwargs: Dict[str, Any] = {}):
    return _default_app_conf.controller(*anno_args, singleton=singleton, args=args, kwargs=kwargs)


def request_map(*anno_args,
                url: str = "",
                regexp: str = "",
                method: Union[str, list, tuple] = "",
                headers: Union[str, list, tuple] = "",
                match_all_headers_expressions: bool = None,
                params: Union[str, list, tuple] = "",
                match_all_params_expressions: bool = None) -> Callable:
    return _default_app_conf.request_map(*anno_args, url=url,
                                         regexp=regexp,
                                         method=method,
                                         headers=headers,
                                         match_all_headers_expressions=match_all_headers_expressions,
                                         params=params,
                                         match_all_params_expressions=match_all_params_expressions)


route = request_map


def request_filter(path: str = "", regexp: str = ""):
    return _default_app_conf.request_filter(path=path, regexp=regexp)


def filter_map(regexp: str = "", filter_function: Callable = None) -> Callable:
    """ deprecated, plese request_filter instead. """
    _logger.warning(
        "`filter_map` is deprecated and will be removed in future version,  please use `request_filter` instead. ")
    return _default_app_conf.filter_map(regexp=regexp, filter_function=filter_function)


def websocket_handler(endpoint: str = "", regexp: str = "", singleton: bool = True) -> Callable:
    return _default_app_conf.websocket_handler(endpoint=endpoint, regexp=regexp, singleton=singleton)


def websocket_handshake(endpoint: str = "", regexp: str = ""):
    return _default_app_conf.websocket_handshake(endpoint=endpoint, regexp=regexp)


def websocket_open(endpoint: str = "", regexp: str = ""):
    return _default_app_conf.websocket_open(endpoint=endpoint, regexp=regexp)


def websocket_close(endpoint: str = "", regexp: str = ""):
    return _default_app_conf.websocket_close(endpoint=endpoint, regexp=regexp)


def websocket_message(endpoint: str = "", regexp: str = "", message_type: str = WEBSOCKET_MESSAGE_TEXT):
    return _default_app_conf.websocket_message(endpoint=endpoint, regexp=regexp, message_type=message_type)


def error_message(*anno_args):
    return _default_app_conf.error_message(*anno_args)


def model_binding(arg_type: Type):
    return _default_app_conf.model_binding(arg_type)


def default_model_binding(*anno_args):
    return _default_app_conf.default_model_binding(*anno_args)


def get_app_conf(tag: str = "") -> AppConf:
    if not tag:
        return _default_app_conf
    if tag not in _app_confs:
        _app_confs[tag] = AppConf()
    return _app_confs[tag]


_session_facory: SessionFactory = None


def set_session_factory(session_factory: SessionFactory):
    global _session_facory
    _session_facory = session_factory


def _get_session_factory() -> SessionFactory:
    return _session_facory
