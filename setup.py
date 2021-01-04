# -*- coding: utf-8 -*-
import setuptools
import simple_http_server

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="simple_http_server",
    version=simple_http_server.version,
    author="Keijack",
    author_email="keijack.wu@gmail.com",
    description="This is a simple http server, use MVC like design.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/keijack/python-simple-http-server",
    packages=["simple_http_server"],
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
