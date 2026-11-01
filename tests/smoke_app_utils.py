"""Smoke test for ``utils.app_utils.ensure_file_downloaded``.

Runnable in two ways::

    # standalone, from anywhere (locates the repo root itself):
    python tests/smoke_app_utils.py

    # or under pytest from the repo root:
    pytest tests/smoke_app_utils.py

The primary check -- ``ensure_file_downloaded('krea2_style_reference.safetensors')``
-- is network-free when the LoRA is already present in the ComfyUI backend models
dir (the normal state). It only performs a real download when the file is absent.
"""

import os
import sys

# Make ``utils`` importable regardless of the cwd the test is invoked from by
# putting the repository root (the directory that contains app.py) on sys.path --
# exactly what running ``python app.py`` does via sys.path[0].
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from utils.app_utils import ensure_file_downloaded, lookup_file_info  # noqa: E402

LORA_NAME = "krea2_style_reference.safetensors"


def test_import_and_signature():
    assert callable(ensure_file_downloaded)


def test_manifest_lookup():
    record = lookup_file_info(LORA_NAME)
    # the manifest category must be the ComfyUI sub-directory it lands in
    assert record["category"] == "loras"
    assert record["source"] == "hf"
    assert record["repo_id"] == "ostris/krea2_turbo_style_reference"


def test_unknown_filename_raises_clearly():
    # silent None would be the old bug; an explicit exception is the contract
    try:
        lookup_file_info("definitely-not-a-real-file.safetensors")
    except FileNotFoundError:
        return
    raise AssertionError("unknown filename should raise FileNotFoundError")


def test_file_lands_in_models_loras():
    path = ensure_file_downloaded(LORA_NAME)
    assert path and os.path.isabs(path)
    assert path.endswith(os.path.join("models", "loras", LORA_NAME))
    assert os.path.isfile(path)
    assert os.path.getsize(path) > 0


if __name__ == "__main__":
    tests = [
        test_import_and_signature,
        test_manifest_lookup,
        test_unknown_filename_raises_clearly,
        test_file_lands_in_models_loras,
    ]
    failures = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL  {fn.__name__}: {exc}")
    if failures:
        print(f"\n{failures} smoke test(s) FAILED")
        sys.exit(1)
    print("\nall smoke tests passed")
