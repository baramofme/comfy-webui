"""Lazy per-file model provisioning for comfy-webui chain injectors.

The image-gen chain injectors reference safetensors by bare filename and pass
that name straight to ``LoraLoaderModelOnly`` / model-loader nodes, but nothing
in this checkout ever fetched those files: ``utils/app_utils.py`` was absent,
``ensure_file_downloaded`` had zero definitions, and no code consumed the
``file_list.yaml`` manifests at all. Every injector therefore swallowed the
missing import with ``try: from utils.app_utils import ensure_file_downloaded
/ except ImportError: ensure_file_downloaded = None`` and silently no-op'd.

This module closes that gap. Given a filename it:

1. resolves the entry across every ``file_list.yaml`` manifest shipped under
   ``<app_root>/yaml`` and walked from ``<app_root>/module`` (the same manifests
   :mod:`comfy_webui_core.model_downloader` reads), where the manifest category
   *is* the ComfyUI ``models/<category>`` subdirectory;
2. maps it to ``COMFYUI_PATH/models/<category>/<filename>`` -- exactly the
   directory the ComfyUI backend loads from, so the loader node finds the file
   by name;
3. if the file is already present it is a no-op that returns the path; otherwise
   it fetches it from HuggingFace (``hf_hub_download`` when an ``HUGGINGFACE_TOKEN``
   is configured -- gated repos require it -- falling back to a streamed
   ``requests`` download of the public ``resolve`` URL);
4. returns the absolute local path on success and raises a clear exception on
   failure. It never silently returns ``None``.
"""

from __future__ import annotations

import os
import shutil
import threading

import yaml
import requests
from tqdm import tqdm


# --------------------------------------------------------------------------- #
# Configuration. Reuse the installed comfy-webui-core values when present so
# this module and model_downloader resolve the *same* paths and token. Guard the
# import so a pure headless/test context without the core package still works.
# --------------------------------------------------------------------------- #
try:  # pragma: no cover - depends on the installed core package
    from comfy_webui_core.config import COMFYUI_PATH, HUGGINGFACE_TOKEN
    from comfy_webui_core.context import get_app_root
except Exception:  # noqa: BLE001 - any import-time failure is tolerated here
    COMFYUI_PATH = os.getenv("COMFYUI_PATH", "")
    HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")

    def get_app_root() -> str:
        env_root = os.getenv("COMFY_WEBUI_APP_ROOT")
        if env_root and os.path.isdir(env_root):
            return os.path.abspath(env_root)
        return os.getcwd()


# --------------------------------------------------------------------------- #
# Manifest index. Built lazily (first call) and cached for the process. A lock
# makes the lazy build safe if several injectors call concurrently.
# --------------------------------------------------------------------------- #
_index_cache: dict | None = None
_index_lock = threading.Lock()


def _candidate_manifest_paths() -> list[str]:
    """Every ``file_list.yaml`` this checkout exposes, global-first."""
    root = get_app_root()
    candidates: list[str] = []

    global_path = os.path.join(root, "yaml", "file_list.yaml")
    if os.path.isfile(global_path):
        candidates.append(global_path)

    module_dir = os.path.join(root, "module")
    if os.path.isdir(module_dir):
        for current_root, _dirs, files in os.walk(module_dir):
            if "file_list.yaml" in files:
                candidates.append(os.path.join(current_root, "file_list.yaml"))

    return candidates


def _build_index() -> dict:
    """Map ``filename -> {category, source, repo_id, repository_file_path, ...}``.

    The first manifest to declare a filename wins (manifests can legitimately
    repeat a file across categories; we keep the first occurrence, matching how
    the backend would resolve it).
    """
    index: dict = {}
    for path in _candidate_manifest_paths():
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except Exception as exc:  # noqa: BLE001
            print(f"[app_utils] warning: could not parse {path}: {exc}")
            continue

        if not isinstance(data, dict) or "file" not in data:
            continue

        for category, entries in data["file"].items():
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                filename = entry.get("filename")
                if not filename:
                    continue
                index.setdefault(
                    filename,
                    {
                        "category": category,
                        "source": entry.get("source", "hf"),
                        "repo_id": entry.get("repo_id"),
                        "repository_file_path": entry.get("repository_file_path"),
                        "model_version_id": entry.get("model_version_id"),
                    },
                )
    return index


def _get_index() -> dict:
    global _index_cache
    if _index_cache is None:
        with _index_lock:
            if _index_cache is None:  # re-check under lock
                _index_cache = _build_index()
    return _index_cache


def _resolve_record(filename: str) -> dict:
    record = _get_index().get(filename)
    if record is None:
        raise FileNotFoundError(
            f"ensure_file_downloaded: '{filename}' is not declared in any "
            f"file_list.yaml manifest. Add it under 'file/<category>' or supply "
            f"the file by hand."
        )
    return record


# --------------------------------------------------------------------------- #
# Download backends.
# --------------------------------------------------------------------------- #
def _hf_public_url(record: dict) -> str:
    return (
        f"https://huggingface.co/{record['repo_id']}"
        f"/resolve/main/{record['repository_file_path']}"
    )


def _download_via_hf_hub(record: dict, destination_path: str) -> None:
    from huggingface_hub import hf_hub_download

    cached_path = hf_hub_download(
        repo_id=record["repo_id"],
        filename=record["repository_file_path"],
        token=HUGGINGFACE_TOKEN or None,
    )
    shutil.copy2(cached_path, destination_path)


def _download_via_requests(url: str, destination_path: str) -> None:
    tmp_path = f"{destination_path}.part"
    with requests.get(url, stream=True, timeout=30) as response:
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))
        with open(tmp_path, "wb") as fh, tqdm(
            total=total_size or None,
            unit="iB",
            unit_scale=True,
            desc=f"Downloading {os.path.basename(destination_path)}",
            leave=False,
        ) as pbar:
            for chunk in response.iter_content(chunk_size=1 << 16):
                if chunk:
                    pbar.update(len(chunk))
                    fh.write(chunk)

    downloaded = os.path.getsize(tmp_path)
    if total_size and downloaded != total_size:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise IOError(
            f"downloaded size {downloaded} != expected {total_size} for {url}"
        )

    os.replace(tmp_path, destination_path)


# --------------------------------------------------------------------------- #
# Public API.
# --------------------------------------------------------------------------- #
def ensure_file_downloaded(filename: str) -> str:
    """Return an absolute local path for ``filename``, fetching it if absent.

    Raises a clear exception (never ``None``) when the filename is unknown to
    the manifests, the destination cannot be created, or every download method
    fails. An already-present file is a no-op that just returns its path.
    """
    record = _resolve_record(filename)
    category = record["category"]

    destination_dir = os.path.join(COMFYUI_PATH, "models", category)
    destination_path = os.path.join(destination_dir, filename)

    if os.path.isfile(destination_path) and os.path.getsize(destination_path) > 0:
        return destination_path

    try:
        os.makedirs(destination_dir, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f"ensure_file_downloaded: cannot create '{destination_dir}' for "
            f"'{filename}': {exc}"
        ) from exc

    source = record["source"]

    if source == "hf":
        public_url = _hf_public_url(record)

        # Gated repos are only reachable through the Hub library with a token.
        if HUGGINGFACE_TOKEN:
            try:
                _download_via_hf_hub(record, destination_path)
                return destination_path
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[app_utils] hf_hub download failed for '{filename}': {exc}; "
                    f"falling back to public requests URL."
                )

        try:
            _download_via_requests(public_url, destination_path)
            return destination_path
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                f"ensure_file_downloaded: HuggingFace download failed for "
                f"'{filename}' ({public_url}): {exc}"
            ) from exc

    if source == "civitai":
        raise NotImplementedError(
            f"ensure_file_downloaded: civitai provisioning is not implemented; "
            f"declare '{filename}' as an 'hf' entry or download it manually."
        )

    raise RuntimeError(
        f"ensure_file_downloaded: unsupported source '{source}' for '{filename}'"
    )


def lookup_file_info(filename: str) -> dict:
    """Expose the resolved manifest record (handy for debugging/tests)."""
    return _resolve_record(filename)
