from workers import Response, WorkerEntrypoint, fetch
from urllib.parse import urlparse
from create_index import create_package_index, make_root_index_page
from js import Headers, Array

DIST_TEMPLATE = "https://cdn.jsdelivr.net/pyodide/v{}/full/"
HEADERS = Headers.new(
    [
        ("access-control-allow-origin", "*"),
        ("access-control-expose-headers", "*"),
        ("content-type", "text/html"),
    ]
)


class Default(WorkerEntrypoint):
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

        version = path.split("/", maxsplit=2)[1]

        result = await self.env.index_cache.get(Array.new(version, path))
        if result:
            if content := result[path]:
                return Response(content, headers=HEADERS)
            if result[version] is not None:
                return Response("Not found", status=404)

        dist_url = DIST_TEMPLATE.format(version)
        lock_url = dist_url + "pyodide-lock.json"
        resp = await fetch(lock_url)
        resp.raise_for_status()
        lock = await resp.json()
        idx = create_package_index(version, lock["packages"], dist_url)
        for key, val in idx:
            if key == path:
                result = val
            await self.env.index_cache.put(key, val)
        await self.env.index_cache.put(version, "")
        return Response(result, headers=HEADERS)
