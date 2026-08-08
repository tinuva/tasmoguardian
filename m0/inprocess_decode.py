#!/usr/bin/env python3
"""M0 prototype: invoke decode-config in-process (import, not subprocess).

decode-config ships as a single script (bin/decode-config.py) with global
ARGS state, module-level SETTINGS tables, and a log() that may sys.exit.
This wrapper loads it once via importlib and drives the same pipeline the
__main__ block uses:

    decrypt_encrypt -> get_config_info -> bin2mapping(raw) -> bin2mapping()

Findings recorded at bottom of file after running against a real device
backup.
"""
import importlib.util
import json
import sys
import types


def load_decode_config(script_path: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("decode_config", script_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["decode_config"] = mod
    spec.loader.exec_module(mod)  # only defs run; work is under __main__ guard
    # parseargs() reads sys.argv (configargparse); feed it a dummy source
    # to obtain the defaults ARGS the module functions expect
    # (jsonhidepw, cmnduseruleconcat, ...).
    argv_backup = sys.argv
    try:
        sys.argv = [script_path, "--source", "dummy.dmp"]
        mod.ARGS = mod.parseargs()
    finally:
        sys.argv = argv_backup
    return mod


def decode_dmp(mod: types.ModuleType, dmp_bytes: bytes) -> dict:
    # NOTE: module functions (exec_function, scriptread, ...) read the
    # module-global CONFIG dict, so we must populate mod.CONFIG, not a
    # local. This makes decoding non-reentrant -> serialize with a lock
    # (or run in a process pool) in the real backend.
    config = mod.CONFIG
    config.clear()
    config["encode"] = dmp_bytes
    if mod.config_has_settings_header(dmp_bytes):
        config["header"] = dmp_bytes[0:16]
        config["decode"] = mod.decrypt_encrypt(dmp_bytes[16:], has_header=True)
    else:
        config["header"] = None
        config["decode"] = mod.decrypt_encrypt(dmp_bytes, has_header=False)
    config["info"] = mod.get_config_info(config["decode"])
    # two-pass mapping, same as __main__: raw first (function macros need it)
    config["valuemapping"] = mod.bin2mapping(config, raw=True)
    config["groupmapping"] = mod.bin2mapping(config, raw=False)
    return config["groupmapping"]


if __name__ == "__main__":
    script = sys.argv[1] if len(sys.argv) > 1 else ".venv/bin/decode-config.py"
    dmp = sys.argv[2] if len(sys.argv) > 2 else "backup1.dmp"
    mod = load_decode_config(script)
    with open(dmp, "rb") as f:
        mapping = decode_dmp(mod, f.read())
    print(json.dumps(mapping, sort_keys=True, indent=2, default=str)[:400])
    print("...")
    print(f"keys: {len(mapping)}")
