# python-simple-http-server

[![PyPI version](https://badge.fury.io/py/simple-http-server.png)](https://badge.fury.io/py/simple-http-server)

## 简介

这是一个轻量级的基于 Python http.server 编写的服务器，你可以非常容易的搭建一个 Restful API。其中一些请求的转发等参考了 SpringMVC 的设计。

## 支持的 Python 的版本

Python 3.7

从 `0.4.0` 开始，该项目仅支持 Python 3.7，如果你在使用 Python 2.7，请使用 `0.3.1` 版本。

## 为什么要选择这个项目？

* 轻量级
* 支持过滤器链
* Spring MVC 风格的请求映射配置
* 简单易用
* 支持 SSL
* 编写风格自由

## 安装

```shell
pip install simple_http_server
```

## 编写控制器

### 配置路由信息

我们接下来，将处理请求的函数命名为 **控制器函数（Controller Function）**。

类似 Spring MVC，我们使用描述性的方式来将配置请求的路由（在 Java 中，我们会使用标注 Annotation，而在 Python，我们使用 decorator，两者在使用时非常类似）。

基础的配置如下，该例子中，请求 /index 将会路由到当前的方法中。

```Python
from simple_http_server import request_map

@request_map("/index")
def your_ctroller_function():
    return "<html><body>Hello, World!</body></html>"
```

@request_map 会接收两个参数，第二个参数会指定当前的控制器函数会处理请求中哪些方法(Method)，以下的例子中的方法，仅会处理方法为 GET 的请求。

```Python
@request_map("/say_hello", method="GET")
def your_ctroller_function():
    return "<html><body>Hello, World!</body></html>"
```

method参数同时也可以是一个列表，以下的例子中，该控制器函数会处理方法为 GET、POST、PUT 的请求

```Python
@request_map("/say_hello", method=["GET", "POST", "PUT"])
def your_ctroller_function():
    return "<html><body>Hello, World!</body></html>"
```

匹配路由时，除了指定具体的路径之外，你还可以指定路径的某一段是可变的，这部方可变的部分将会作为路径参数放入请求中，如何取得这些路径参数我们将会在 **取得请求参数** 一节具体说明。@request_map 的配置如下。该配置下，`/say/hello/to/world`，`/say/hello/to/jhon` 等 url 都能访问该控制器方法。

```Python
@request_map("/say_hello/to/{name}", method=["GET", "POST", "PUT"])
def your_ctroller_function():
    return "<html><body>Hello, World!</body></html>"
```

你可以给一个控制器函数增加多个 @request_map

```python
@request_map("/")
@request_map("/index")
def index():
    return "<html><body>Hello, World!</body></html>"
```

### 取的请求中的信息

参考了 Spring MVC 的设计，获取请求方法的方式非常自由。其中最基本的方法是取得 Request 对象，该对象中包含了所有其他方式能够获取的内容。

```Python
from simple_http_server import request_map
from simple_http_server import Request

@request_map("/say_hello/to/{name}", method=["GET", "POST", "PUT"])
def your_ctroller_function(req=Request()):
    """ 请注意关键字参数传入的默认参数是一个 Request 对象，而不是类本身。 """
    ##
    # 该请求的方法，可能是 "OPTIONS", "GET", "HEAD", "POST", "PUT", "DELETE", "TRACE", "CONNECT" 中的一个
    print(req.method)
    ##
    # 该请求的路径，就是 /say/hello/to/xxx
    print(req.path)
    ##
    #  一个 dict 对象，包含了所有的头部参数。
    print(req.headers)
    ##
    # 一个 dict 对象，包含了请求的参数，包括了来源于QueryString与 body 中的参数
    # 该对象仅存储一个参数，如果同一个参数名传入了多个值，该对象只记录第一个值。
    print(req.parameter)
    ##
    # 一个 dict 对象，类似，req.parameter，但该对象包含了所有的参数
    # 该对象的值总是会返回一个列表，即使一个参数名只传入了一个参数。
    print(req.parameters)
    ##
    # 返回 query string
    print(req.query_string)
    ##
    # 返回一个 Cookies 对象，该对象是 http.cookies.SimpleCookie 的子类
    print(req.cookies)
    ##
    # 一个 dict 对象，包含了所有的路径上的参数，本例中是 {"name": "xxx"}
    print(req.path_values)
    ##
    # 请求体部分，在 3.6 中是一个 bytes 对象。2.7 中是一个 str 对象
    print(req.body)
    ##
    # 当你的请求的 Content-Type 是 application/json 时，框架会自动将请求体中的 JSON 对象加载为一个dict对象。
    print(req.json)
    return "<html><body>Hello, World!</body></html>"
```

我们还可以通过更直接的参数和关键字参数来获取请求中的信息，使得编码更加简洁和方便。

```python
from simple_http_server import request_map

@request_map("/say_hello/to/{name}", method=["GET", "POST", "PUT"])
def your_ctroller_function(
        user_name, # 传入 req.parameter["user_name"]，如果该参数为空，则会响应为 400 参数错误
        password, # 传入 req.parameter["password"]，如果参数为空，则会响应为 400 参数错误
        nickName="", # 传入 req.parameter["nickName"]，如果参数为空，则会传入 ""
        age=16, # 传入 int(req.parameter["age"])，如果传入空则传入 16，如果传入的不是数字类型，会返回 400 参数错误
        male=True, # 传入 0, false, 空字符串 为 False，其他均为 True，如果不传入，传入这里指定的默认值
        skills=[], # 传入 req.parameters["skills"]，会返回一个数组，如果没有传入任何的内容，则返回这里指定的数组
        extra={} # 传入 json.loads(req.parameter["extra"])，如果不传入则传入这里指定的 dict 对象，如果传入的字符串不是 JSON 格式，则响应为 400 参数错误
    ):
    return "<html><body>Hello, World!</body></html>"
```

以上的是基础类型的获取，实施上，我们还提供了几个类，通过这些类，你还能快速地获取一些在请求头中，Cookies 中，请求体，路径中的信息。以下是一些代码实例：

```python
from simple_http_server import request_map
from simple_http_server import Parameter
from simple_http_server import Parameters
from simple_http_server import Headers
from simple_http_server import Header
from simple_http_server import Cookies
from simple_http_server import Cookie
from simple_http_server import PathValue


@request_map("/say_hello/to/{name}", method=["GET", "POST", "PUT"])
def your_ctroller_function(
        user_name=Parameter("userName", required=True), # 传入 req.parameter["userName"]，如果该参数为空，则会响应为 400 参数错误
        password=Parameter("password", required=True), # 传入 req.parameter["password"]，如果参数为空，则会响应为 400 参数错误
        nickName=Parameter(default=""), # 传入 req.parameter["nickName"]，如果参数为空，则会传入 ""，参数名和
        skills=Parameters(required=True), # 传入 req.parameters["skills"]，会返回一个数组，如果没有传入任何的内容，则响应为 400 参数错误
        all_headers=Headers(), # 传入 req.headers
        user_token=Header(name="userToken", required=True), # 传入 req.headers["userToken"]，如果请求头中没有 "userToken" 字段，则响应为 400 参数错误
        all_cookies=Cookies(), # 传入 req.cookies，返回所有当前请求的 cookies
        user_info=Cookie("userInfo", required=False), # 传入 req.cookies["userInfo"]，如果没有该 cookie，则响应为 400 参数错误
        name=PathValue("name"), # 传入 req.path_values["name"]，返回路径中你路由配置中匹配 {name} 的字符串
    ):
    return "<html><body>Hello, World!</body></html>"
```

从上述的例子我们看出，这些类中的参数均有默认值，即使不传入，也能返回正确的数据。除了上述的这些例子之外，我们还有一些额外的情况。例如请求的 Content-Type 是 application/json，然后我们将 JSON 字符串直接写入请求体中，我们可以这样获取信息：

```python
from simple_http_server import request_map
from simple_http_server import JSONBody

@request_map("/from_json_bldy", method=["post", "put", "delete"])
def your_json_body_controller_function(data=JSONBody()):
    ##
    #  JSONBody 是 dict 的子类，你可以直接其是一个 dict 来使用
    print(data["some_key"])
    return "<html><body>Hello, World!</body></html>"
```

我们也支持使用 multipart/form-data 上传文件，你可以这样获取文件：

```python
from simple_http_server import request_map
from simple_http_server import MultipartFile

@request_map("/upload", method="POST")
def upload(
        img=MultipartFile("img", required=True) # 如果没有传入 img 参数，或者该参数不是一个文件，均响应为 400 参数错误
        ):
    root = os.path.dirname(os.path.abspath(__file__))
    ##
    # 获取上传文件的 content-type
    print(img.content_type)
    ##
    # MultipartFile.content 在 3.6 中为 bytes 类型，在 2.7 中为字符串
    print(img.content)
    ##
    # 还可以通过内置的 save_to_file 将内容直接写入到某个文件中
    img.save_to_file(root + "/uploads/imgs/" + img.filename)
    return "<!DOCTYPE html><html><body>upload ok!</body></html>"

```

### 响应请求

从上述的例子中可以看出，取得请求中的参数我们有许多方式，这个给了开发者很高的自由度来编写这些信息。而响应的方法一样具有各种方法。

上述的例子中是其中一种，我们直接返回了一个HTML格式的字符串，该框架会自动的将这个字符串响应为 text/html 格式。

除了 HTML5 格式的字符串，我们还可以返回以下的内容：

```python
    ##
    # 如果你返回一个 dict，那么框架将会将其响应为 application/json
    return {"success": True, "message": "Success!"}
```

```python
    ##
    # 你可以返回一个 XML 格式的字符串，框架会将其响应为 text/xml
    return "<?xml><root></root>"
```

```python
    ##
    # 返回其他的字符串，框架会将其响应为 text/plain
    return "some other string value"
```

```python
    ##
    # 响应为 HTTP 错误，可以在任何适合抛出一个 HttpError 异常
    from simple_http_server import HttpError
    raise HttpError(404, "page not found")
```

```python
    ##
    # 如果抛出其他的异常，默认会响应为 500 服务器错误
    raise Exception()
```

```python
    ##
    # 返回 Redirect 对象
    from simple_http_server import Redirect
    return Redirect("/redirect/to/this/path")
```

```python
    ##
    # 你可以返回一个 StaticFile 类，返回一个文件，这个可以编写下载用的控制器方法
    from simple_http_server import StaticFile
    return StaticFile("/path/to/file.xml", content_type="text/xml")
```

```python
    ##
    # 还可以返回一个 Response 对象，这个对象可以设置更多的信息
    from simple_http_server import Response
    from http.cookies import SimpleCookie
    res = Response(status_code=200)
    res.headers["Content-Type"] = "text/html"
    res.set_header("userToken", "user_id_token_xxxx") # set_header() 会覆盖之前设置的信息
    res.add_header("userToken", "xxxx") # add_header() 会增加多一个信息
    res.cookies = SimpleCookie()
    res.cookie["userInfo"] = "ABC"
    res.cookie["userInfo"]["path"] = "/"
    res.body = "<!DOCTYPE html><html><body>hello world</body></html>"
    return res
```

```python
    ##
    # 我们还有一个更为简便的方式，就是直接返回一个元祖(tuple)
    from simple_http_server import Headers
    from simple_http_server import Cookies
    res_cookies = Cookies()
    res_cookie["userInfo"] = "ABC"
    res_cookie["userInfo"]["path"] = "/"
    ##
    # 该元祖中，这些参数的顺序其实并无关系，
    # 第一个返回的 int 元素会将作为请求的状态码
    # 但是元组中所有 Headers 对象均将会被写入到响应头中
    # 同样，元祖中所有 http.cookies.BaseCookies 以及其子类，含 http.cookie.SimpleCookie 以及 simple_http_server.Cookies 均会被写入响应的 cookies 中
    # 而元祖中第一个出现的类型在 (str, unicode, dict, StaticFile, bytes) 会被作为响应的数据。
    # 其他不符合条件的元素将被忽略
    return 200, Headers({"userToken": "user_id_token_xxx"}), res_cookie, {"success": True, "message": "success!"}, "这个字符串会被忽略"
```

```python
    ##
    # 元祖中所有的元素均不是必须的，即使是 body 也是一样，你可以省略一些没有的内容
    # 以下的元祖只写入了头部和响应体信息
    return Headers({"userToken": "user_id_token_xxx"}), {"success": True, "message": "success!"},

```

上述的例子中描述的通过返回信息来进行响应，你也可以通过 Response 参数来响应

```python
from simple_http_server import request_map
from simple_http_server import Response

@request_map("/say_hello")
def say_hello(res=Response()):
    ##
    # Response 对象就是上述我们写在返回的那个对象，所以，上面的对 headers、cookies 等的接口这个对象均有。
    res.body = "<html><body>Hello, world! </body></html>"
    res.send_response()
    # 如果使用 res 来发送请求，就不再在控制器函数中返回任何内容了。

@request_map("/")
def redirect(res=Response()):
    res.send_redirect("/index")
```

## 编写过滤器

参考 Java 的设计，我们增加了过滤器链式的设计，这个给了你一定的面向切面编码的能力，虽然比较弱，但是做一些权限验证，日志记录等也是够用的。

```python
from simple_http_server import filter_map

# 请注意！过滤器的字符串配置是一个正则表达式的字符串。
@filter_map("^/tuple")
def filter_tuple(ctx):
    print("---------- through filter ---------------")
    # 在过滤器中加入一些信息到请求头中
    ctx.request.headers["filter-set"] = "through filter"
    if "user_name" not in ctx.request.parameter:
        ctx.response.send_redirect("/index")
    elif "pass" not in ctx.request.parameter:
        ctx.response.send_error(400, "pass should be passed")
        # 你也可以使用以下代码，通过抛出异常的方式来返回错误的响应信息。
        # raise HttpError(400, "pass should be passed")
    else:
        # 如果你需要进入下一个过滤器链条或者调用请求处理的函数，必须显式调用以下的方法。
        ctx.do_chain()
```

## 启动服务器

```python

import simple_http_server.server as server
# 如果你的控制器代码（处理请求的函数）放在别的文件中，那么在你的 main.py 中，你必须将他都 import 进来。
import my_test_ctrl


def main(*args):
    # 除了 import 外，还可以通过 scan 方法批量加载 controller 文件。
    server.scan("my_ctr_pkg", r".*controller.*")
    server.start()

if __name__ == "__main__":
    main()
```

如果需要指定IP或者端口：

```python
    server.start(host="", port=8080)
```

如果需要指定静态资源：

*注意: `/path_prefix/`/`/path_prefix/*`/`/path_prefix/**` 具有相同的效果。*

```python 
    server.start(resources={"/path_prefix/*", "/absolute/dir/root/path",
                            "/path_prefix/*", "/absolute/dir/root/path"})
```

如果需要支持 HTTPS（SSL）


```python
    server.start(host="", 
                 port=8443,
                 ssl=True,
                 ssl_protocol=ssl.PROTOCOL_TLS, # 可选，默认使用 TLS
                 ssl_check_hostname=False, # 可选，是否检查域名，如果设为 True，那么如果不是通过该域名访问则无法建立对应链接。
                 keyfile="/path/to/your/keyfile.key",
                 certfile="/path/to/your/certfile.cert",
                 keypass="", # 可选，如果你的私钥使用了密码加密
                 )
    
```

## 日志

默认情况下，日志会输出到控制台，你创建自己的 Logging Handler 来将日志输出到别处，例如一个滚动文件中：

```python
import simple_http_server.logger as logger
import logging

_formatter = logging.Formatter(fmt='[%(asctime)s]-[%(name)s]-%(levelname)-4s: %(message)s')
_handler = logging.TimedRotatingFileHandler("/var/log/simple_http_server.log", when="midnight", backupCount=7)
_handler.setFormatter(_formatter)
_handler.setLevel("INFO")

logger.set_handler(_handler)
```

如果你想增加一个日志控制器而不是想替代内置的，那么你可以使用以下方法：

```python
logger.add_handler(_handler)
```

你也可以使用以下方法来设置日志输出级别：

```python
logger.set_level("DEBUG")
```

这个日志使用了一个背景线程来输出日志，因此其非常适合使用在多线程的场景，特别你是你有多个 logger 共用一个 `TimedRotatingFileHandler` 的时候。在多线程的场景下，这个日志控制器经常不能正常地按时切割文件。

## 问题

### 多线程的安全性

因为这是一个“SIMPLE”的服务器，所以在很多的情况下我并没有考虑多线程的资源控制，默认的情况下，使用了 socketserver 的 ThreadingMixIn 来确保每个请求都在自己的线程当中。但是如果你在自己的代码中编写一些多线程的代码，那么例如往传入的 Headers、Request、Response 等对象中写入内容可能会导致多线程安全性问题。