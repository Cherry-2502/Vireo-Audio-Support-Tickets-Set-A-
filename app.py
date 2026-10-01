"""
Root entrypoint for Streamlit application.
Runs src/app.py seamlessly from project root.
"""
import os
import sys

# Add src to path and execute src/app.py
src_app_path = os.path.join(os.path.dirname(__file__), "src", "app.py")
with open(src_app_path, "r", encoding="utf-8") as f:
    code = f.read()

exec(code, {"__name__": "__main__", "__file__": src_app_path})
