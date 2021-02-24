

def remove_url_first_slash(url: str):
    _url = url
    while _url.startswith("/"):
        _url = url[1:]
    return _url
