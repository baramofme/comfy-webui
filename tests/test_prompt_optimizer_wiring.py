"""Unit tests for the prompt-optimizer wiring on the comfy-webui side and its
failure-fallback / idempotency-cache behaviour.

Run: python -m unittest tests.test_prompt_optimizer_wiring   (from the repo root,
with the .venv interpreter: .venv/bin/python -m unittest ...)

Two integration points share one optimizer module (module/video_gen/prompt_optimizer.py):
  * comfy-webui ``video_gen/H3/h3_logic.process_inputs`` — rewrites the prompt before it
    reaches the ComfyUI workflow assembler;
  * the Dock composer (separate repo, covered by its own TS test) — rewrites before submit.
This file exercises the comfy-webui point plus the engine itself. The LLM endpoint is
mocked throughout: nothing here contacts the network.

The real ``WorkflowAssembler.assemble`` needs a LIVE ComfyUI backend (/object_info) to
resolve node templates, so this suite stubs ``assemble`` and captures the ``local_ui_values``
handed to it — i.e. exactly the values that flow into the graph. The recipe maps
``prompt -> "minimax_h3:prompt"``, so whatever prompt the assembler receives is what
reaches the H3 node's prompt input.

Acceptance criteria exercised:
  (2) process_inputs calls the optimizer and the REWRITTEN prompt reaches the workflow;
  (3) HTTP failure falls through to the ORIGINAL prompt with a warning log and never
      raises out of process_inputs (the failure-fallback path is explicitly tested);
  (4) the sha256 cache returns the cached rewrite on a repeated identical prompt and
      makes no second HTTP call.
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import requests  # noqa: E402

from module.video_gen.H3 import h3_logic  # noqa: E402
from module.video_gen import prompt_optimizer as po  # noqa: E402

# The canned rewrite a mocked optimizer returns. It keeps the H3 ``<Picture N>``/``<d>``
# tags so a test can prove they survive the round-trip into the graph input.
CANNED_TAGS = "REWRITTEN::cinematic city alley <Picture 1> <d>안녕</d>"

RAW_PROMPT = "원문 프롬프트 @이미지1가 골목.\n#안녕"


def token_converted(prompt):
    """The prompt as it is handed to the optimizer: AFTER the `#`/`@` -> `<d>`/`<Picture N>`
    conversion that runs in process_inputs before the optimizer step."""
    return h3_logic.apply_reference_tokens(
        h3_logic.apply_dialog_prefixes(prompt, "h3"), "h3"
    )


class _StubAssembler:
    """Captures the exact local_ui_values the graph-assembly step receives."""

    def __init__(self, recipe_path, base_path=None):
        self.recipe_path = recipe_path
        self.captured = {}

    def assemble(self, local_ui_values):
        self.captured = local_ui_values
        return {"__stub__": True, "prompt_seen": local_ui_values.get("prompt")}


def make_ui_values(prompt):
    """A minimal T2VA ui_values (no frames / media) — enough to drive process_inputs."""
    return {
        "task": "T2VA",
        "prompt": prompt,
        "width": 0,
        "height": 0,
        "resolution": "768p",
        "aspect_ratio": "16:9 (Landscape)",
        "steps": 20,
        "duration": 3.0,
        "seed": 1234,
        "loras": [],
        "h3_guide_images": [],
        "h3_guides": [],
        "first_frame": None,
        "last_frame": None,
        "ref_images": [],
    }


class OptimizerTestCase(unittest.TestCase):
    """Shared fixture: stub the assembler, clear the cache, isolate the env gate,
    and guarantee the optimizer HTTP layer never reaches a real socket."""

    def setUp(self):
        # A fresh stub per test; capture its received values.
        self.stub = _StubAssembler("recipe", base_path="base")
        h3_logic.WorkflowAssembler = self.stub
        # Deterministic cache state for every test.
        po.cache_clear()
        # Default-enabled gate; tests that need a specific value set it themselves.
        os.environ.pop("PROMPT_OPTIMIZER_ENABLED", None)
        # Remember the real HTTP seam so every test restores it.
        self._orig_http = po.optimizer_http_json
        self._orig_requests_post = po.requests.post

    def tearDown(self):
        po.optimizer_http_json = self._orig_http
        po.requests.post = self._orig_requests_post
        os.environ.pop("PROMPT_OPTIMIZER_ENABLED", None)
        po.cache_clear()

    def _restore_env(self):
        os.environ.pop("PROMPT_OPTIMIZER_ENABLED", None)

    def run_process_inputs(self, prompt, monkey_http):
        """Call process_inputs with the optimizer HTTP layer swapped for ``monkey_http``."""
        po.optimizer_http_json = monkey_http
        workflow, _ = h3_logic.process_inputs(make_ui_values(prompt), seed_override=1234)
        prompt_at_assembler = (self.stub.captured or {}).get("prompt")
        if not isinstance(prompt_at_assembler, str):
            prompt_at_assembler = ""
        return workflow, prompt_at_assembler


class TestWiringStructure(OptimizerTestCase):
    def test_h3_logic_imports_optimize_prompt(self):
        self.assertTrue(callable(getattr(h3_logic, "optimize_prompt", None)))

    def test_h3_logic_exposes_wrapper(self):
        self.assertTrue(callable(h3_logic._optimize_h3_prompt))

    def test_module_vendored_at_video_gen_path(self):
        self.assertTrue(po.__file__.endswith("module/video_gen/prompt_optimizer.py"))

    def test_recipe_routes_prompt_into_h3_node(self):
        import yaml

        recipe_path = os.path.join(
            h3_logic.MODULE_DIR, "workflow_recipes", "h3_fl2va_recipe.yaml"
        )
        with open(recipe_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        ui_map = data.get("ui_map") or {}
        self.assertEqual(ui_map.get("prompt"), "minimax_h3:prompt")


class TestOptimizerGate(OptimizerTestCase):
    def _check(self, value, expected):
        if value is None:
            os.environ.pop("PROMPT_OPTIMIZER_ENABLED", None)
        else:
            os.environ["PROMPT_OPTIMIZER_ENABLED"] = value
        self.assertEqual(h3_logic._optimizer_enabled(), expected)

    def test_unset_is_enabled(self):
        self._check(None, True)

    def test_one_is_enabled(self):
        self._check("1", True)

    def test_zero_is_disabled(self):
        self._check("0", False)

    def test_off_is_disabled(self):
        self._check("off", False)

    def test_false_is_disabled(self):
        self._check("false", False)

    def test_no_is_disabled(self):
        self._check("no", False)

    def test_empty_string_is_disabled(self):
        self._check("", False)


class TestProcessInputsSuccess(OptimizerTestCase):
    """Criterion (2): process_inputs calls the optimizer; the rewritten prompt is what
    reaches the workflow-assembly step (and therefore the H3 node's prompt input)."""

    def test_rewritten_prompt_reaches_assembler(self):
        def http_ok(api_url, api_key, model, api_format, system_prompt, user_prompt,
                    timeout_seconds=None, max_output_tokens=None):
            return CANNED_TAGS

        _, prompt_at_assembler = self.run_process_inputs(RAW_PROMPT, http_ok)
        self.assertEqual(prompt_at_assembler, CANNED_TAGS)

    def test_original_replaced_at_assembler(self):
        def http_ok(*a, **k):
            return CANNED_TAGS

        _, prompt_at_assembler = self.run_process_inputs(RAW_PROMPT, http_ok)
        self.assertNotIn("원문 프롬프트", prompt_at_assembler)

    def test_picture_tag_survives_into_graph_input(self):
        def http_ok(*a, **k):
            return CANNED_TAGS

        _, prompt_at_assembler = self.run_process_inputs(RAW_PROMPT, http_ok)
        self.assertIn("<Picture 1>", prompt_at_assembler)

    def test_dialogue_tag_survives_into_graph_input(self):
        def http_ok(*a, **k):
            return CANNED_TAGS

        _, prompt_at_assembler = self.run_process_inputs(RAW_PROMPT, http_ok)
        self.assertIn("<d>", prompt_at_assembler)
        self.assertIn("</d>", prompt_at_assembler)


class TestProcessInputsFailure(OptimizerTestCase):
    """Criterion (3): on optimizer failure the ORIGINAL (token-converted) prompt is kept,
    a warning is logged, and no exception escapes process_inputs."""

    def _http_fail(self, *a, **k):
        raise RuntimeError("simulated HTTP 502")

    def test_no_exception_escapes(self):
        # If process_inputs raised, this call would error out and fail the test.
        workflow, _ = self.run_process_inputs(RAW_PROMPT, self._http_fail)
        self.assertIsNotNone(workflow)

    def test_assembler_receives_original_token_converted_prompt(self):
        _, prompt_at_assembler = self.run_process_inputs(RAW_PROMPT, self._http_fail)
        self.assertEqual(prompt_at_assembler, token_converted(RAW_PROMPT))

    def test_raw_original_text_kept(self):
        _, prompt_at_assembler = self.run_process_inputs(RAW_PROMPT, self._http_fail)
        self.assertIn("원문 프롬프트", prompt_at_assembler)

    def test_rewrite_not_used_on_failure(self):
        _, prompt_at_assembler = self.run_process_inputs(RAW_PROMPT, self._http_fail)
        self.assertNotIn("REWRITTEN", prompt_at_assembler)

    def test_conversion_ran_before_optimizer(self):
        # The token conversion runs before the optimizer step, so the tags survive even
        # when the rewrite is discarded by the fallback.
        _, prompt_at_assembler = self.run_process_inputs(RAW_PROMPT, self._http_fail)
        self.assertIn("<Picture 1>", prompt_at_assembler)
        self.assertIn("<d>", prompt_at_assembler)

    def test_warning_logged_on_failure(self):
        with self.assertLogs("prompt_optimizer", level="WARNING") as captured:
            self.run_process_inputs(RAW_PROMPT, self._http_fail)
        self.assertTrue(
            any("optimization failed" in m or "using original prompt" in m
                for m in captured.output)
        )


class TestProcessInputsDisabled(OptimizerTestCase):
    """A disabled gate passes the prompt through byte-identical (after the token
    conversion) and makes no HTTP call at all."""

    def _http_must_not_be_called(self, *a, **k):
        raise AssertionError("HTTP call made while the gate is disabled")

    def test_byte_identical_after_conversion(self):
        os.environ["PROMPT_OPTIMIZER_ENABLED"] = "0"
        _, prompt_at_assembler = self.run_process_inputs(
            "raw raw raw @이미지2", self._http_must_not_be_called
        )
        self.assertEqual(prompt_at_assembler, token_converted("raw raw raw @이미지2"))

    def test_conversion_independent_of_gate(self):
        os.environ["PROMPT_OPTIMIZER_ENABLED"] = "0"
        _, prompt_at_assembler = self.run_process_inputs(
            "raw raw raw @이미지2", self._http_must_not_be_called
        )
        self.assertIn("<Picture 2>", prompt_at_assembler)


class TestWrapperDefenseInDepth(OptimizerTestCase):
    """The wrapper adds defense-in-depth: even an unexpected raise from the optimizer's
    public entry point falls back to the original prompt with a wrapper warning."""

    def test_unexpected_raise_falls_back_and_logs(self):
        original = "keep this prompt <Picture 1> <d>hi</d>"

        def boom(*a, **k):
            raise ValueError("optimizer blew up unexpectedly")

        # The wrapper calls optimize_prompt directly, not through process_inputs.
        h3_logic.optimize_prompt = boom
        try:
            with self.assertLogs("prompt_optimizer", level="WARNING") as captured:
                result = h3_logic._optimize_h3_prompt(original)
        finally:
            h3_logic.optimize_prompt = po.optimize_prompt
        self.assertEqual(result, original)
        self.assertTrue(any("wrapper failed" in m for m in captured.output))


class TestEngineSuccessAndCache(OptimizerTestCase):
    """Engine-level: mock the endpoint at ``requests.post`` so the REAL parser runs, and
    verify the thinking-block + code-fence strip, the sha256 cache, and the cache key.
    """

    THINKY = "<|think|>\nreasoning that must vanish\n<|/think|>\n```text\n" + \
             "A cinematic cat strides across the moon.\n```"
    CLEAN = "A cinematic cat strides across the moon."

    class _Resp:
        def __init__(self, payload, status=200):
            self._payload = payload
            self.status_code = status

        def raise_for_status(self):
            if self.status_code >= 400:
                err = requests.HTTPError(f"{self.status_code}")
                err.response = self
                raise err

        def json(self):
            return self._payload

        @property
        def text(self):
            return "upstream exploded"

    def _install_post(self, behaviour):
        calls = []
        po.requests.post = behaviour(calls)
        return calls

    def test_success_strips_thoughts_and_fences(self):
        def factory(calls):
            def post(url, *a, **k):
                calls.append(url)
                return self._Resp({"choices": [{"message": {"content": self.THINKY}}]})
            return post

        calls = self._install_post(factory)
        result = po.optimize_prompt("a cat on the moon", api_url="http://x/v1", model="m")
        self.assertEqual(result, self.CLEAN)
        self.assertEqual(len(calls), 1)
        self.assertTrue(calls[0].endswith("/v1/chat/completions"))

    def test_cache_hit_no_second_http_call(self):
        def factory(calls):
            def post(url, *a, **k):
                calls.append(url)
                return self._Resp({"choices": [{"message": {"content": self.THINKY}}]})
            return post

        calls = self._install_post(factory)
        first = po.optimize_prompt("cache me", api_url="http://x/v1", model="m")
        self.assertEqual(len(calls), 1)
        second = po.optimize_prompt("cache me", api_url="http://x/v1", model="m")
        # Criterion (4): the cached rewrite is returned without refetching.
        self.assertEqual(second, first)
        self.assertEqual(len(calls), 1, "a cache hit must not refetch")

    def test_different_prompt_refetches(self):
        def factory(calls):
            def post(url, *a, **k):
                calls.append(url)
                return self._Resp({"choices": [{"message": {"content": self.THINKY}}]})
            return post

        calls = self._install_post(factory)
        po.optimize_prompt("first", api_url="http://x/v1", model="m")
        po.optimize_prompt("second", api_url="http://x/v1", model="m")
        self.assertEqual(len(calls), 2)

    def test_result_flags(self):
        def factory(calls):
            def post(url, *a, **k):
                calls.append(url)
                return self._Resp({"choices": [{"message": {"content": self.THINKY}}]})
            return post

        self._install_post(factory)
        r1 = po.optimize_prompt_result("flag me", api_url="http://x/v1", model="m")
        self.assertEqual(r1["text"], self.CLEAN)
        self.assertTrue(r1["changed"])
        self.assertFalse(r1["cached"])
        r2 = po.optimize_prompt_result("flag me", api_url="http://x/v1", model="m")
        self.assertTrue(r2["cached"])

    def test_cache_key_is_prompt_sensitive(self):
        a = po._cache_key("a", "u", "", "m", "openai", po.DEFAULT_SYSTEM_PROMPT)
        b = po._cache_key("b", "u", "", "m", "openai", po.DEFAULT_SYSTEM_PROMPT)
        same = po._cache_key("a", "u", "", "m", "openai", po.DEFAULT_SYSTEM_PROMPT)
        self.assertNotEqual(a, b)
        self.assertEqual(a, same)


class TestEngineFallback(OptimizerTestCase):
    """Engine-level HTTP failure (criterion (3)): the original prompt is returned and a
    warning is logged; the richer result carries the reason for the UI banner."""

    def _raise_http_error(self):
        resp = TestEngineSuccessAndCache._Resp({}, status=500)
        err = requests.HTTPError("boom")
        err.response = resp
        return err

    def test_http_error_returns_original(self):
        def post(url, *a, **k):
            raise self._raise_http_error()

        po.requests.post = post
        result = po.optimize_prompt("keep me raw", api_url="http://x/v1", model="m")
        self.assertEqual(result, "keep me raw")

    def test_http_error_logs_warning(self):
        def post(url, *a, **k):
            raise self._raise_http_error()

        po.requests.post = post
        with self.assertLogs("prompt_optimizer", level="WARNING") as captured:
            po.optimize_prompt("keep me raw", api_url="http://x/v1", model="m")
        self.assertTrue(any("passing through original" in m for m in captured.output))

    def test_request_exception_returns_original_with_reason(self):
        def post(url, *a, **k):
            raise requests.ConnectionError("connection refused")

        po.requests.post = post
        result = po.optimize_prompt_result("keep me", api_url="http://x/v1", model="m")
        self.assertEqual(result["text"], "keep me")
        self.assertFalse(result["changed"])
        self.assertIn("error", result)

    def test_empty_response_treated_as_failure(self):
        def post(url, *a, **k):
            return TestEngineSuccessAndCache._Resp({"choices": [{"message": {"content": "   "}}]})

        po.requests.post = post
        result = po.optimize_prompt("x", api_url="http://x/v1", model="m")
        self.assertEqual(result, "x")


class TestEngineGuards(OptimizerTestCase):
    """Disabled or empty prompts pass straight through with no HTTP call."""

    def test_disabled_makes_no_http(self):
        def post(*a, **k):
            raise AssertionError("HTTP call made while disabled")

        po.requests.post = post
        self.assertEqual(po.optimize_prompt("bypass", enabled=False), "bypass")

    def test_empty_makes_no_http(self):
        def post(*a, **k):
            raise AssertionError("HTTP call made for an empty prompt")

        po.requests.post = post
        self.assertEqual(po.optimize_prompt("   "), "   ")


class TestCacheApi(OptimizerTestCase):
    def test_cache_size_and_clear(self):
        def post(url, *a, **k):
            return TestEngineSuccessAndCache._Resp(
                {"choices": [{"message": {"content": TestEngineSuccessAndCache.CLEAN}}]}
            )

        po.requests.post = post
        po.optimize_prompt("prompt one", api_url="http://x/v1", model="m")
        po.optimize_prompt("prompt two", api_url="http://x/v1", model="m")
        self.assertEqual(po.cache_size(), 2)
        cleared = po.cache_clear()
        self.assertEqual(cleared, 2)
        self.assertEqual(po.cache_size(), 0)


if __name__ == "__main__":
    unittest.main()
