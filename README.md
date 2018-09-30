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

@request_map("/index")
def my_ctrl(paramters=None,
            json=None,
            **kargs  # This is required, for there are still other key arguments that will set to call this function
            ):

    return {"code": 0, "message": "success"} # You can return a dictionary, a string or a `simple_http_server.simple_http_server.Response` object.
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