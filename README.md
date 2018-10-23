# python-simple-http-server

## Discription

This is a simple http server, use MVC like design.

## Support Python Version

Python 2.7 / 3.6+ (It should also work at 3.5, not test)

## Why choose

* Lightway.
* Filter support.
* Spring(Java) like request mapping.

## Change log

### Version 0.1.0 2018-10-23

1, Move all the Interface Class and method to simple_http_server.
2, Change `Controller` method wrting style, it is now more flexiable and spring-like.
3, You can raise a `simple_http_server.HttpError` now to interupt the request process.

## TODOs

* Support path values.

## How to use

### Install

```shell
pip install simple_http_server
```

### Write Controllers

```python
from simple_http_server import request_map
from simple_http_server import Response
from simple_http_server import MultipartFile
from simple_http_server import Parameter
from simple_http_server import Parameters
from simple_http_server import Header
from simple_http_server import JSONBody
from simple_http_server import HttpError


@request_map("/index")
def my_ctrl():
    return {"code": 0, "message": "success"}  # You can return a dictionary, a string or a `simple_http_server.simple_http_server.Response` object.


@request_map("/say_hello", method=["GET", "POST"])
def my_ctrl2(name, name2=Parameter("name", default="KEIJACK")):
    """name and name2 is the same"""
    return "<!DOCTYPE html><html><body>hello, %s, %s</body></html>" % (name, name2)


@request_map("/error")
def my_ctrl3():
    return Response(status_code=500)


@request_map("/exception")
def exception_ctrl():
    raise HttpError(400, "Exception")


@request_map("/upload", method="POST")
def my_upload(img=MultipartFile("img")):
    root = os.path.dirname(os.path.abspath(__file__))

    img.save_to_file(root + "/my_dev/imgs/" + img.filename)

    return "<!DOCTYPE html><html><body>upload ok!</body></html>"


@request_map("/upload", method="GET")
def show_upload():
    root = os.path.dirname(os.path.abspath(__file__))
    with open(root + "/my_dev/my_test_index.html", "r") as html:
        return html.read()
```

### Start your server

```python
# If you place the controllers method in the other files, you should import them here.

import simple_http_server.server as server
import my_test_ctrl


def main(*args):
    server.start()

if __name__ == "__main__":
    main()
```