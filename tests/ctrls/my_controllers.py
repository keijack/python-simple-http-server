# -*- coding: utf-8 -*-

import asyncio
import queue
from typing import List
import uuid
from simple_http_server import ModelDict, Redirect, RegGroup, RegGroups
from simple_http_server import Headers
from simple_http_server import StaticFile
from simple_http_server import HttpError
from simple_http_server import JSONBody
from simple_http_server import Header
from simple_http_server import Parameters
from simple_http_server import Cookie
from simple_http_server import Cookies
from simple_http_server import PathValue
from simple_http_server import Parameter
from simple_http_server import MultipartFile
from simple_http_server import Response
from simple_http_server import Request
from simple_http_server import Session
from simple_http_server import filter_map
from simple_http_server import request_map, route
from simple_http_server import controller
from simple_http_server import error_message
import os
import simple_http_server.logger as logger
import simple_http_server.server as server
import functools


_logger = logger.get_logger("my_test_main")


_logger = logger.get_logger("controller")


def cors(origin="*", methods="*", headers="*"):
    def add_cors_headers(ctrl):
        def ctrl_warpper(*args, **kwargs):
            cors_header = Headers({
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": methods,
                "Access-Control-Allow-Headers": headers
            })
            res = ctrl(*args, **kwargs)
            if isinstance(res, tuple):
                l = list(res)
                l.insert(0, cors_header)
                return tuple(l)
            else:
                return cors_header, res
        return ctrl_warpper
    return add_cors_headers


@request_map("/")
@request_map("/index")
def my_ctrl():
    return {"code": 0, "message": "success"}  # You can return a dictionary, a string or a `simple_http_server.simple_http_server.Response` object.


@request_map("/say_hello", method=["GET", "POST"])
@cors()
def my_ctrl2(name, name2=Parameter("name", default="KEIJACK")):
    """name and name2 is the same"""
    return f"<!DOCTYPE html><html><body>hello, {name}, {name2}</body></html>"


@request_map("/error")
def my_ctrl3():
    raise HttpError(400, "Parameter Error!", "Test Parameter Error!")


async def say(sth: str = ""):
    _logger.info(f"Say: {sth}")
    return f"Success! {sth}"


@request_map("/中文/coroutine")
async def coroutine_ctrl(hey: str = "Hey!"):
    # raise RuntimeError
    return await say(hey)


@request_map("/exception")
def exception_ctrl():
    raise Exception("some error occurs!")


@request_map("/upload", method="POST")
def my_upload(img=MultipartFile("img"), txt=Parameter("中文text", required=False, default="DEFAULT"), req=Request()):
    for k, v in req.parameter.items():
        print("%s (%s)====> %s " % (k, str(type(k)), v))
    print(txt)

    root = os.path.dirname(os.path.abspath(__file__))
    img.save_to_file(root + "/imgs/" + img.filename)
    return f"<!DOCTYPE html><html><body>upload ok! {txt} </body></html>"


@request_map("/post_txt", method=["GET", "POST"])
def normal_form_post(txt=Parameter("中文txt", required=False, default="DEFAULT"), req=Request()):
    for k, v in req.parameter.items():
        print("%s ====> %s " % (k, v))
    return f"<!DOCTYPE html><html><body>hi, {txt}</body></html>"


@request_map("/post_json", method="POST")
def post_json(json=JSONBody()):
    print(json)
    return json


@request_map("/cookies")
def set_headers(res: Response, headers: Headers, cookies: Cookies, cookie=Cookie("sc")):
    print("==================cookies==========")
    print(cookies)
    print("==================cookies==========")
    print(cookie)
    res.add_header("Set-Cookie", "sc=keijack; Expires=Web, 31 Oct 2018 00:00:00 GMT;")
    res.add_header("Set-Cookie", "sc=keijack2;")
    res.body = "<!DOCTYPE html><html><body>OK!</body></html>"


@request_map("tuple")
def tuple_results():
    return 200, Headers({"MyHeader": "my header"}), "hello tuple result!"


@request_map("session")
def test_session(session: Session, invalid=False):
    ins = session.get_attribute("in-session")
    if not ins:
        session.set_attribute("in-session", "Hello, Session!")

    _logger.info("session id: %s" % session.id)
    if invalid:
        _logger.info("session[%s] is being invalidated. " % session.id)
        session.invalidate()
    return "<!DOCTYPE html><html><body>%s</body></html>" % str(ins)


@request_map("tuple_cookie")
def tuple_with_cookies(headers=Headers(), all_cookies=Cookies(), cookie_sc=Cookie("sc")):
    print("=====>headers")
    print(headers)
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

    return 200, Header({"xx": "yyy"}), cks, "<html><body>OK</body></html>"


@request_map("header_echo")
def header_echo(headers: Headers):
    return 200, headers, ""


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
        res: Response = ctx.response
        print("add headers to response!")
        res.add_header("Access-Control-Allow-Origin", "*")
        res.add_header("Access-Control-Allow-Methods", "*")
        res.add_header("Access-Control-Allow-Headers", "*")
        ctx.do_chain()


@request_map("/redirect")
def redirect():
    return Redirect("/index")


@request_map("/params")
def my_ctrl4(user_name,
             password=Parameter(name="passwd", required=True),
             remember_me=True,
             locations=[],
             json_param={},
             lcs=Parameters(name="locals", required=True),
             content_type=Header("Content-Type", default="application/json"),
             connection=Header("Connection"),
             ua=Header("User-Agent"),
             headers=Headers()
             ):
    return f"""<!DOCTYPE html>
    <html>
    <head>
        <title>show all params!</title>
    </head>
    <body>
        <p>user_name: {user_name}</p>
        <p>password: {password}</p>
        <p>remember_me: {remember_me}</p>
        <p>locations: {locations}</p>
        <p>json_param: {json_param}</p>
        <p>locals: {lcs}</p>
        <p>conent_type: {content_type}</p>
        <p>user_agent: {ua}</p>
        <p>connection: {connection}</p>
        <p>all Headers: {headers}</p>
    </body>
    </html>
    """


@request_map("/int_status_code")
def return_int(status_code=200):
    return status_code


@request_map("/path_values/{pval}/{path_val}/x")
def my_path_val_ctr(pval: PathValue, path_val=PathValue()):
    return f"<html><body>{pval}, {path_val}</body></html>"


@controller(args=["my-ctr"], kwargs={"desc": "desc"})
@route("/obj")
class MyController:

    def __init__(self, name, desc="") -> None:
        self._name = f"ctr object[#{name}]:{desc}"

    @route("/hello", method="GET, POST")
    @request_map
    def my_ctrl_mth(self, model: ModelDict):
        return {"message": f"hello, {model['name']}, {self._name} says. "}

    @request_map("/hello2", method=("GET", "POST"))
    def my_ctr_mth2(self, name: str, i: List[int]):
        return f"<html><head><title>{self._name}</title></head><body>{self._name}: {name}, {i}</body></html>"

    @route(regexp="^(reg/(.+))$", method="GET")
    def my_reg_ctr(self, reg_group: RegGroup = RegGroup(1)):
        return f"{self._name}, {reg_group.group},{reg_group}"


@error_message("400")
def my_40x_page(message: str, explain=""):
    return f"code：400, message: {message}, explain: {explain}"


@error_message
def my_other_error_page(code, message, explain=""):
    return f"{code}-{message}-{explain}"
