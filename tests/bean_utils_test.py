# coding: utf-8

import unittest
import json
import simple_http_server.logger as logger
import simple_http_server.bean_utils as bean_utils

logger.set_level("DEBUG")

_logger = logger.get_logger("bean_utils_test")


class Child:

    def __init__(self, cvalue: str = "abcde") -> None:
        self.cvalue = cvalue


class Parent0:

    par_clz_val = "parent class 0"


class Parent:

    par_clz_val = "parent class value"

    def __init__(self):
        self.par_val = "par"

    @property
    def par_pro(self):
        return self.par_val


class Clz(Parent0, Parent):

    clz_field = "clz_val"

    def __init__(self, int_val: int, clz_val: Child, str_kw: str = "default_val", list_kw=[0, "a", Child("in_list")]) -> None:
        super().__init__()
        self.int_val = int_val if int_val else 1
        self.__chi = clz_val
        self.list_kw = list_kw
        self.str_kw = str_kw

    @property
    def int_pro(self) -> int:
        return self.int_val

    @property
    def chi(self) -> Child:
        return self.__chi

    @chi.setter
    def chi(self, val):
        self.__chi = val


class TestCases(unittest.TestCase):

    def test_obj_to_json(self):
        obj = Clz(1, Child("init"))
        json_str = bean_utils.bean_to_json(obj)
        assert_dict = {"clz_field": "clz_val",
                       "int_pro": 1, "chi": {"cvalue": "init"},
                       "par_clz_val": "parent class 0",
                       "par_pro": "par",
                       "par_val": "par",
                       "int_val": 1,
                       "list_kw": [0, "a", {"cvalue": "in_list"}], "str_kw": "default_val"}
        assert json.loads(json_str) == assert_dict

    def test_json_to_dict(self):
        json_str = json.dumps({"clz_field": "clz_val3",
                               "int_val": 0,
                               "par_val": "par2",
                               "list_kw": [0, "a", {"cvalue": "in_list"}]})
        obj: Clz = bean_utils.json_to_bean(json_str, Clz)
        assert obj.clz_field == "clz_val3"
        assert obj.int_val == 0
        assert obj.int_pro == 0
        assert obj.chi.cvalue == "abcde"  # 自动填充的默认值
        assert obj.list_kw[2]["cvalue"] == "in_list"
        assert obj.par_pro == "par2"
