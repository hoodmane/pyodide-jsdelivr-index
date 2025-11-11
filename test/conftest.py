import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import js
from pyodide import http

http.Object = js.Object

sys.path.append(str(Path(__file__).parents[1] / "src"))

from workers import _workers


@dataclass
class ResponseWrapper:
    js_response: Any


class ResponseBodyConstructor:
    name = "Response"


@dataclass
class ResponseBody:
    constructor = ResponseBodyConstructor
    response: httpx.Response

    @property
    def url(self):
        return self.response.url

    @property
    def status(self):
        return self.response.status_code

    @property
    def bodyUsed(self):
        return not self.response.is_closed

    async def text(self):
        return self.response.text


async def pyfetch(url: str, /, *, fetcher=None):
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
    return ResponseWrapper(ResponseBody(r))


_workers._pyfetch_patched = pyfetch

