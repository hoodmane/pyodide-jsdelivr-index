from dataclasses import dataclass, field

import pytest
from bs4 import BeautifulSoup
from js import Request
from pytest_httpx import HTTPXMock


class Ctx:
    pass


@dataclass
class KV:
    data: dict = field(default_factory=dict)

    async def get(self, k: str | list[str]):
        if isinstance(k, str):
            return self.data.get(k)
        if isinstance(k, list):
            return {key: self.data.get(key) for key in k}

    async def put(self, key, value):
        self.data[key] = value


@dataclass
class Env:
    index_cache: KV = field(default_factory=KV)


from worker import Default

AFFINE_JSDELIVR_INFO = {
    "depends": [],
    "file_name": "affine-2.4.0-py3-none-any.whl",
    "imports": ["affine"],
    "install_dir": "site",
    "name": "affine",
    "package_type": "package",
    "sha256": "1d4c8070a40853fc28819af0821ee25d42979718165e0d4255d3063d9b11d1d4",
    "unvendored_tests": True,
    "version": "2.4.0",
}

@pytest.fixture
def package_json(httpx_mock: HTTPXMock):

    packages = {"affine": AFFINE_JSDELIVR_INFO}
    json = {"packages": packages}
    httpx_mock.add_response(
        method="GET",
        url="https://cdn.jsdelivr.net/pyodide/v0.28.3/full/pyodide-lock.json",
        json=json,
    )


@pytest.mark.parametrize("url", ["/", "/index.html"])
@pytest.mark.asyncio
async def test_root(httpx_mock: HTTPXMock, url: str):
    latest = "0.29.0"
    versions = ["0.29.0", "0.28.3", "0.28.2", "0.28.1", "0.28.0"]
    json = {"tags": {"latest": latest}, "versions": versions}
    httpx_mock.add_response(
        method="GET", url="https://data.jsdelivr.com/v1/package/npm/pyodide", json=json
    )
    worker = Default(Ctx, Env())
    result = await worker.fetch(Request(url))
    assert "This is a collection of Pyodide simple package indices." in result.body
    assert "The most recent one is here <a href=0.29.0>0.29.0</a>." in result.body
    assert worker.env.index_cache.data == {}
    parsed = BeautifulSoup(result.body, "html.parser")
    links = parsed.find_all("a")
    assert len(links) == len(versions) + 1
    for ver, link in zip(versions, links[1:]):
        assert link.text == ver
        assert link["href"] == ver



@pytest.mark.parametrize("url", ["/0.28.3", "/0.28.3/index.html"])
@pytest.mark.asyncio
async def test_version_index(package_json, url: str, capsys):
    worker = Default(Ctx, Env())
    result = await worker.fetch(Request("/0.28.3"))
    assert "Pyodide 0.28.3 Simple Package Index" in result.body
    assert list(worker.env.index_cache.data.keys()) == ["0.28.3", "/0.28.3/index.html"]
    parsed = BeautifulSoup(result.body, "html.parser")
    all_links = parsed.find_all("a")
    assert len(all_links) == 1
    res = all_links[0]
    assert res.text == "affine"
    assert res["href"] == "0.28.3/affine/"
    io = capsys.readouterr()
    assert "... Fetching lock info" in io.out
    assert "Found result in cache" not in io.out

    # If we make the request again, we shouldn't request the package list again
    result2 = await worker.fetch(Request("/0.28.3"))
    assert result2.body == result.body
    io = capsys.readouterr()
    assert "Fetching lock info" not in io.out
    assert "Found result in cache" in io.out


@pytest.mark.asyncio
async def test_package_info(package_json, httpx_mock: HTTPXMock, capsys):
    json = {
        "releases": {
            "2.4.0": [
                {
                    "digests": {
                        "blake2b_256": "0bf785273299ab57117850cc0a936c64151171fac4da49bc6fba0dad984a7c5f",
                        "md5": "8626f021f29631950dfad7b4c6435fc4",
                        "sha256": "8a3df80e2b2378aef598a83c1392efd47967afec4242021a0b06b4c7cbc61a92",
                    },
                    "filename": "affine-2.4.0-py3-none-any.whl",
                    "url": "https://files.pythonhosted.org/packages/0b/f7/85273299ab57117850cc0a936c64151171fac4da49bc6fba0dad984a7c5f/affine-2.4.0-py3-none-any.whl",
                },
                {
                    "digests": {
                        "blake2b_256": "6998d2f0bb06385069e799fc7d2870d9e078cfa0fa396dc8a2b81227d0da08b9",
                        "md5": "bc92555b48556f7439664cec13cf31f8",
                        "sha256": "a24d818d6a836c131976d22f8c27b8d3ca32d0af64c1d8d29deb7bafa4da1eea",
                    },
                    "filename": "affine-2.4.0.tar.gz",
                    "url": "https://files.pythonhosted.org/packages/69/98/d2f0bb06385069e799fc7d2870d9e078cfa0fa396dc8a2b81227d0da08b9/affine-2.4.0.tar.gz",
                },
            ]
        }
    }
    pypi_url = json["releases"]["2.4.0"][0]["url"]
    pypi_shasum = json["releases"]["2.4.0"][0]["digests"]["sha256"]
    httpx_mock.add_response(
        method="GET", url="https://pypi.org/pypi/affine/json", json=json
    )
    worker = Default(Ctx, Env())
    result = await worker.fetch(Request("/0.28.3/affine"))
    assert "Pyodide 0.28.3 Simple Package Index" in result.body
    assert list(worker.env.index_cache.data.keys()) == [
        "0.28.3",
        "/0.28.3/index.html",
        "/0.28.3/affine/index.html",
    ]
    parsed = BeautifulSoup(result.body, "html.parser")
    all_links = parsed.find_all("a")
    assert len(all_links) == 3
    jsdelivr_link = all_links[0]
    assert jsdelivr_link.text == "affine-2.4.0-py3-none-any.whl"
    assert jsdelivr_link["href"] == f"https://cdn.jsdelivr.net/pyodide/v0.28.3/full/{AFFINE_JSDELIVR_INFO['file_name']}#sha256={AFFINE_JSDELIVR_INFO['sha256']}"

    pypi_wheel_link = all_links[1]
    assert pypi_wheel_link.text == "affine-2.4.0-py3-none-any.whl"
    assert pypi_wheel_link["href"].startswith(
        "https://files.pythonhosted.org/packages/"
    )
    assert pypi_wheel_link["href"] == f"{pypi_url}#sha256={pypi_shasum}"

    io = capsys.readouterr()
    assert "Fetching lock info" in io.out
    assert "Fetching pypi info for affine" in io.out
    assert "Found result in cache" not in io.out
    
    # Test we hit cache on the second request
    result2 = await worker.fetch(Request("/0.28.3/affine"))
    assert result2.body == result.body
    io = capsys.readouterr()
    assert "Fetching lock info" not in io.out
    assert "Fetching pypi info for affine" not in io.out
    assert "Found result in cache" in io.out


@pytest.mark.asyncio
async def test_package_info_no_pypi_release(package_json, httpx_mock: HTTPXMock):
    json = {
        "releases": {}
    }
    httpx_mock.add_response(
        method="GET", url="https://pypi.org/pypi/affine/json", json=json
    )
    worker = Default(Ctx, Env())
    result = await worker.fetch(Request("/0.28.3/affine"))
    parsed = BeautifulSoup(result.body, "html.parser")
    all_links = parsed.find_all("a")
    assert len(all_links) == 1
