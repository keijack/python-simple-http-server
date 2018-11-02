# Change log and TODOs of `python-simple-http-server`

## Change log

### Version 0.1.4 2018-11-1

1. Support `cookies`, you can read and write `cookies` very easily in your controller function.
2. You can use `Headers()` as a default argument in your controller function, if you do so, All headers will be given to this argument.
3. Some bugs are fixed.

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