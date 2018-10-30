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

### Version 0.1.3 2018-10-30

1. Support add header in Response object, you can send several different header value with the same name now.
2. Fix some `utf-8` encoding bug for python 2.7 when using `multipart/form-data`
3. Fix a bug when using a Response object to send back data rather than returning it in controller function.

### Version 0.1.2 2018-10-28

1. You can return a `StaticFile` in the controller function, the response will read the file content and write it to output stream.
2. Add a default `/favicon.ico`.
3. Fix some `utf-8` encoding bug for python 2.7.  

### Version 0.1.1 2018-10-26

1. You can post JSON in a request body now.
2. `request.body` will be the raw data which is byte array in python 3.6 and origianl string in python 2.7 now.

### Version 0.1.0 2018-10-23

1. Move all the Interface Class and method to simple_http_server.
2. Change `Controller` method wrting style, it is now more flexiable and spring-like.
3. You can raise a `simple_http_server.HttpError` now to interupt the request process.

## TODOs

* Support path values.
* Support Cookies.
* Support controller functions returning tuples.

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
from simple_http_server import StaticFile


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


@request_map("/post_txt", method="POST")
def normal_form_post(txt):
    return "<!DOCTYPE html><html><body>hi, %s</body></html>" % txt


@request_map("/upload", method="GET")
def show_upload():
    root = os.path.dirname(os.path.abspath(__file__))
    return StaticFile("%s/my_dev/my_test_index.html" % root, "text/html; charset=utf-8")
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