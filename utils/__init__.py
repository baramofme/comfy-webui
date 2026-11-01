"""Host-application helper package for comfy-webui.

Kept intentionally light: re-exports nothing heavy so importing `utils`
never triggers network or config side effects. Concrete helpers live in
submodules such as :mod:`utils.app_utils`.
"""
