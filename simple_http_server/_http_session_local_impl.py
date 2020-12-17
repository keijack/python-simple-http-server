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

import threading
import uuid
import time

from typing import Any, Dict, Tuple
from threading import RLock
from simple_http_server import Session, SessionFactory, set_session_factory
from simple_http_server.logger import get_logger

_logger = get_logger("http_session")

_SESSION_TIME_CLEANING_INTERVAL = 60

SESSION_COOKIE_NAME: str = "PY_SIM_HTTP_SER_SESSION_ID"


def _get_from_dict(adict: Dict[str, Any], key: str) -> Any:
    if key not in adict:
        return None
    try:
        return adict[key]
    except KeyError:
        _logger.debug("key %s was deleted in other thread.")
        return None


class LocalSessionImpl(Session):

    def __init__(self, id: str, creation_time: float, session_fac: SessionFactory):
        super().__init__()
        self.__id = id
        self.__creation_time = creation_time
        self.__last_acessed_time = creation_time
        self.__is_new = True
        self.__attr_lock = RLock()
        self.__attrs = {}
        self.__ses_fac = session_fac

    @property
    def id(self) -> str:
        return self.__id

    @property
    def creation_time(self) -> float:
        return self.__creation_time

    @property
    def last_acessed_time(self) -> float:
        return self.__last_acessed_time

    @property
    def is_new(self) -> bool:
        return self.__is_new

    def _set_last_acessed_time(self, last_acessed_time: float):
        self.__last_acessed_time = last_acessed_time
        self.__is_new = False

    @property
    def attribute_names(self) -> Tuple:
        return tuple(self.__attrs.keys())

    def get_attribute(self, name: str) -> Any:
        return _get_from_dict(self.__attrs, name)

    def set_attribute(self, name: str, value: Any) -> None:
        with self.__attr_lock:
            self.__attrs[name] = value

    def invalidate(self) -> None:
        self._set_last_acessed_time(0)
        self.__ses_fac.clean_session(session_id=self.id)


class LocalSessionFactory(SessionFactory):

    def __init__(self):
        self.__sessions: Dict[str, LocalSessionImpl] = {}
        self.__session_lock = RLock()
        self.__started = False
        self.__clearing_thread = threading.Thread(target=self._clear_time_out_session_in_bg, daemon=True)

    def _start_cleaning(self):
        if not self.__started:
            self.__started = True
            self.__clearing_thread.start()

    def _create_local_session(self, session_id: str) -> Session:
        if session_id:
            sid = session_id
        else:
            sid = uuid.uuid4().hex
        return LocalSessionImpl(sid, time.time(), self)

    def _clear_time_out_session_in_bg(self):
        while True:
            time.sleep(_SESSION_TIME_CLEANING_INTERVAL)
            self._clear_time_out_session()

    def _clear_time_out_session(self):
        cl_ids = []
        for k, v in self.__sessions.items():
            if not v.is_valid:
                cl_ids.append(k)
        for k in cl_ids:
            self.clean_session(k)

    def clean_session(self, session_id: str):
        if session_id in self.__sessions:
            try:
                _logger.debug("session[#%s] is being cleaned" % session_id)
                sess = self.__sessions[session_id]
                if not sess.is_valid:
                    del self.__sessions[session_id]
            except KeyError:
                _logger.debug("Session[#%s] in session cache is already deleted. " % session_id)

    def _get_session(self, session_id: str) -> LocalSessionImpl:
        if not session_id:
            return None
        sess: LocalSessionImpl = _get_from_dict(self.__sessions, session_id)
        if sess and sess.is_valid:
            return sess
        else:
            return None

    def get_session(self, session_id: str, create: bool = False) -> Session:
        sess = self._get_session(session_id)
        if sess:
            sess._set_last_acessed_time(time.time())
            return sess
        with self.__session_lock:
            session = self._create_local_session(session_id)
            self.__sessions[session.id] = session

            self._start_cleaning()

            return session


set_session_factory(LocalSessionFactory())
