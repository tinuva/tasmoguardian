import os
from pathlib import Path

import reflex as rx

# Exclude data directory from hot reload to prevent backup files triggering recompile
os.environ.setdefault(
    "REFLEX_HOT_RELOAD_EXCLUDE_PATHS",
    str(Path.cwd() / "data")
)

config = rx.Config(
    app_name="tasmo_guardian",
    disable_plugins=["reflex.plugins.sitemap.SitemapPlugin"],
)
