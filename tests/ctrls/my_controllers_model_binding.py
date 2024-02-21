
from typing import Any
from simple_http_server.models.model_bindings import ModelBinding
from simple_http_server import model_binding, route
from simple_http_server import HttpError


class Person:

    def __init__(self, name: str = "", sex: int = "", age: int = 0) -> None:
        self.name = name
        self.sex = sex
        self.age = age


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


@route("/model_binding/person")
def test_model_binding(person: Person):
    return {
        "name": person.name,
        "sex": person.sex,
        "age": person.age,
    }
