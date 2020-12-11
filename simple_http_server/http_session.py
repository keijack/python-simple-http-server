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
import sched
import time

from typing import Any, Dict, Tuple
from threading import RLock
from simple_http_server import _Session, Session
from simple_http_server.logger import get_logger

_logger = get_logger("http_session")

_SESSION_TIME_CLEANING_INTERVAL = 60

SESSION_COOKIE_NAME: str = "PY_SIM_HTTP_SER_SESSION_ID"


class SessionFactory:

    def clean_session(self, session_id: str):
        pass

    def get_session(self, session_id: str, create: bool = False) -> Session:
        return None


class LocalSessionImpl(_Session):

    def __init__(self, id: str, creation_time: float, session_fac: SessionFactory):
        super().__init__(id, creation_time)
        self.__attr_lock = RLock()
        self.__attrs = {}
        self.__ses_fac = session_fac

    @property
    def attribute_names(self) -> Tuple:
        return tuple(self.__attrs.keys())

    def get_attribute(self, name: str) -> Any:
        with self.__attr_lock:
            if name in self.__attrs:
                return self.__attrs[name]
            return None

    def set_attribute(self, name: str, value: Any) -> None:
        with self.__attr_lock:
            self.__attrs[name] = value

    def invalidate(self) -> None:
        self._set_last_acessed_time(0)
        self.__ses_fac.clean_session(session_id=self.id)


class LocalSessionFactory(SessionFactory):

    def __init__(self):
        self.__sessions: Dict[str, _Session] = {}
        self.__session_lock = RLock()
        self.__started = False
        self.__clearing_thread = threading.Thread(target=self._clear_time_out_session_in_bg, daemon=True)

    def _start_cleaning(self):
        if not self.__started:
            self.__started = True
            self.__clearing_thread.start()

    def _create_local_session(self) -> Session:
        sid = uuid.uuid4().hex
        return LocalSessionImpl(sid, time.time(), self)

    def _clear_time_out_session_in_bg(self):
        while True:
            time.sleep(_SESSION_TIME_CLEANING_INTERVAL)
            self._clear_time_out_sessin()

    def _clear_time_out_sessin(self):
        cl_ids = []
        for k, v in self.__sessions.items():
            if not v.is_valid:
                cl_ids.append(k)
        for k in cl_ids:
            self.clean_session(k)

    def clean_session(self, session_id: str):
        with self.__session_lock:
            if session_id in self.__sessions:
                del self.__sessions[session_id]

    def get_session(self, session_id: str, create: bool = False) -> Session:
        with self.__session_lock:
            sid = session_id
            if (not sid or sid not in self.__sessions) and not create:
                return None

            if (not sid or sid not in self.__sessions):
                session = self._create_local_session()
                self.__sessions[session.id] = session
            else:
                session = self.__sessions[sid]
                if not session.is_valid:
                    _logger.debug("session is not valid, create new one.")
                    del self.__sessions[sid]
                    session = self._create_local_session()
                    self.__sessions[session.id] = session
                else:
                    session._set_last_acessed_time(time.time())

            self._start_cleaning()

            return session


session_factory = LocalSessionFactory()


def get_session(session_id: str, create: bool = False) -> Session:
    return session_factory.get_session(session_id, create)
