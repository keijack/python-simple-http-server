# python-simple-http-server

## 简介

这是一个轻量级的基于 Python http.server 编写的服务器，你可以非常容易的搭建一个 Restful API。其中一些请求的转发等参考了 SpringMVC 的设计。

## 支持的 Python 的版本

Python 2.7 / 3.6+ (3.5 也应该支持，没有在3.5环境测试过)

## 为什么要选择这个项目？

* 轻量级
* 支持过滤器链
* Spring MVC 风格的请求映射配置
* 简单易用
* 编写风格自由

## 如何使用？

### 安装

```shell
pip install simple_http_server
```

### 编写控制器

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


@request_map("/index")
def my_ctrl():
    # 直接返回一个 dict 对象，框架会将其变为一个 JSON 返回到请求方。
    return {"code": 0, "message": "success"}  


@request_map("/say_hello", method=["GET", "POST"])
def my_ctrl2(name, name2=Parameter("name", default="KEIJACK")):
    # 如果你的 url 传入了 name， 那么 name == name2，如果不传，会抛出400错误，因为 name 为必填值，如果删除name，不传 name 参数， name2 会使用默认值而不会抛出400错误。
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
    # 返回的元祖中，各个参数的顺序不必要是固定的，并且缺少任何的参数都可以。
    # 框架会使用第一个出现的 int 值作为该响应的状态。
    # 所有的 Header 对象都会被写入到响应头中。
    # 所有的 Cookies 对象都会被写入到响应中。
    # 第一个类型在 (str, unicode, dict, StaticFile, bytes) 会被作为响应的数据。
    # 其他不符合条件的元素将被忽略
    cks = Cookies()
    cks["ck1"] = "keijack"
    return 200, Headers({"my-header": "headers"}), cks, {"success": True}

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
    # cks = cookies.SimpleCookie() # 你可以使用 python 源生的 Cookie 对象。
    cks["ck1"] = "keijack"
    cks["ck1"]["path"] = "/"
    cks["ck1"]["expires"] = expires.strftime(Cookies.EXPIRE_DATE_FORMAT)

    return Header({"xx": "yyy"}), cks, "<html><body>OK</body></html>"

"""
" 如果你访问 /a/b/xyz/x，那么以下方法 `path_val` 就是 `xyz`
"""
@request_map("/a/b/{path_val}/x")
def my_path_val_ctr(path_val=PathValue()):
    return "<html><body>%s</body></html>" % path_val
```

### 编写过滤器

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

### 启动服务器

```python

import simple_http_server.server as server
# 如果你的控制器代码（处理请求的函数）放在别的文件中，那么在你的 main.py 中，你必须将他都 import 进来。
import my_test_ctrl


def main(*args):
    server.start()

if __name__ == "__main__":
    main()
```

## 问题

### Unicode 支持

虽然我已经尽力使得该框架在 Python 2.7 的环境下支持 unicode 字符串，但是由于 python 2.7 本身对 unicode 支持得不太友好，所以，普通的中文字可能问题不大，但是一些罕见字和字符可能还是会发生错误。而最有效的方法则是使用 Python 3。

### 多线程的安全性

因为这是一个“SIMPLE”的服务器，所以在很多的情况下我并没有考虑多线程的资源控制，默认的情况下，使用了 socketserver 的 ThreadingMixIn 来确保每个请求都在自己的线程当中。但是如果你在自己的代码中编写一些多线程的代码，那么例如往传入的 Headers、Request、Response 等对象中写入内容可能会导致多线程安全性问题。