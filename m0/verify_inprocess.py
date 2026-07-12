#!/usr/bin/env python3
"""M0: verify in-process decode == CLI decode (minus header) and dedup hash."""
import json
import sys

from inprocess_decode import load_decode_config, decode_dmp
from config_hash import config_hash

mod = load_decode_config(".venv/bin/decode-config.py")

for name in ("backup1", "backup2", "backup4", "backup5", "backup6"):
    with open(f"{name}.dmp", "rb") as f:
        inproc = decode_dmp(mod, f.read())
    with open(f"{name}.json") as f:
        cli = json.load(f)

    inproc = {k: v for k, v in inproc.items() if k != "header"}
    cli_stripped = {k: v for k, v in cli.items() if k != "header"}
    match = "MATCH" if inproc == cli_stripped else "MISMATCH"
    print(f"{name}: cli-vs-inprocess={match}  config_hash={config_hash(inproc)}")
    if match == "MISMATCH":
        only_cli = set(cli_stripped) - set(inproc)
        only_inp = set(inproc) - set(cli_stripped)
        diff_vals = {k for k in set(cli_stripped) & set(inproc) if cli_stripped[k] != inproc[k]}
        print(f"  only_cli={only_cli} only_inprocess={only_inp} value_diffs={diff_vals}")
        sys.exit(1)
