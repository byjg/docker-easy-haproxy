"""
The HTML pages HAProxy serves by itself: the welcome page, until the first
service is configured, and the error pages (HAPROXY_CUSTOMERRORS).

They share one template, so they look alike, and are rendered into the image
assets once, not at run time:

    uv run python -m functions.pages

tests/test_pages.py fails when the committed files no longer match the
templates.
"""

import base64
import os

from jinja2 import Environment, FileSystemLoader

PAGES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), "templates", "pages")
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))),
                          "deploy", "docker", "assets", "etc", "easyhaproxy")

# The status codes HAProxy answers by itself, with the reason and what it
# means for a visitor. 404 is a host no service is configured for.
ERRORS = {
    400: ("Bad Request", "The request could not be understood."),
    403: ("Forbidden", "You do not have access to this page."),
    404: ("Not Found", "There is no site configured for this address."),
    408: ("Request Timeout", "The request took too long to arrive. Try again."),
    500: ("Internal Server Error", "Something went wrong. Try again in a moment."),
    502: ("Bad Gateway", "The site did not answer correctly. Try again in a moment."),
    503: ("Service Unavailable", "The site is temporarily unavailable. Try again in a moment."),
    504: ("Gateway Timeout", "The site took too long to answer. Try again in a moment."),
}


def _environment():
    env = Environment(loader=FileSystemLoader(PAGES_DIR), autoescape=True)
    env.trim_blocks = True
    env.lstrip_blocks = True
    return env


def render_welcome():
    with open(os.path.join(PAGES_DIR, "logo.png"), "rb") as f:
        logo = base64.b64encode(f.read()).decode()
    return _environment().get_template("welcome.html.j2").render(title="EasyHAProxy is running", logo=logo)


def render_error(code):
    """A complete HTTP response, as HAProxy's errorfile expects it."""
    reason, message = ERRORS[code]
    html = _environment().get_template("error.html.j2").render(
        title=f"{code} {reason}", code=code, reason=reason, message=message)
    return (f"HTTP/1.0 {code} {reason}\n"
            "Cache-Control: no-cache\n"
            "Connection: close\n"
            "Content-Type: text/html; charset=utf-8\n"
            "\n" + html)


def asset_files():
    """Every page, keyed by its path under the image's /etc/easyhaproxy."""
    files = {"www/welcome.html": render_welcome()}
    for code in ERRORS:
        files[f"haproxy/errors-custom/{code}.http"] = render_error(code)
    return files


if __name__ == "__main__":
    for path, content in asset_files().items():
        with open(os.path.join(ASSETS_DIR, path), "w") as f:
            f.write(content)
        print(f"wrote {path} ({len(content.encode())} bytes)")
