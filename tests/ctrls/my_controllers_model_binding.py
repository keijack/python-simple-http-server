
from typing import Any
from naja_atra.request_handlers.model_bindings import ModelBinding
from naja_atra import model_binding, default_model_binding
from naja_atra import HttpError, route
from naja_atra.utils.logger import get_logger

_logger = get_logger("my_ctrls_model_bindings")


class Person:

    def __init__(self, name: str = "", sex: int = "", age: int = 0) -> None:
        self.name = name
        self.sex = sex
        self.age = age


class Dog:

    def __init__(self, name="a dog") -> None:
        self.name = name

    def wang(self):
        name = self.name
        if hasattr(self, "name"):
            name = self.name
        _logger.info(f"wang, I'm {name}, with attrs {self.__dict__}")
        return name


@model_binding(Person)
class PersonModelBinding(ModelBinding):

    async def bind(self) -> Any:
        name = self.request.get_parameter("name", "no-one")
        sex = self.request.get_parameter("sex", "secret")
        try:
            age = int(self.request.get_parameter("age", ""))
        except:
            raise HttpError(400, "Age is required, and must be an integer")
        return Person(name, sex, age)


@default_model_binding
class SetAttrModelBinding(ModelBinding):

    def bind(self) -> Any:
        try:
            obj = self.arg_type()
            for k, v in self.request.parameter.items():
                setattr(obj, k, v)
            return obj
        except Exception as e:
            _logger.warning(
                f"Cannot create Object with given type {self.arg_type}. ", stack_info=True)
            return self.default_value


@route("/model_binding/person")
def test_model_binding(person: Person):
    return {
        "name": person.name,
        "sex": person.sex,
        "age": person.age,
    }


@route("/model_binding/dog")
def test_model_binding_dog(dog: Dog):
    return {
        "name": dog.wang()
    }
