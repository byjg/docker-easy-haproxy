import os
import sys

# Add EasyHAProxy src/ so plugin imports (plugins, functions) resolve correctly.
# When running: cd new_plugin && EASYHAPROXY_SRC=../src uv run pytest -s -vv tests/
EASYHAPROXY_SRC = os.getenv("EASYHAPROXY_SRC", "../src")
sys.path.insert(0, os.path.abspath(EASYHAPROXY_SRC))

# Add this plugin's own src/ so protect_legacy can be imported directly.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
