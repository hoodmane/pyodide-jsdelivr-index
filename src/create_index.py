from urllib.parse import urlparse
from textwrap import dedent

INDEX_TEMPLATE = dedent(
    """
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="pypi:repository-version" content="1.0">
    <title>Simple index</title>
    </head>
    <body>
    {packages_str}
    </body>
    </html>
    """
).strip()

FILE_TEMPLATE = dedent(
    """
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="pypi:repository-version" content="1.0">
    <title>Links for {pkgname}</title>
    </head>
    <body>
    <h1>Links for {pkgname}</h1>
    {links}
    </body>
    </html>
    """
).strip()

def create_package_index(
    version: str, packages, dist_url: str
) -> list[tuple[str, str]]:
    # We only want to index the wheels
    packages = {
        pkgname: pkginfo
        for (pkgname, pkginfo) in packages.items()
        if pkginfo["file_name"].endswith(".whl")
    }

    # Create top level index
    packages_str = "\n".join(f'<a href="{x}/">{x}</a>' for x in packages.keys())

    result = []
    result.append((f"/{version}/index.html", INDEX_TEMPLATE.format(packages_str=packages_str)))

    for pkgname, pkginfo in packages.items():
        filename = pkginfo["file_name"]
        if urlparse(filename).scheme:
            href = filename
        else:
            shasum = pkginfo["sha256"]
            href = f"{dist_url}{filename}#sha256={shasum}"
        links_str = f'<a href="{href}">{pkgname}</a>\n'
        files_html = FILE_TEMPLATE.format(pkgname=pkgname, links=links_str)
        result.append((f"/{version}/{pkgname}/index.html", files_html))
    return result
