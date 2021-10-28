# -*- coding: utf-8 -*-
import setuptools
import codecs
import os.path

def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), 'r') as fp:
        return fp.read()

def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith('version'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="simple_http_server",
    version=get_version("simple_http_server/__init__.py"),
    author="Keijack",
    author_email="keijack.wu@gmail.com",
    description="This is a simple http server, use MVC like design.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/keijack/python-simple-http-server",
    python_requires='>=3.7',
    packages=["simple_http_server"],
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
