# python-simple-http-server

## Discription

This is a simple http server, use MVC like design.

## Support Python Version

Python 2.7 / 3.6+ (It should also work at 3.5, not test)

## Why choose

* Lightway.
* Filter support.
* Spring(Java) like request mapping.

## How to use

### Install

```Shell
pip install simple_http_server
```

### Write Controllers

```python
from simple_http_server.server import request_map
from simple_http_server.http_server import Response


@request_map("/index")
def my_ctrl(parameters=None,
            json=None,
            **kargs  # This is required, for there are still other key arguments that will set to call this function
            ):

    return {"code": 0, "message": "success"}  # You can return a dictionary, a string or a `simple_http_server.simple_http_server.Response` object.


@request_map("/say_hello", method="GET")
def my_ctrl2(
        parameter={"name": "1"}, # default values, if there are no name parameter in the request, the one here will be use
        parameters={"name": "2"},
        json={"name": "3"},
        **kargs):
    print("parameter name %s " % parameter["name"])
    print("parameters name %s " % str(parameters["name"]))
    print("json name %s " % json["name"])
    return "<!DOCTYPE html><html><body>hello, %s</body></html>" % parameter["name"]


@request_map("/error")
def my_ctrl3(**kargs):
    return Response(status_code=500)


@request_map("/")
def my_ctrl4(response=None,
             **kargs):
    response.send_redirect("/index")

@request_map("/upload", method="POST")
def my_upload(parameter={},
              **kargs):
    root = os.path.dirname(os.path.abspath(__file__))

    img = parameter["img"]  # <input type="file" name="img">
    print(img.filename + " => " + img.content_type)
    img.save_to_file(root + "/my_dev/imgs/" + img.filename)

    return "<!DOCTYPE html><html><body>upload ok!</body></html>"
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