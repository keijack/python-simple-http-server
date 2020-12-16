# python-simple-http-server

[![PyPI version](https://badge.fury.io/py/simple-http-server.png)](https://badge.fury.io/py/simple-http-server)

## Discription

This is a simple http server, use MVC like design.

## Support Python Version

Python 3.7+

from `0.4.0`, python 2.7 is no longer supported, if you are using python 2.7, please use version `0.3.1`

## Why choose

* Lightway.
* Functional programing.
* Filter chain support.
* Session support.
* Spring MVC like request mapping.
* SSL support.
* Easy to use.
* Free style controller writing.

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
from simple_http_server import Headers
from simple_http_server import Cookies
from simple_http_server import Cookie
from simple_http_server import Redirect


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

@request_map("/upload", method="GET")
def show_upload():
    root = os.path.dirname(os.path.abspath(__file__))
    return StaticFile("%s/my_dev/my_test_index.html" % root, "text/html; charset=utf-8")

@request_map("/upload", method="POST")
def my_upload(img=MultipartFile("img")):
    root = os.path.dirname(os.path.abspath(__file__))
    img.save_to_file(root + "/my_dev/imgs/" + img.filename)
    return "<!DOCTYPE html><html><body>upload ok!</body></html>"


@request_map("/post_txt", method="POST")
def normal_form_post(txt):
    return "<!DOCTYPE html><html><body>hi, %s</body></html>" % txt

@request_map("/tuple")
def tuple_results():
    # The order here is not important, we consider the first `int` value as status code,
    # All `Headers` object will be sent to the response
    # And the first valid object whose type in (str, unicode, dict, StaticFile, bytes) will
    # be considered as the body
    return 200, Headers({"my-header": "headers"}), {"success": True}

"""
" Cookie_sc will not be written to response. It's just some kind of default
" value
"""
@request_map("tuple_cookie")
def tuple_with_cookies(all_cookies=Cookies(), cookie_sc=Cookie("sc")):
    print("=====> cookies ")
    print(all_cookies)
    print("=====> cookie sc ")
    print(cookie_sc)
    print("======<")
    import datetime
    expires = datetime.datetime(2018, 12, 31)

    cks = Cookies()
    # cks = cookies.SimpleCookie() # you could also use the build-in cookie objects
    cks["ck1"] = "keijack"
    cks["ck1"]["path"] = "/"
    cks["ck1"]["expires"] = expires.strftime(Cookies.EXPIRE_DATE_FORMAT)
    # You can ignore status code, headers, cookies even body in this tuple.
    return Header({"xx": "yyy"}), cks, "<html><body>OK</body></html>"

"""
" If you visit /a/b/xyz/x，this controller function will be called, and `path_val` will be `xyz`
"""
@request_map("/a/b/{path_val}/x")
def my_path_val_ctr(path_val=PathValue()):
    return "<html><body>%s</body></html>" % path_val


@request_map("/redirect")
def redirect():
    return Redirect("/index")

@request_map("session")
def test_session(session=Session(), invalid=False):
    ins = session.get_attribute("in-session")
    if not ins:
        session.set_attribute("in-session", "Hello, Session!")

    __logger.info("session id: %s" % session.id)
    if invalid:
        __logger.info("session[%s] is being invalidated. " % session.id)
        session.invalidate()
    return "<!DOCTYPE html><html><body>%s</body></html>" % str(ins)
```

Beside using the default values, you can also use variable annotations to specify your controller function's variables.

```python
@request_map("/say_hello/to/{name}", method=["GET", "POST", "PUT"])
def your_ctroller_function(
        user_name: str, # req.parameter["user_name"]，400 error will raise when there's no such parameter in the query string.
        password: str, # req.parameter["password"]，400 error will raise when there's no such parameter in the query string.
        skills: list, # req.parameters["skills"]，400 error will raise when there's no such parameter in the query string.
        all_headers: Headers, # req.headers
        user_token: Header, # req.headers["user_token"]，400 error will raise when there's no such parameter in the quest headers.
        all_cookies: Cookies, # req.cookies, return all cookies
        user_info: Cookie, # req.cookies["user_info"]，400 error will raise when there's no such parameter in the cookies.
        name: PathValue, # req.path_values["name"]，get the {name} value from your path.
        session: Session # req.getSession(True)，get the session, if there is no sessions, create one.
    ):
    return "<html><body>Hello, World!</body></html>"
```

### Write filters

```python
from simple_http_server import filter_map

# Please note filter will map a regular expression, not a concrect url.
@filter_map("^/tuple")
def filter_tuple(ctx):
    print("---------- through filter ---------------")
    # add a header to request header
    ctx.request.headers["filter-set"] = "through filter"
    if "user_name" not in ctx.request.parameter:
        ctx.response.send_redirect("/index")
    elif "pass" not in ctx.request.parameter:
        ctx.response.send_error(400, "pass should be passed")
        # you can also raise a HttpError
        # raise HttpError(400, "pass should be passed")
    else:
        # you should always use do_chain method to go to the next
        ctx.do_chain()
```

### Start your server

```python
# If you place the controllers method in the other files, you should import them here.

import simple_http_server.server as server
import my_test_ctrl


def main(*args):
    # The following method can import several controller files once.
    server.scan("my_ctr_pkg", r".*controller.*")
    server.start()

if __name__ == "__main__":
    main()
```

If you want to specify the host and port:

```python
    server.start(host="", port=8080)
```

If you want to specify the resources path: 

*Notice: `/path_prefix/`/`/path_prefix/*`/`/path_prefix/**` is the same effect.*

```python 
    server.start(resources={"/path_prefix/*", "/absolute/dir/root/path",
                            "/path_prefix/*", "/absolute/dir/root/path"})
```

If you want to use ssl:

```python
    server.start(host="", 
                 port=8443,
                 ssl=True,
                 ssl_protocol=ssl.PROTOCOL_TLS_SERVER, # Optional, default is ssl.PROTOCOL_TLS_SERVER, which will auto detect the highted protocol version that both server and client support. 
                 ssl_check_hostname=False, #Optional, if set to True, if the hostname is not match the certificat, it cannot establish the connection, default is False.
                 keyfile="/path/to/your/keyfile.key",
                 certfile="/path/to/your/certfile.cert",
                 keypass="", # Optional, your private key's password
                 )
```

## Logger

The default logger is try to write logs to the screen, you can specify the logger handler to write it to a file.

```python
import simple_http_server.logger as logger
import logging

_formatter = logging.Formatter(fmt='[%(asctime)s]-[%(name)s]-%(levelname)-4s: %(message)s')
_handler = logging.TimedRotatingFileHandler("/var/log/simple_http_server.log", when="midnight", backupCount=7)
_handler.setFormatter(_formatter)
_handler.setLevel("INFO")

logger.set_handler(_handler)
```

If you want to add a handler rather than replace the inner one, you can use:

```python
logger.add_handler(_handler)
```

If you want to change the logger level:

```python
logger.set_level("DEBUG")
```

This logger will first save all the log record to a global queue, and then output them in a background thread, so it is very suitable for getting several logger with a same handler, especialy the `TimedRotatingFileHandler` which may slice the log files not quite well in a mutiple thread environment. 

## Problems

### Multipul threading safety

For this is a SIMPLE http server, I have not done much work to ensure multipul threading safety. It may cause some problem if you trid to write data to `Request` and `Response` objects in multipul threads in one request scope (including in filters and controller functions).