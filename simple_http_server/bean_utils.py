# coding: utf-8

from collections import OrderedDict
import json
import copy
import inspect
from typing import Any, Dict, Type


class ObjectProperties:

    def __init__(self, obj: object) -> None:
        self.__obj = obj
        self.__clz = type(obj)
        self.__load()

    def __load(self):
        self.__class_property_values: Dict[str, Any] = {}
        self.__object_property_values: Dict[str, Any] = {}
        self.__property_values: Dict[str, Any] = {}
        self.__vars = {}
        self.__val_dict = None
        self.__class_property_values: Dict[str, Any] = dict([(name, val) for name, val in vars(self.__clz).items() if not name.startswith("_")])
        self.__object_property_values: Dict[str, Any] = dict([(name, val) for name, val in vars(self.__obj).items() if not name.startswith("_")])
        pros = inspect.getmembers(self.__clz, predicate=inspect.isdatadescriptor)

        pros_list = [(name, pro) for name, pro in pros if not name.startswith("_")]

        for name, pro in pros_list:
            getter = pro.fget
            self.__property_values[name] = getter(self.__obj)

        self.__vars = copy.copy(self.__class_property_values)
        self.__vars.update(self.__object_property_values)
        self.__vars.update(self.__property_values)

        for n, v in self.__vars.items():
            try:
                self.__vars[n] = self.__actual_val(v)
            except:
                pass

    def __actual_val(self, v):
        type_v = type(v)
        if issubclass(type_v, dict):
            res = {}
            for k, val in v.items():
                res[k] = self.__actual_val(val)
            return res
        elif not issubclass(type_v, str) and hasattr(v, "__iter__"):
            arr = []
            it = iter(v)
            while True:
                try:
                    arr.append(self.__actual_val(next(it)))
                except StopIteration:
                    break
            return arr
        elif hasattr(v, "__dict__"):
            return ObjectProperties(v)
        else:
            return v

    @property
    def value_dict(self):
        if self.__val_dict:
            return self.__val_dict
        self.__val_dict = {}
        for n, v in self.__vars.items():
            self.__val_dict[n] = self.__val_to_dict(v)

        return self.__val_dict

    def __val_to_dict(self, v):
        if isinstance(v, dict):
            res = {}
            for k, val in v.items():
                res[k] = self.__val_to_dict(val)
            return res
        elif isinstance(v, list):
            arr = []
            for it in v:
                arr.append(self.__val_to_dict(it))
            return arr
        elif isinstance(v, ObjectProperties):
            return v.value_dict
        else:
            return v

    def fill(self, values: Dict[str, Any]):
        for k, v in values.items():
            if k not in self.__vars:
                continue
            var = self.__vars[k]
            if isinstance(var, ObjectProperties):
                if isinstance(v, dict):
                    var.fill(v)
                else:
                    print(f"warn:{k} should be a object, but now: {v}")
                    self.__set_val(k, v)
            else:
                self.__set_val(k, v)

        self.__load()
        return self.__obj

    def __set_val(self, name, value):
        try:
            setattr(self.__obj, name, value)
        except:
            print(f"Cannot set value to property {name} which may be read only")


def get_function_args(func, default_type=str):
    argspec = inspect.getfullargspec(func)
    # ignore first argument like `self` or `clz` in object methods or class methods
    start = 1 if inspect.ismethod(func) else 0
    if argspec.defaults is None:
        args = argspec.args[start:]
    else:
        args = argspec.args[start: len(argspec.args) - len(argspec.defaults)]
    arg_turples = []
    for arg in args:
        if arg in argspec.annotations:
            ty = argspec.annotations[arg]
        else:
            ty = default_type
        arg_turples.append((arg, ty))
    return arg_turples


def get_function_kwargs(func, default_type=str):
    argspec = inspect.getfullargspec(func)
    if argspec.defaults is None:
        return []

    kwargs = OrderedDict(zip(argspec.args[-len(argspec.defaults):], argspec.defaults))
    kwarg_turples = []
    for k, v in kwargs.items():
        if k in argspec.annotations:
            k_anno = argspec.annotations[k]
        else:
            k_anno = default_type
        kwarg_turples.append((k, v, k_anno))
    return kwarg_turples


def new_instance(bean_type: Type):
    if bean_type is None:
        return None
    if not hasattr(bean_type, "__init__"):
        return None
    args_def = get_function_args(bean_type.__init__, default_type=None)[1:]
    args = []
    for n, t in args_def:
        args.append(new_instance(t))

    return bean_type(*args)


def bean_to_dict(bean: object) -> Dict[str, Any]:
    return ObjectProperties(bean).value_dict


def dict_to_bean(dict: Dict[str, Any], bean_type: Type) -> object:
    obj_pro = ObjectProperties(new_instance(bean_type))
    return obj_pro.fill(dict)


def bean_to_json(bean: object) -> str:
    return json.dumps(bean_to_dict(bean))


def json_to_bean(json_str: str, bean_type: Type) -> object:
    return dict_to_bean(json.loads(json_str), bean_type)
