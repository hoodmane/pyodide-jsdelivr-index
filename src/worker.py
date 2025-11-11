import json
from asyncio import gather
from urllib.parse import urlparse

from js import Array, Headers
from workers import Response, WorkerEntrypoint, fetch

from create_index import (
    Package,
    ReleaseInfo,
    create_package_index,
    create_top_level_index,
    make_root_index_page,
)

DIST_TEMPLATE = "https://cdn.jsdelivr.net/pyodide/v{}/full/"
HEADERS = Headers.new(
    [
        ("access-control-allow-origin", "*"),
        ("access-control-expose-headers", "*"),
        ("content-type", "text/html"),
    ]
)


async def fetch_pypi_metadata(pkg: Package) -> ReleaseInfo:
    resp = await fetch(f"https://pypi.org/pypi/{pkg['name']}/json")
    if resp.status >= 400:
        pkg["releases"] = []
        return
    info = await resp.json()
    try:
        releases = info["releases"][pkg["version"]]
    except KeyError:
        pkg["releases"] = []
        return
    pkg["releases"] = releases


async def fetch_pypi_metadatas(pkgs: list[Package]) -> dict[str, ReleaseInfo]:
    await gather(*(fetch_pypi_metadata(pkg) for pkg in pkgs))


async def fetch_package_info(version) -> dict[str, Package]:
    dist_url = DIST_TEMPLATE.format(version)
    lock_url = dist_url + "pyodide-lock.json"
    resp = await fetch(lock_url)
    resp.raise_for_status()
    lock = await resp.json()
    return lock["packages"]


class Default(WorkerEntrypoint):
    async def cache_package_infos(
        self, version: str, pkg_infos: dict[str, Package]
    ) -> str:
        await self.env.index_cache.put(version, json.dumps(pkg_infos))
        k, v = create_top_level_index(version, pkg_infos)
        await self.env.index_cache.put(k, v)
        return v

    async def fetch(self, request):
        path = urlparse(request.url).path
        if path.startswith("/assets"):
            return await self.env._env.ASSETS.fetch(
                "http://fakehost.invalid/" + path.removeprefix("/assets")
            )
        if not path.endswith("/index.html") and not path.endswith("/"):
            path += "/"
        if path.endswith("/"):
            path += "index.html"
        if path == "/index.html":
            resp = await fetch("https://data.jsdelivr.com/v1/package/npm/pyodide")
            resp.raise_for_status()
            version_json = await resp.json()
            html = make_root_index_page(version_json)
            return Response(html, headers=HEADERS)

        parts = path.split("/", maxsplit=3)
        version = parts[1]
        name = parts[2]
        print("version", version, "name", name)

        result = await self.env.index_cache.get(Array.new(version, path))
        if content := result[path]:
            print("... Found result in cache")
            return Response(content, headers=HEADERS)
        pkg_infos: dict[str, Package]
        if result[version]:
            print("... Found lock info in cache")
            pkg_infos = json.loads(result[version])
        else:
            print("... Fetching lock info")
            pkg_infos = await fetch_package_info(version)
            v = await self.cache_package_infos(version, pkg_infos)
            if name == "index.html":
                # Return top level index
                return Response(v, headers=HEADERS)

        pkg_info = pkg_infos.get(name)
        if not pkg_info:
            return Response("Not found", status=404)

        print("... Fetching pypi info for", name)
        await fetch_pypi_metadata(pkg_info)
        dist_url = DIST_TEMPLATE.format(version)
        k, v = create_package_index(version, dist_url, pkg_info)
        await self.env.index_cache.put(k, v)
        return Response(v, headers=HEADERS)
