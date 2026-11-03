# Graph Report - comfy-webui  (2026-11-04)

## Corpus Check
- 227 files · ~518,593 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1138 nodes · 1689 edges · 116 communities (101 shown, 15 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 18 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ae0e7874`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 102|Community 102]]
- [[_COMMUNITY_Community 106|Community 106]]
- [[_COMMUNITY_Community 107|Community 107]]
- [[_COMMUNITY_Community 108|Community 108]]
- [[_COMMUNITY_Community 109|Community 109]]
- [[_COMMUNITY_Community 110|Community 110]]
- [[_COMMUNITY_Community 111|Community 111]]
- [[_COMMUNITY_Community 112|Community 112]]
- [[_COMMUNITY_Community 113|Community 113]]
- [[_COMMUNITY_Community 114|Community 114]]
- [[_COMMUNITY_Community 115|Community 115]]

## God Nodes (most connected - your core abstractions)
1. `process_inputs()` - 32 edges
2. `apply_reference_tokens()` - 30 edges
3. `create_ui()` - 26 edges
4. `apply_dialog_prefixes()` - 25 edges
5. `TestReferenceTokens` - 24 edges
6. `ensure_file_downloaded()` - 22 edges
7. `_load_yaml()` - 16 edges
8. `OptimizerTestCase` - 16 edges
9. `make_not_found_error()` - 14 edges
10. `load_model_config()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `test_manifest_lookup()` --calls--> `lookup_file_info()`  [EXTRACTED]
  tests/smoke_app_utils.py → utils/app_utils.py
- `test_unknown_filename_raises_clearly()` --calls--> `lookup_file_info()`  [EXTRACTED]
  tests/smoke_app_utils.py → utils/app_utils.py
- `test_file_lands_in_models_loras()` --calls--> `ensure_file_downloaded()`  [EXTRACTED]
  tests/smoke_app_utils.py → utils/app_utils.py
- `inject()` --calls--> `ensure_file_downloaded()`  [EXTRACTED]
  module/imagegen/chain_injectors/flux3_prompt_upsampler_injector.py → utils/app_utils.py
- `inject()` --calls--> `ensure_file_downloaded()`  [EXTRACTED]
  module/imagegen/chain_injectors/krea2_identity_edit_injector.py → utils/app_utils.py

## Import Cycles
- None detected.

## Communities (116 total, 15 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.06
Nodes (63): MCP Module for ImageGen in comfy-webui. Exposes MCP_FUNCTIONS from .mcp_tools pa, _apply_multiangle_ui_values(), _download_image_from_url(), DummyProgress, _execute_imagegen_pipeline(), _get_ipadapter_presets_by_arch(), _get_public_base_url(), _load_yaml() (+55 more)

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (50): create_event_handlers(), create_ui(), Blocks, load_architectures_config(), load_constants_config(), load_controlnet_models(), load_features_config(), load_ipadapter_presets() (+42 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (46): create_node(), inject(), FLUX.3 Prompt Upsampler Chain Injector.  This injector integrates the FLUX.3 pro, Create a workflow node dictionary with fallback template generation., Inject FLUX.3 prompt upsampler nodes into the target generation workflow., create_node(), inject(), create_node() (+38 more)

### Community 3 - "Community 3"
Cohesion: 0.08
Nodes (38): MCP Module for MiniMax-H3 Video Generation in comfy-webui. Exposes MCP_FUNCTIONS, _download_file_from_url(), _download_image_from_url(), _execute_h3_pipeline(), _lora_entry_to_prefixed(), _normalize_lora_entries(), _parse_audio_param(), _parse_image_param() (+30 more)

### Community 4 - "Community 4"
Cohesion: 0.08
Nodes (34): process_inputs(), MCP Module for Lightricks LTX-2.5 Video Generation in comfy-webui. Exposes MCP_F, create_event_handlers(), Blocks, _download_audio_from_url(), _download_image_from_url(), _execute_ltx2_5_pipeline(), _parse_audio_param() (+26 more)

### Community 5 - "Community 5"
Cohesion: 0.09
Nodes (14): apply_dialog_prefixes(), dialogue_line_content(), has_dialogue_lines(), r"""`#` dialogue-prefix preprocessing (ported from ComfyUI-MiniMaxH3-Easy).  Sou, True when the prompt contains at least one `#` dialogue line., Rewrite `#` dialogue segments into the target model's audio convention.      tar, r"""Return the dialogue text of `line` if it is a `#` dialogue line, else None., Format one dialogue segment as an LTX quoted-speech cue sentence. (+6 more)

### Community 6 - "Community 6"
Cohesion: 0.15
Nodes (31): process_inputs(), Generic input processor for all image generation tasks based on unified_recipe.y, process_inputs(), process_conditioning_inputs(), process_controlnet_inputs(), process_embedding_inputs(), process_flux1_ipadapter_inputs(), process_flux3_prompt_upsampler_inputs() (+23 more)

### Community 7 - "Community 7"
Cohesion: 0.11
Nodes (17): 1. Adding a New Feature, 2. Removing Features, Automated long-context workflows, Comfy web UI — A Modular, Recipe-Driven "Workflow-as-a-Service (WaaS)" Platform for ComfyUI, ⚙️ Core Configuration Files (`*.yaml`), 🧩 Development and Feature Extension Guide, Development Status, 💡 For Developers: Discover the Comfy web UI Core Framework (+9 more)

### Community 8 - "Community 8"
Cohesion: 0.14
Nodes (13): create_event_handlers(), create_ui(), on_select_job(), Any, Blocks, Fetches completed jobs from the output folder and formats them for the UI., Handles row selection in the DataFrame to update the preview., Binds event handlers for the History UI module. (+5 more)

### Community 9 - "Community 9"
Cohesion: 0.20
Nodes (9): process_inputs(), _3DGen_Hunyuan3D_2(), _download_and_decode_image(), Image, Request, Generates a 3D model from a single input image using the Hunyuan3D-2 model., create_event_handlers(), Blocks (+1 more)

### Community 10 - "Community 10"
Cohesion: 0.20
Nodes (9): process_inputs(), _3DGen_Hunyuan3D_2_multiview(), _download_and_decode_image(), Image, Request, Generates a 3D model from three input images (front, back, left) using the Hunyu, create_event_handlers(), Blocks (+1 more)

### Community 11 - "Community 11"
Cohesion: 0.20
Nodes (9): process_inputs(), _3DGen_Pixal3D_TRELLIS_2(), _download_and_decode_image(), Image, Request, Generates a 3D model from a single input image using TRELLIS-2 / Pixal3D with au, create_event_handlers(), Blocks (+1 more)

### Community 12 - "Community 12"
Cohesion: 0.18
Nodes (12): process_inputs(), Processes UI inputs and assembles the ComfyUI workflow to generate an XML prompt, create_character_ui(), create_event_handlers(), create_ui(), get_main_output_components(), Blocks, Creates UI components for a single character, including an enable checkbox. (+4 more)

### Community 13 - "Community 13"
Cohesion: 0.28
Nodes (12): _combine_conditioning(), create_node(), inject(), _inject_krea2_anygles(), _inject_qwenmultiangle(), Multi-angle camera conditioning injector (comfy-webui).  ADDITIVE / COMPLEMENTAR, Numeric camera node -> translated camera prompt -> CLIP conditioning     that is, Subject re-projection chain. Needs a source image. Returns (model_ref,     posit (+4 more)

### Community 14 - "Community 14"
Cohesion: 0.24
Nodes (6): process_inputs(), AudioGen_MiniMax_Music_3(), Request, Generates a music clip from a style description and optional structured lyrics u, create_event_handlers(), Blocks

### Community 15 - "Community 15"
Cohesion: 0.24
Nodes (5): process_inputs(), create_event_handlers(), create_ui(), get_preprocessor_choices(), Blocks

### Community 16 - "Community 16"
Cohesion: 0.33
Nodes (6): extract_audio_ffmpeg(), merge_video_audio_ffmpeg(), process_inputs(), create_event_handlers(), Blocks, run_generation()

### Community 17 - "Community 17"
Cohesion: 0.33
Nodes (6): extract_audio_ffmpeg(), merge_video_audio_ffmpeg(), process_inputs(), create_event_handlers(), Blocks, run_generation()

### Community 18 - "Community 18"
Cohesion: 0.31
Nodes (5): process_inputs(), process_uso_reference_inputs(), process_uso_style_reference_inputs(), create_event_handlers(), Blocks

### Community 19 - "Community 19"
Cohesion: 0.28
Nodes (4): process_inputs(), create_event_handlers(), process_inputs(), Blocks

### Community 20 - "Community 20"
Cohesion: 0.32
Nodes (4): process_inputs(), create_event_handlers(), Blocks, run_generation()

### Community 21 - "Community 21"
Cohesion: 0.32
Nodes (4): process_inputs(), create_event_handlers(), Blocks, run_generation()

### Community 22 - "Community 22"
Cohesion: 0.32
Nodes (4): process_inputs(), create_event_handlers(), Blocks, run_generation()

### Community 23 - "Community 23"
Cohesion: 0.32
Nodes (4): process_inputs(), create_event_handlers(), Blocks, run_generation()

### Community 24 - "Community 24"
Cohesion: 0.32
Nodes (4): process_inputs(), create_event_handlers(), Blocks, run_generation()

### Community 25 - "Community 25"
Cohesion: 0.32
Nodes (4): process_inputs(), create_event_handlers(), Blocks, run_generation()

### Community 26 - "Community 26"
Cohesion: 0.32
Nodes (4): process_inputs(), create_event_handlers(), process_inputs(), Blocks

### Community 27 - "Community 27"
Cohesion: 0.32
Nodes (4): process_inputs(), create_event_handlers(), process_inputs(), Blocks

### Community 28 - "Community 28"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 29 - "Community 29"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 30 - "Community 30"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 31 - "Community 31"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 32 - "Community 32"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 33 - "Community 33"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 34 - "Community 34"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 35 - "Community 35"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 36 - "Community 36"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 37 - "Community 37"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 38 - "Community 38"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 39 - "Community 39"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 40 - "Community 40"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 41 - "Community 41"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 42 - "Community 42"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 43 - "Community 43"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 44 - "Community 44"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 45 - "Community 45"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 46 - "Community 46"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 47 - "Community 47"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 48 - "Community 48"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 49 - "Community 49"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 50 - "Community 50"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 51 - "Community 51"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 52 - "Community 52"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 53 - "Community 53"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 54 - "Community 54"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 55 - "Community 55"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 56 - "Community 56"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 57 - "Community 57"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 58 - "Community 58"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 59 - "Community 59"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 60 - "Community 60"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 61 - "Community 61"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 62 - "Community 62"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 63 - "Community 63"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 64 - "Community 64"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 65 - "Community 65"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 66 - "Community 66"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 67 - "Community 67"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 68 - "Community 68"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 69 - "Community 69"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 70 - "Community 70"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 71 - "Community 71"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 72 - "Community 72"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 73 - "Community 73"
Cohesion: 0.33
Nodes (3): process_inputs(), create_event_handlers(), Blocks

### Community 74 - "Community 74"
Cohesion: 0.83
Nodes (3): discover_and_register_mcp_modules(), main(), Blocks

### Community 75 - "Community 75"
Cohesion: 0.83
Nodes (3): inject(), load_model_config(), load_pid_config()

### Community 106 - "Community 106"
Cohesion: 0.09
Nodes (9): apply_reference_tokens(), has_reference_tokens(), r"""`@` media-reference token resolution (ported from ComfyUI-MiniMaxH3-Easy)., Rewrite `@이미지N` / `@동영상N` index tokens into the target model's reference convent, True when the prompt carries at least one `@이미지N` / `@동영상N` index token.      `@, Whether THIS target has at least one token it would actually rewrite.      h3, _resolvable_for_target(), Unit tests for the `@이미지N` media-reference index resolver (media_ref_prompt). (+1 more)

### Community 107 - "Community 107"
Cohesion: 0.08
Nodes (36): calculate_h3_frame_length(), _optimize_h3_prompt(), _optimizer_enabled(), process_h3_guide_inputs(), process_inputs(), Gate the prompt-optimizer pre-processing step.      Enabled by default. Set ``PR, Rewrite the H3-tag-bearing prompt via the shared optimizer.      Purely a pre-pr, Converts duration (seconds) at 24fps to a valid frame length     snapped up to t (+28 more)

### Community 108 - "Community 108"
Cohesion: 0.11
Nodes (11): make_ui_values(), OptimizerTestCase, Unit tests for the prompt-optimizer wiring on the comfy-webui side and its failu, The wrapper adds defense-in-depth: even an unexpected raise from the optimizer's, Disabled or empty prompts pass straight through with no HTTP call., A minimal T2VA ui_values (no frames / media) — enough to drive process_inputs., Shared fixture: stub the assembler, clear the cache, isolate the env gate,     a, TestCacheApi (+3 more)

### Community 109 - "Community 109"
Cohesion: 0.18
Nodes (5): Call process_inputs with the optimizer HTTP layer swapped for ``monkey_http``., Criterion (2): process_inputs calls the optimizer; the rewritten prompt is what, Criterion (3): on optimizer failure the ORIGINAL (token-converted) prompt is kep, TestProcessInputsFailure, TestProcessInputsSuccess

### Community 112 - "Community 112"
Cohesion: 0.29
Nodes (4): A disabled gate passes the prompt through byte-identical (after the token     co, The prompt as it is handed to the optimizer: AFTER the `#`/`@` -> `<d>`/`<Pictur, TestProcessInputsDisabled, token_converted()

## Knowledge Gaps
- **11 isolated node(s):** `Development Status`, `Security Advisory`, `✨ Key Features`, `Automated long-context workflows`, `💡 For Developers: Discover the Comfy web UI Core Framework` (+6 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `process_inputs()` connect `Community 6` to `Community 0`, `Community 1`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Why does `apply_dialog_prefixes()` connect `Community 5` to `Community 107`, `Community 4`?**
  _High betweenness centrality (0.010) - this node is a cross-community bridge._
- **Why does `process_inputs()` connect `Community 4` to `Community 106`, `Community 5`?**
  _High betweenness centrality (0.009) - this node is a cross-community bridge._
- **Are the 18 inferred relationships involving `create_ui()` (e.g. with `create_conditioning_ui()` and `create_controlnet_ui()`) actually correct?**
  _`create_ui()` has 18 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Generates a 3D model from a single input image using the Hunyuan3D-2 model.`, `Generates a 3D model from three input images (front, back, left) using the Hunyu`, `Generates a 3D model from a single input image using TRELLIS-2 / Pixal3D with au` to the rest of the system?**
  _166 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.06394027913015254 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.09508196721311475 - nodes in this community are weakly interconnected._