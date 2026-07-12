"""In-process decode-config integration.

decode-config ships as a single script (bin/decode-config.py) with
module-global state (CONFIG, ARGS) and a log() that may sys.exit — see
M0 findings. We load it via importlib inside a dedicated single-worker
process pool: this sidesteps the non-reentrant globals and SystemExit
behavior, and keeps the event loop unblocked.

Public API (async):
    decode_dmp_bytes(dmp: bytes) -> dict   decoded config mapping
"""
import asyncio
import importlib.util
import sys
import sysconfig
import types
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

_MODULE: types.ModuleType | None = None
_EXECUTOR: ProcessPoolExecutor | None = None


def _find_script() -> Path:
    """Locate the pip-installed decode-config.py script."""
    candidates = [
        Path(sys.executable).parent / "decode-config.py",
        Path(sysconfig.get_path("scripts")) / "decode-config.py",
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError(
        f"decode-config.py not found; looked in {[str(c) for c in candidates]}"
    )


def _load_module() -> types.ModuleType:
    global _MODULE
    if _MODULE is not None:
        return _MODULE
    script = _find_script()
    spec = importlib.util.spec_from_file_location("decode_config", script)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["decode_config"] = mod
    spec.loader.exec_module(mod)  # defs only; work is under __main__ guard
    # parseargs() reads sys.argv and requires a source arg; feed a dummy
    # to obtain defaults (jsonhidepw, cmnduseruleconcat, ...).
    argv_backup = sys.argv
    try:
        sys.argv = [str(script), "--source", "dummy.dmp", "--json-show-pw"]
        mod.ARGS = mod.parseargs()
    finally:
        sys.argv = argv_backup
    _MODULE = mod
    return mod


def _decode_sync(dmp_bytes: bytes) -> dict:
    """Runs inside the worker process. Returns the decoded mapping."""
    mod = _load_module()
    # Functions read the module-global CONFIG dict (non-reentrant).
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
    # two-pass mapping, same as the CLI __main__ path
    config["valuemapping"] = mod.bin2mapping(config, raw=True)
    mapping = mod.bin2mapping(config, raw=False)
    # bin2mapping injects a 'header' metadata key (decode-config's own
    # crc/env/timestamp) — not device config; drop it.
    mapping.pop("header", None)
    return mapping


class DecodeError(Exception):
    pass


def _executor() -> ProcessPoolExecutor:
    global _EXECUTOR
    if _EXECUTOR is None:
        _EXECUTOR = ProcessPoolExecutor(max_workers=1)
    return _EXECUTOR


async def decode_dmp_bytes(dmp_bytes: bytes) -> dict:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(_executor(), _decode_sync, dmp_bytes)
    except SystemExit as exc:  # decode-config log() exits on fatal errors
        raise DecodeError(f"decode-config aborted (exit {exc.code})") from exc
    except Exception as exc:
        raise DecodeError(str(exc)) from exc


def shutdown() -> None:
    global _EXECUTOR
    if _EXECUTOR is not None:
        _EXECUTOR.shutdown(wait=False, cancel_futures=True)
        _EXECUTOR = None
