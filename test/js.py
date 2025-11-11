from collections import UserDict
from dataclasses import dataclass, field


class Array:
    @staticmethod
    def new(*args):
        return list(args)


class Headers:
    @staticmethod
    def new(arg):
        return dict(arg)


class Object(UserDict):
    @staticmethod
    def fromEntries(entries):
        return Object(entries)

    def to_py(self):
        return self.data


@dataclass
class Request:
    url: str


class Headers(UserDict):
    @staticmethod
    def new(arg):
        return Headers()

    def entries(self):
        return self.data.items()


@dataclass
class Response:
    def new(arg, *, headers=None):
        if headers is None:
            headers = {}
        if isinstance(arg, str):
            return Response(arg, headers=Headers(headers.items()))
        return arg

    body: str
    url: str = ""
    status: int = 200
    statusText: str = "Ok"
    headers: Headers = field(default_factory=Headers)
    type: str = "default"
