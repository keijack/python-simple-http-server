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
from typing import Any, Dict, List, Union, Callable

from .basic_models import SessionFactory, WebsocketHandler
from .basic_models import WEBSOCKET_MESSAGE_BINARY, WEBSOCKET_MESSAGE_BINARY_FRAME, WEBSOCKET_MESSAGE_PING, WEBSOCKET_MESSAGE_PONG, WEBSOCKET_MESSAGE_TEXT
from .logger import get_logger

_logger = get_logger("simple_http_server.app_conf")


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


def _favicon():
    return b'\x00\x00\x01\x00\x01\x00  \x00\x00\x01\x00 \x00\xa8\x10\x00\x00\x16\x00\x00\x00(\x00\x00\x00 \x00\x00\x00@\x00\x00\x00\x01\x00 ' + \
        b'\x00\x00\x00\x00\x00\x00\x10\x00\x00\xc3\x0e\x00\x00\xc3\x0e\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xff\xff\xff\xef\xef\xef\xff' + \
        b'\x8b\x8b\x8c\xff**,\xff\x03\x03\x03\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00' + \
        b'\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff' + \
        b'\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00\x00\x00\xff\x00' + \
        b'\x00\x00\xff##$\xff}}\x7f\xff\xe8\xe8\xe8\xff\xff\xff\xff\xff\xef\xef\xef\xffcce\xff\x07\x07\x08\xff!!"\xffMMO\xffTTU\xffTTU\xffTTU' + \
        b'\xffSST\xffTTU\xffSSU\xffSSU\xffUUV\xffSSU\xffUUV\xffTTV\xffTTU\xffSSU\xffSST\xffSST\xffSSU\xffSSU\xffTTU\xffSST\xffSST\xffTTU\xffTTU' + \
        b'\xffNNP\xff%%&\xff\x05\x05\x06\xffZZ[\xff\xe9\xe9\xe9\xff\x8a\x8a\x8b\xff\x08\x08\t\xffSST\xff\xd7\xd7\xd7\xff\xe6\xe6\xe6\xff\xf4\xf4' + \
        b'\xf4\xff\xf0\xf0\xf0\xff\xf2\xf2\xf2\xff\xfc\xfc\xfc\xff\xf5\xf5\xf5\xff\xfa\xfa\xfa\xff\xf6\xf6\xf6\xff\xe2\xe2\xe2\xff\xf8\xf8\xf8\xff' + \
        b'\xd5\xd5\xd5\xff\xe3\xe3\xe3\xff\xf4\xf4\xf4\xff\xfa\xfa\xfa\xff\xfb\xfb\xfb\xff\xfb\xfb\xfb\xff\xf9\xf9\xf9\xff\xf7\xf7\xf8\xff\xe9\xe9' + \
        b'\xea\xff\xfb\xfb\xfb\xff\xfc\xfc\xfc\xff\xea\xea\xea\xff\xf2\xf2\xf2\xff\xf6\xf6\xf6\xff\xdc\xdc\xdc\xff^^_\xff\x06\x06\x06\xff}}\x7f' + \
        b'\xff112\xff\x1d\x1d\x1e\xff\xd4\xd4\xd4\xff\xf9\xf9\xf9\xffffh\xff\xbf\xbf\xc0\xff\x82\x82\x83\xff\x81\x81\x82\xff\xf3\xf3\xf3\xff\x86' + \
        b'\x86\x87\xff\x9f\x9f\xa0\xff\xa6\xa6\xa7\xff..0\xff\xbb\xbb\xbc\xff\xaf\xaf\xb0\xff\x84\x84\x85\xff}}~\xff\xb0\xb0\xb1\xff\xff\xff\xff' + \
        b'\xff\xe8\xe8\xe8\xff\x8f\x8f\x90\xff\xbd\xbd\xbd\xffCCE\xff\x97\x97\x98\xff\xa4\xa4\xa5\xff==@\xff\x9b\x9b\x9c\xffvvw\xff\xe2\xe2\xe2' + \
        b'\xff\xde\xde\xdf\xff&&(\xff##%\xff\r\r\x0f\xffCCE\xff\xf6\xf6\xf6\xff\xf6\xf6\xf6\xffNNN\xffKKL\xffDDE\xffAAA\xffxxy\xffyyz\xff\x0e\x0e' + \
        b'\x10\xffBBD\xff--.\xff\x9c\x9c\x9c\xff\x90\x90\x91\xff\\\\\\\xffssu\xff113\xff\xdf\xdf\xdf\xff\x83\x83\x84\xff##%\xff\x9d\x9d\x9e\xffJJK' + \
        b'\xff\x0e\x0e\x10\xff\x0e\x0e\x0f\xff::;\xff\x98\x98\x99\xff<<>\xff\xd3\xd3\xd3\xff\xfc\xfc\xfc\xffOOP\xff\x00\x00\x00\xff\x00\x00\x00' + \
        b'\xffJJL\xff\xf9\xf9\xf9\xff\xf5\xf5\xf5\xffOOQ\xff889\xffUUV\xff557\xffUUU\xffzz{\xff\x05\x05\x06\xff\x80\x80\x81\xffRRT\xff\x81\x81\x82' + \
        b'\xff\xaf\xaf\xb0\xff\xa1\xa1\xa2\xff\xec\xec\xec\xffFFH\xffiij\xff../\xff\x8f\x8f\x90\xff\x98\x98\x99\xff\x1d\x1d\x1f\xff\x0c\x0c\x0e\xff' + \
        b'\x0c\x0c\x0e\xff\x1e\x1e!\xff\x90\x90\x91\xff\xb6\xb6\xb7\xff\xf0\xf0\xf0\xff\xfb\xfb\xfb\xffSSU\xff\x00\x00\x00\xff\x00\x00\x00\xffJJL\xff' + \
        b'\xfb\xfb\xfb\xff\xd1\xd1\xd2\xff++.\xff[[]\xffGGI\xff446\xffsst\xffBBC\xff((*\xff,,.\xff\x07\x07\n\xff\x1a\x1a\x1d\xff\xce\xce\xcf\xff\xff' + \
        b'\xff\xff\xff\xff\xff\xff\xff\x9e\x9e\x9f\xff\x0b\x0b\r\xff;;<\xff\xec\xec\xec\xff\xd1\xd1\xd1\xff\\\\^\xffUUW\xffdde\xffxxy\xff\xbf\xbf\xc0' + \
        b'\xffssu\xff\xe7\xe7\xe7\xff\xfc\xfc\xfc\xffSST\xff\x00\x00\x00\xff\x00\x00\x00\xffJJL\xff\xfc\xfc\xfd\xff\xaf\xaf\xaf\xff\x11\x11\x13\xffiik' + \
        b'\xffiik\xff224\xff||~\xffZZ\\\xff88:\xffIIK\xff446\xffNNO\xff\xe8\xe8\xe8\xff\xff\xff\xff\xff\xff\xff\xff\xff\xcd\xcd\xcd\xff\x11\x11\x12' + \
        b'\xff\x85\x85\x86\xff\xff\xff\xff\xff\xd8\xd8\xd8\xff99;\xff\x0f\x0f\x11\xff\x15\x15\x18\xff447\xff\xba\xba\xba\xffKKL\xff\xd9\xd9\xd9\xff' + \
        b'\xfd\xfd\xfd\xffSST\xff\x00\x00\x00\xff\x00\x00\x00\xffJJL\xff\xfa\xfa\xfb\xff\xda\xda\xdb\xff++-\xff335\xff\x19\x19\x1b\xff\x0f\x0f\x10' + \
        b'\xff:::\xff--/\xff\x00\x00\x02\xff\\\\^\xffppq\xffTTU\xff\xf8\xf8\xf8\xff\xff\xff\xff\xff\xff\xff\xff\xff\xda\xda\xda\xff##%\xff\xb9\xb9' + \
        b'\xb9\xff\xff\xff\xff\xff\xc8\xc8\xc8\xff@@A\xff\x04\x04\x06\xff\x04\x04\x05\xff::<\xff\xa5\xa5\xa6\xff335\xff\xcc\xcc\xcc\xff\xfd\xfd\xfd' + \
        b'\xffSST\xff\x00\x00\x00\xff\x00\x00\x00\xffJJL\xff\xf9\xf9\xf9\xff\xfd\xfd\xfd\xffdde\xffGGI\xff\x1e\x1e\x1f\xffCCE\xff||~\xffmmn\xff==>' + \
        b'\xffbbd\xff\x0c\x0c\x0e\xff../\xff\xea\xea\xea\xff\xff\xff\xff\xff\xff\xff\xff\xff\xdd\xdd\xdd\xff///\xff\xc9\xc9\xc9\xff\xff\xff\xff\xff' + \
        b'\xc4\xc4\xc5\xff\x1f\x1f \xff\x1f\x1f \xff!!"\xff""#\xff\xa3\xa3\xa4\xff99;\xff\xcb\xcb\xcc\xff\xfd\xfd\xfd\xffSST\xff\x00\x00\x00\xff\x00' + \
        b'\x00\x00\xffJJL\xff\xf9\xf9\xf9\xff\xff\xff\xff\xff\xcb\xcb\xcb\xff\xbb\xbb\xbb\xff\xa2\xa2\xa3\xff\xe4\xe4\xe4\xff\xff\xff\xff\xff\xcf\xcf' + \
        b'\xcf\xff\xa7\xa7\xa7\xff\xce\xce\xcf\xff\x89\x89\x8b\xff\xa0\xa0\xa1\xff\xf5\xf5\xf5\xff\xff\xff\xff\xff\xff\xff\xff\xff\xec\xec\xec\xff\x8b' + \
        b'\x8b\x8c\xff\xe2\xe2\xe2\xff\xff\xff\xff\xff\xf8\xf8\xf8\xff\xaf\xaf\xb0\xff\xa2\xa2\xa3\xff\xa4\xa4\xa5\xff\xaf\xaf\xaf\xff\xf0\xf0\xf1\xff' + \
        b'\xce\xce\xce\xff\xf2\xf2\xf3\xff\xfb\xfb\xfc\xffSST\xff\x00\x00\x00\xff\x00\x00\x00\xffIIJ\xff\xf3\xf3\xf4\xff\xfa\xfa\xfa\xff\xfb\xfb\xfb' + \
        b'\xff\xfc\xfc\xfc\xff\xfc\xfc\xfd\xff\xfb\xfb\xff\xff\xfa\xfa\xfe\xff\xfa\xfa\xfe\xff\xfb\xfb\xff\xff\xfb\xfb\xfd\xff\xfd\xfd\xfe\xff\xfd\xfd' + \
        b'\xff\xff\xfa\xfa\xfe\xff\xfa\xfa\xfe\xff\xfa\xfa\xfe\xff\xfa\xfa\xfe\xff\xfb\xfb\xff\xff\xfa\xfa\xfe\xff\xf9\xf9\xfa\xff\xfa\xfa\xfa\xff\xfc' + \
        b'\xfc\xfc\xff\xfb\xfb\xfb\xff\xfb\xfb\xfb\xff\xfc\xfc\xfc\xff\xfa\xfa\xfa\xff\xfc\xfc\xfc\xff\xfa\xfa\xfa\xff\xf5\xf5\xf5\xffRRS\xff\x00\x00' + \
        b'\x00\xff\x00\x00\x02\xff\x17\x17\x18\xffMMK\xffOOM\xffNOM\xffNNM\xffPPX\xff^\\\xc6\xffeb\xf5\xffdb\xf2\xffeb\xf5\xff][\xb7\xffRQe\xffa_\xdc' + \
        b'\xffeb\xf3\xffdb\xf2\xffdb\xf2\xffeb\xf3\xffeb\xf5\xff_]\xcd\xffPPY\xffNOM\xffNOM\xffOOM\xffOOM\xffNOM\xffNOM\xffNOM\xffOOM\xffMML\xff\x1a\x1a' + \
        b'\x1b\xff\x00\x00\x02\xff\x01\x01\x03\xff\x01\x01\x10\xff\x04\x031\xff\x04\x032\xff\x04\x032\xff\x04\x032\xff\x01\x01\x18\xff\x07\x06B\xff\x1d' + \
        b'\x19\xd9\xff \x1c\xee\xff \x1d\xef\xff\x19\x16\xbe\xff\x03\x02\x1a\xff\x15\x12\xa1\xff \x1d\xf0\xff \x1c\xec\xff \x1c\xec\xff\x1d\x19\xd8\xff' + \
        b'\x1f\x1b\xe7\xff\x12\x0f\x88\xff\x00\x00\n\xff\x03\x03.\xff\x04\x032\xff\x04\x032\xff\x04\x032\xff\x04\x032\xff\x04\x032\xff\x04\x032\xff\x04' + \
        b'\x032\xff\x04\x031\xff\x01\x01\x12\xff\x01\x01\x03\xff\x01\x01\x00\xff\n\tC\xff!\x1d\xdb\xff"\x1e\xdf\xff"\x1e\xdf\xff"\x1e\xe1\xff\x1a\x18' + \
        b'\xb1\xff\x04\x04\x1d\xff\x10\x0ej\xff#\x1f\xe9\xff$ \xee\xff"\x1f\xe4\xff\t\x08<\xff\x0f\rb\xff$ \xed\xff$ \xed\xff$ \xec\xff\x18\x16\xa2\xff' + \
        b'\x1e\x1b\xc8\xff\x0b\nK\xff\n\tF\xff!\x1d\xda\xff"\x1e\xdf\xff"\x1e\xdf\xff"\x1e\xdf\xff"\x1e\xdf\xff"\x1e\xdf\xff"\x1e\xdf\xff"\x1e\xdf\xff!' + \
        b'\x1e\xdc\xff\x0b\nK\xff\x01\x01\x00\xff\x01\x01\x00\xff\n\tH\xff#\x1f\xe9\xff$ \xee\xff$ \xee\xff$ \xed\xff$ \xef\xff\x16\x14\x94\xff\x03\x03' + \
        b'\x17\xff\x16\x14\x95\xff#\x1f\xe8\xff!\x1e\xdc\xff\x12\x10w\xff\x06\x06-\xff!\x1d\xd9\xff$ \xee\xff$ \xed\xff# \xec\xff\x1e\x1b\xc9\xff\x04\x04' + \
        b'\x1e\xff\x14\x12\x89\xff$!\xf2\xff$!\xf1\xff$ \xef\xff$ \xee\xff$ \xee\xff$ \xee\xff$ \xee\xff$ \xee\xff# \xeb\xff\x0c\nP\xff\x01\x01\x00\xff' + \
        b'\x01\x01\x00\xff\n\tG\xff#\x1f\xe8\xff$ \xed\xff$ \xed\xff#\x1f\xe9\xff\x1a\x17\xab\xff\x11\x0fq\xff\x04\x03\x1a\xff\x05\x05$\xff\x1b\x18\xb4' + \
        b'\xff\x19\x16\xa5\xff\x1a\x18\xb0\xff\x03\x03\x17\xff\x1a\x17\xab\xff$ \xf0\xff$ \xec\xff$!\xf1\xff\x16\x14\x95\xff\x04\x03\x1a\xff\x1d\x1a\xc0' + \
        b'\xff!\x1e\xdd\xff\x1c\x19\xbb\xff \x1c\xd3\xff$ \xef\xff$ \xed\xff$ \xec\xff$ \xec\xff$ \xed\xff#\x1f\xea\xff\x0c\nO\xff\x01\x01\x00\xff\x01' + \
        b'\x01\x00\xff\n\tG\xff#\x1f\xe8\xff$ \xed\xff$ \xed\xff$ \xf0\xff!\x1d\xda\xff\x13\x11\x83\xff\x04\x03\x1a\xff\x05\x04!\xff\x1f\x1c\xce\xff# ' + \
        b'\xec\xff!\x1d\xdb\xff\x07\x06.\xff\x11\x0fn\xff$!\xf2\xff$ \xee\xff!\x1e\xdd\xff\x0c\x0bQ\xff\x03\x03\x14\xff\x0c\x0bQ\xff\x07\x061\xff\x05' + \
        b'\x04!\xff\t\x08?\xff\x17\x14\x9a\xff"\x1f\xe5\xff$ \xee\xff$ \xed\xff$ \xed\xff#\x1f\xea\xff\x0c\nO\xff\x01\x01\x00\xff\x01\x01\x00\xff\n\tG' + \
        b'\xff#\x1f\xe8\xff$ \xee\xff"\x1e\xe2\xff\x1b\x18\xb3\xff\x19\x16\xa7\xff\x19\x16\xa8\xff\x08\x079\xff\x0c\nO\xff#\x1f\xe9\xff$ \xed\xff$ \xed' + \
        b'\xff\x0f\rf\xff\x07\x06.\xff\x17\x15\x9a\xff\x10\x0ek\xff\x08\x076\xff\x03\x02\x14\xff\x06\x05\'\xff\x0c\x0bS\xff\x15\x12\x8b\xff\x1d\x1a\xbf' + \
        b'\xff\x1a\x17\xae\xff\n\tI\xff\x0c\nV\xff\x1f\x1c\xd0\xff$ \xee\xff$ \xed\xff#\x1f\xea\xff\x0c\nO\xff\x01\x01\x00\xff\x01\x01\x00\xff\n\tG' + \
        b'\xff#\x1f\xe8\xff$ \xed\xff#\x1f\xe8\xff\x1a\x17\xac\xff\n\tC\xff\x01\x01\x0c\xff\x00\x00\x05\xff\x15\x13\x8d\xff$!\xf1\xff$ \xed\xff$!\xf1' + \
        b'\xff\x17\x15\x9b\xff\x01\x01\x05\xff\x00\x00\x04\xff\x00\x00\x00\xff\n\tE\xff\x1b\x18\xb0\xff!\x1d\xd9\xff"\x1e\xe4\xff\x1e\x1b\xcf\xff\x17' + \
        b'\x14\x9f\xff\x10\x0eh\xff\x0f\x0e3\xff\x15\x15\x14\xff\x12\x10u\xff$ \xee\xff$ \xed\xff#\x1f\xea\xff\x0c\nO\xff\x01\x01\x00\xff\x01\x01\x00' + \
        b'\xff\n\tG\xff#\x1f\xe8\xff$ \xed\xff# \xea\xff# \xeb\xff!\x1d\xd9\xff\x11\x0ft\xff\x04\x04\x1d\xff\x1d\x19\xbe\xff"\x1f\xe4\xff$ \xee\xff!' + \
        b'\x1d\xda\xff\x0b\nJ\xff\x07\x060\xff\x0e\x0c^\xff\x0c\nO\xff\x07\x06/\xff\x15\x13\x8c\xff\x14\x11\x86\xff\x11\x10Q\xff\x1b\x1b5\xff115\xffNNK' + \
        b'\xffeeb\xffcc^\xff\x10\x0f>\xff!\x1e\xde\xff$ \xee\xff#\x1f\xea\xff\x0c\nO\xff\x01\x01\x00\xff\x01\x01\x00\xff\n\tG\xff#\x1f\xe8\xff$ \xee' + \
        b'\xff \x1d\xd6\xff\x13\x11}\xff\x0c\x0bS\xff\t\x08<\xff\x07\x062\xff\x1d\x19\xbd\xff\x17\x15\x9c\xff$ \xef\xff\x15\x13\x8f\xff\x08\x076\xff' + \
        b'\x13\x10|\xff\x11\x0fo\xff\x11\x0fp\xff\x10\x0ek\xff\x02\x01\r\xff\x00\x00\x00\xff((&\xffjjg\xff^^b\xffHG\\\xff/.a\xff\x1e\x1cy\xff\x0f\r[' + \
        b'\xff \x1d\xd4\xff$ \xee\xff#\x1f\xea\xff\x0c\nO\xff\x01\x01\x00\xff\x01\x01\x00\xff\n\tG\xff#\x1f\xe8\xff$ \xed\xff$ \xec\xff\x1f\x1c\xd1' + \
        b'\xff\x11\x0fs\xff\x03\x03\x18\xff\x02\x02\x0f\xff\x1a\x17\xad\xff#\x1f\xe6\xff$ \xef\xff\x11\x0fn\xff\x0f\ra\xff\x11\x0fp\xff!\x1d\xd9\xff' + \
        b'\x1b\x18\xb1\xff\x17\x14\x99\xff\x06\x05%\xff\x02\x02\x11\xff\x11\x10A\xff!\x1fy\xff\x19\x17\x9d\xff\x1b\x18\xc4\xff\x1f\x1c\xda\xff\x1e\x1b' + \
        b'\xcc\xff\x13\x10}\xff \x1c\xd3\xff$ \xee\xff#\x1f\xea\xff\x0c\nO\xff\x01\x01\x00\xff\x01\x01\x00\xff\n\tG\xff#\x1f\xe8\xff$ \xed\xff#\x1f\xe7' + \
        b'\xff\x1e\x1b\xca\xff\x1d\x1a\xc0\xff\x16\x13\x92\xff\x06\x05)\xff\x0f\rb\xff$ \xec\xff$ \xf0\xff\x15\x13\x8c\xff\x0e\x0c^\xff\x1c\x19\xba' + \
        b'\xff$ \xed\xff$!\xf1\xff\x1d\x1a\xc3\xff\x0b\nK\xff\x1b\x18\xb6\xff"\x1e\xe3\xff#\x1f\xed\xff$!\xf2\xff%!\xf4\xff \x1c\xd2\xff\x0b\tH\xff\x0e' + \
        b'\x0c]\xff"\x1e\xdf\xff$ \xee\xff#\x1f\xea\xff\x0c\nO\xff\x01\x01\x00\xff\x01\x01\x00\xff\n\tG\xff#\x1f\xe8\xff$ \xed\xff#\x1f\xe7\xff\x19\x16' + \
        b'\xa6\xff\n\tC\xff\x03\x03\x18\xff\x01\x01\x0b\xff\x05\x05#\xff\x1c\x19\xb8\xff\x19\x16\xa7\xff \x1c\xd4\xff\x0e\r`\xff\x18\x15\xa0\xff!\x1d\xd8' + \
        b'\xff\x1e\x1b\xca\xff\x15\x12\x8a\xff\x1b\x18\xb4\xff\x1d\x1a\xb7\xff\x1f\x1c\xca\xff#\x1f\xe8\xff\x1f\x1c\xd1\xff\x18\x15\xa0\xff\x0e\r`\xff\t' + \
        b'\x08:\xff\x1c\x19\xb9\xff$ \xee\xff$ \xed\xff#\x1f\xea\xff\x0c\nO\xff\x01\x01\x00\xff\x01\x01\x00\xff\n\tG\xff#\x1f\xe8\xff$ \xed\xff$ \xed\xff$ ' + \
        b'\xee\xff \x1c\xd4\xff\x13\x10|\xff\x05\x04 \xff\x00\x00\x03\xff\x10\x0el\xff\x1e\x1a\xc5\xff$ \xf0\xff \x1c\xd4\xff\x16\x13\x91\xff\x14\x12\x88' + \
        b'\xff\x17\x14\x98\xff\x1d\x1a\xc4\xff\x14\x12u\xff\x1b\x1b(\xff\x15\x14^\xff\x11\x0fv\xff\n\tD\xff\x0f\rc\xff\x17\x15\x9c\xff \x1d\xd5\xff$ \xee' + \
        b'\xff$ \xed\xff$ \xed\xff#\x1f\xea\xff\x0c\nO\xff\x01\x01\x00\xff\x00\x00\x00\xff\x0b\tH\xff#\x1f\xe8\xff$ \xed\xff$ \xed\xff$ \xed\xff$ \xee\xff$ ' + \
        b'\xee\xff\x1e\x1b\xc7\xff\x0f\re\xff\x04\x03\x1b\xff\x0c\nN\xff\x1c\x19\xbc\xff$ \xef\xff \x1c\xd3\xff"\x1e\xdf\xff!\x1e\xdf\xff\x1f\x1c\xd1\xff' + \
        b'\x1d\x1a\xc0\xff\x19\x17\x93\xff\x0e\x0cZ\xff\n\tE\xff\x1d\x1a\xc1\xff# \xec\xff$ \xf0\xff$ \xee\xff$ \xed\xff$ \xed\xff$ \xed\xff#\x1f\xea\xff' + \
        b'\x0c\nP\xff\x01\x01\x00\xff\x10\x11\x0f\xff\t\x08@\xff"\x1f\xe5\xff$ \xed\xff$ \xed\xff$ \xed\xff$ \xed\xff$ \xed\xff$ \xef\xff# \xeb\xff\x1b\x18' + \
        b'\xb4\xff\x0b\nL\xff\x05\x04#\xff\x12\x10y\xff\x16\x13\x8f\xff\x1a\x17\xab\xff\x13\x10}\xff\x06\x06,\xff\x0f\rg\xff\x10\x0ek\xff\x0b\tH\xff\x1e\x1b' + \
        b'\xc9\xff$ \xf0\xff$ \xed\xff$ \xed\xff$ \xed\xff$ \xed\xff$ \xed\xff$ \xed\xff#\x1f\xe9\xff\x0b\nK\xff\x01\x01\x00\xff;;:\xff\x02\x02\x1a\xff\x1e' + \
        b'\x1a\xc5\xff$!\xf1\xff$ \xed\xff$ \xed\xff$ \xed\xff$ \xed\xff$ \xed\xff$ \xed\xff$ \xf0\xff"\x1f\xe5\xff\x18\x15\x9e\xff\t\x08=\xff\x08\x077\xff' + \
        b'\x0b\nK\xff\x0f\rd\xff\x16\x13\x90\xff\x18\x15\x9e\xff\x13\x11}\xff\x1e\x1b\xc9\xff$ \xf0\xff$ \xed\xff$ \xed\xff$ \xed\xff$ \xed\xff$ \xed\xff$ ' + \
        b'\xed\xff$!\xf0\xff\x1f\x1c\xce\xff\x04\x03#\xff&&&\xff\x8f\x8f\x90\xff\t\t\n\xff\x0b\tL\xff\x1e\x1b\xc7\xff#\x1f\xe7\xff#\x1f\xe8\xff#\x1f\xe8\xff#' + \
        b'\x1f\xe8\xff#\x1f\xe8\xff#\x1f\xe8\xff#\x1f\xe8\xff#\x1f\xe9\xff$ \xeb\xff \x1d\xd6\xff\x1c\x19\xb9\xff \x1d\xd4\xff#\x1f\xe7\xff$ \xec\xff$ \xec' + \
        b'\xff# \xeb\xff# \xe9\xff#\x1f\xe8\xff#\x1f\xe8\xff#\x1f\xe8\xff#\x1f\xe8\xff#\x1f\xe8\xff#\x1f\xe8\xff#\x1f\xe7\xff\x1f\x1b\xcc\xff\x0c\x0bV\xff' + \
        b'\x06\x06\x07\xff\x88\x88\x89\xff\xf2\xf2\xf2\xffrrs\xff\x08\x08\t\xff\x02\x02\x1d\xff\t\x08C\xff\x0b\tH\xff\n\tG\xff\n\tG\xff\n\tG\xff\n\tG\xff\n' + \
        b'\tG\xff\n\tG\xff\n\tG\xff\x0b\tH\xff\x0b\nJ\xff\x0b\tH\xff\n\tG\xff\n\tG\xff\n\tG\xff\n\tG\xff\n\tG\xff\n\tG\xff\n\tG\xff\n\tG\xff\n\tG\xff\n\tG' + \
        b'\xff\x0b\tG\xff\n\tD\xff\x03\x03 \xff\x04\x04\x06\xffZZ\\\xff\xe9\xe9\xe9\xff\xff\xff\xff\xff\xf2\xf2\xf2\xff\x8b\x8b\x8c\xff000\xff\t\t\t\xff' + \
        b'\x00\x00\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff' + \
        b'\x01\x01\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff' + \
        b'\x01\x01\x00\xff\x01\x01\x00\xff\x01\x01\x00\xff\x00\x00\x00\xff\x04\x04\x03\xff,,,\xff\x87\x87\x89\xff\xe9\xe9\xe9\xff\xff\xff\xff\xff\x00\x00' + \
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + \
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + \
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' + \
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'


class AppConf:

    def __init__(self) -> None:
        pass

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
