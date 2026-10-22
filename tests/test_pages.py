import os
import re

import pytest

from functions import pages

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                      "deploy", "docker", "assets", "etc", "easyhaproxy")

# HAProxy loads an error page into one buffer (tune.bufsize, 16384 by
# default) and keeps part of it free for rewrites.
HAPROXY_PAGE_LIMIT = 15360


@pytest.mark.parametrize("path", sorted(pages.asset_files()))
def test_committed_page_matches_its_template(path):
    """The pages in the image are rendered from src/templates/pages: run
    `python -m functions.pages` after changing a template."""
    with open(os.path.join(ASSETS, path)) as f:
        assert f.read() == pages.asset_files()[path], f"{path} is out of date: run python -m functions.pages"


def test_every_errorfile_in_the_config_is_rendered():
    with open(os.path.join(os.path.dirname(pages.PAGES_DIR), "haproxy.cfg.j2")) as f:
        codes = {int(c) for c in re.findall(r"errorfile (\d{3}) ", f.read())}
    assert codes == set(pages.ERRORS)


@pytest.mark.parametrize("code", sorted(pages.ERRORS))
def test_error_page(code):
    page = pages.render_error(code)
    reason = pages.ERRORS[code][0]

    assert page.startswith(f"HTTP/1.0 {code} {reason}\n")
    assert len(page.encode()) < HAPROXY_PAGE_LIMIT
    # Visitors of every site behind it see these: nothing names the proxy,
    # and nothing is loaded from elsewhere.
    assert "easyhaproxy" not in page.lower()
    assert "http://" not in page and "https://" not in page and "<script" not in page


def test_welcome_page_fits_haproxy():
    assert len(pages.render_welcome().encode()) < HAPROXY_PAGE_LIMIT
