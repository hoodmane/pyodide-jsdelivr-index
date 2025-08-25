from workers import Response, WorkerEntrypoint, fetch
from urllib.parse import urlparse
from create_index import create_package_index
from js import Headers

DIST_TEMPLATE = "https://cdn.jsdelivr.net/pyodide/v{}/full/"
HEADERS = Headers.new([
    ("access-control-allow-origin", "*"),
    ("access-control-expose-headers", "*"),
    ("content-type", "text/html"),
])

class Default(WorkerEntrypoint):
    async def fetch(self, request):
        path = urlparse(request.url).path
        if path == "/favicon":
            return Response("")
        if path.endswith("/"):
            path += "index.html"
        version = path.split("/", maxsplit=2)[1]

        result = await self.env.index_cache.get(path)
        if result:
            return Response(result)

        dist_url = DIST_TEMPLATE.format(version)
        lock_url = dist_url + "pyodide-lock.json"
        print("Fetching url", lock_url)
        resp = await fetch(lock_url)
        resp.raise_for_status()
        lock = await resp.json()
        idx = create_package_index(version, lock["packages"], dist_url)
        for key, val in idx:
            await self.env.index_cache.put(key, val)
        result = await self.env.index_cache.get(path)
        return Response(result, headers=HEADERS)
