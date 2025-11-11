import re
from textwrap import dedent
from typing import TypedDict
from urllib.parse import urlparse

_canonicalize_regex = re.compile(r"[-_.]+")


def canonicalize_name(name: str) -> str:
    # This is taken from PEP 503.
    return _canonicalize_regex.sub("-", name).lower()


ROOT_INDEX_TEMPLATE = dedent(
    """
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="pypi:repository-version" content="1.0">
    <title>Pyodide Simple Package Indices</title>
    <link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
    <link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon-16x16.png">
    </head>
    <body>
    <h1>Pyodide simple package indices</h1>
    <p>
    This is a collection of Pyodide simple package indices.
    The most recent one is here <a href={latest}>{latest}</a>.
    You can pass the url to that page as an <code>--extra-index-url</code> for
    pip or uv to install packages for Pyodide. Though it's unlikely you need to
    do this directly.
    </p>

    <h2>All available versions</h2>
    {all_versions}
    </body>
    </html>
    """
).strip()


def make_root_index_page(version_json):
    latest = version_json["tags"]["latest"]
    # Skip alpha versions. Before 0.24.0 we didn't have a pyodide-lock.json so
    # this won't work.
    all_versions = (
        key
        for key in version_json["versions"]
        if "alpha" not in key and "dev" not in key and key >= "0.24.0"
    )
    versions_html = []
    for ver in all_versions:
        versions_html.append(f"<div><a href={ver}>{ver}</a></div>")
    return ROOT_INDEX_TEMPLATE.format(
        latest=latest, all_versions="\n".join(versions_html)
    )


INDEX_TEMPLATE = dedent(
    """
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="pypi:repository-version" content="1.0">
    <title>Pyodide {version} Simple Package Index</title>
    <link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
    <link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon-16x16.png">
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
    <title>Links for {pkgname} from Pyodide {version} Simple Package Index</title>
    <link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
    <link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon-16x16.png">
    </head>
    <body>
    <h1>Links for {pkgname}</h1>
    {links}
    </body>
    </html>
    """
).strip()


class Digests(TypedDict):
    sha256: str


class ReleaseInfo(TypedDict):
    digests: Digests
    url: str
    filename: str


class Package(TypedDict):
    name: str
    file_name: str
    sha256: str
    version: str
    releases: list[ReleaseInfo]


def create_top_level_index(
    version: str, packages: dict[str, Package]
) -> tuple[str, str]:
    # We only want to index the wheels
    packages = {
        pkgname: pkginfo
        for (pkgname, pkginfo) in packages.items()
        if pkginfo["file_name"].endswith(".whl")
    }

    # Create top level index
    packages_str = "\n".join(
        f'<a href="{version}/{x}/">{x}</a>' for x in packages.keys()
    )

    return (
        f"/{version}/index.html",
        INDEX_TEMPLATE.format(version=version, packages_str=packages_str),
    )


def create_package_index(version: str, dist_url, pkginfo: Package) -> tuple[str, str]:
    filename = pkginfo["file_name"]
    if urlparse(filename).scheme:
        href = filename
    else:
        shasum = pkginfo["sha256"]
        href = f"{dist_url}{filename}#sha256={shasum}"
    links = [f'<a href="{href}">{filename}</a>\n']
    for release in pkginfo["releases"]:
        shasum = release["digests"]["sha256"]
        href = release["url"]
        links.append(f'<a href="{href}#sha256={shasum}">{release["filename"]}</a>')
    pkgname = canonicalize_name(pkginfo["name"])
    file_html = FILE_TEMPLATE.format(
        version=version, pkgname=pkgname, links="\n".join(links)
    )
    return (f"/{version}/{pkgname}/index.html", file_html)
