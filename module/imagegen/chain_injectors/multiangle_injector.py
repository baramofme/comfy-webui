"""
Multi-angle camera conditioning injector (comfy-webui).

ADDITIVE / COMPLEMENTARY to the existing prompt-token conditioning path.
This injector NEVER removes pos_prompt / neg_prompt CLIPTextEncode nodes; it
COMBINES camera-angle conditioning with them via ConditioningCombine, and
(optionally for krea2-anygles) re-routes the KSampler model through the
anygles model-patch chain.

Two sub-paths, each activated only when the corresponding numeric inputs are
present on the chain item:

  * qwenmultiangle  (no source image required; works for txt2img & img2img)
      QwenMultiangleCameraNode -> QwenMultiangleCameraTranslateNode (English
      pass-through) -> CLIPTextEncode -> ConditioningCombine into positive.

  * krea2_anygles  (requires a source image: re-renders the subject at a new
      camera angle; meaningful for img2img / reference-image runs)
      Krea2AnyblesLoadLoRA -> Krea2AnyblesCamera -> Krea2AnyblesEncode ->
      Krea2AnyblesModelPatch. The patched MODEL replaces the sampler model and
      the anygles positive conditioning is combined with the existing positive.

When neither sub-path's inputs are present (the default request shape), the
process-side returns an empty chain list and the injector is never invoked --
so the generated graph is byte-identical to the pre-existing behaviour
(zero regression).
"""

CHAIN_TYPE = "dynamic_multiangle_chains"


def create_node(assembler, class_type, title=None):
    try:
        node = assembler._get_node_template_from_api(class_type)
    except Exception:
        try:
            node = assembler._get_node_template(class_type)
        except Exception:
            node = {"inputs": {}, "class_type": class_type,
                    "_meta": {"title": title or class_type}}
    if title:
        node['_meta']['title'] = title
    return node


def _resolve_clip_connection(assembler, chain_definition, pos_prompt_name):
    """Resolve the CLIP connection to encode the camera-angle text against.

    Preferred: whatever CLIP currently feeds the positive prompt node, so the
    angle conditioning is produced by the SAME (possibly LoRA-weighted) text
    encoder as the user-prompt conditioning. Fallback: the recipe clip_source.
    """
    pos_id = assembler.node_map.get(pos_prompt_name)
    if pos_id and pos_id in assembler.workflow:
        cur = assembler.workflow[pos_id]['inputs'].get('clip')
        if cur:
            return cur
    clip_source_str = chain_definition.get('clip_source')
    if clip_source_str:
        node_name, idx = clip_source_str.split(':')
        if node_name in assembler.node_map:
            return [assembler.node_map[node_name], int(idx)]
    return None


def _resolve_vae_connection(assembler, chain_definition):
    vae_source_str = chain_definition.get('vae_source')
    if vae_source_str:
        node_name, idx = vae_source_str.split(':')
        if node_name in assembler.node_map:
            return [assembler.node_map[node_name], int(idx)]
    for node_id, node in assembler.workflow.items():
        if isinstance(node, dict) and node.get('class_type') == 'VAELoader':
            return [node_id, 0]
    return None


def _combine_conditioning(assembler, conditioning_refs):
    """Fold a list of conditioning connections [id, idx] into one via
    ConditioningCombine. Returns [id, idx] of the final combined node, or the
    single input unchanged when only one, or None when empty."""
    refs = [r for r in conditioning_refs if r]
    if not refs:
        return None
    if len(refs) == 1:
        return refs[0]
    current = refs[0]
    for nxt in refs[1:]:
        comb_id = assembler._get_unique_id()
        comb_node = create_node(assembler, "ConditioningCombine",
                                "Conditioning Combine (Multi-Angle)")
        comb_node['inputs']['conditioning_1'] = current
        comb_node['inputs']['conditioning_2'] = nxt
        assembler.workflow[comb_id] = comb_node
        current = [comb_id, 0]
    return current


def _inject_qwenmultiangle(assembler, chain_definition, qwm):
    """Numeric camera node -> translated camera prompt -> CLIP conditioning
    that is COMBINED with (never replaces) the existing positive prompt."""
    camera_id = assembler._get_unique_id()
    camera_node = create_node(assembler, "QwenMultiangleCameraNode",
                              "Qwen Multiangle Camera")
    camera_node['inputs']['horizontal_angle'] = int(qwm.get('horizontal_angle', 0))
    camera_node['inputs']['vertical_angle'] = int(qwm.get('vertical_angle', 0))
    camera_node['inputs']['zoom'] = float(qwm.get('zoom', 5.0))
    # Optional image passthrough (the camera scene preview) -- harmless when absent.
    if qwm.get('image'):
        camera_node['inputs']['image'] = qwm['image']
    assembler.workflow[camera_id] = camera_node

    # Translate node: English == pass-through (the camera terms are already
    # English tokens produced by the OH angle layer). Only glossary phrases
    # are translated; everything else is untouched.
    language = chain_definition.get('qwenmultiangle_default_language', 'English')
    translate_id = assembler._get_unique_id()
    translate_node = create_node(assembler, "QwenMultiangleCameraTranslateNode",
                                 "Qwen Multiangle Camera Translate")
    translate_node['inputs']['target_language'] = language
    translate_node['inputs']['prompt'] = [camera_id, 0]
    assembler.workflow[translate_id] = translate_node

    clip_connection = _resolve_clip_connection(
        assembler, chain_definition,
        chain_definition.get('pos_prompt_node', 'pos_prompt'))

    encode_id = assembler._get_unique_id()
    encode_node = create_node(assembler, "CLIPTextEncode",
                              "CLIP Text Encode (Multi-Angle Camera)")
    encode_node['inputs']['text'] = [translate_id, 0]
    if clip_connection:
        encode_node['inputs']['clip'] = clip_connection
    assembler.workflow[encode_id] = encode_node

    return [encode_id, 0]


def _inject_krea2_anygles(assembler, chain_definition, ag, source_ref):
    """Subject re-projection chain. Needs a source image. Returns (model_ref,
    positive_ref): the patched MODEL connection and the anygles positive
    conditioning connection, both meant to replace/augment the sampler inputs."""
    projector_lora = chain_definition.get(
        'anygles_projector_lora',
        "Krea-2-Turbo-Projector-Scale-LoRA-Diffusers.safetensors")
    sam3d_checkpoint = chain_definition.get('anygles_sam3d_checkpoint', 'model.ckpt')

    ksampler_name = chain_definition.get('ksampler_node', 'ksampler')
    ksampler_id = assembler.node_map[ksampler_name]
    current_model_connection = assembler.workflow[ksampler_id]['inputs'].get('model')
    if not current_model_connection:
        print("Multiangle: no model connection on sampler; anygles skipped.")
        return None, None

    # 1. Projector LoRA -> model + anygles_projection
    lora_id = assembler._get_unique_id()
    lora_node = create_node(assembler, "Krea2AnyblesLoadLoRA",
                            "Load LoRA (Anybles Projector)")
    lora_node['inputs']['model'] = current_model_connection
    lora_node['inputs']['lora_name'] = projector_lora
    lora_node['inputs']['strength'] = float(ag.get('strength',
                                          chain_definition.get('anygles_default_strength', 1.0)))
    assembler.workflow[lora_id] = lora_node

    # 2. Camera (source image -> re-projected normal + camera prompt)
    camera_id = assembler._get_unique_id()
    camera_node = create_node(assembler, "Krea2AnyblesCamera",
                              "Krea2 Anybles Camera")
    camera_node['inputs']['source'] = source_ref
    camera_node['inputs']['yaw'] = float(ag.get('yaw', 50.0))
    camera_node['inputs']['elevation'] = float(ag.get('elevation', 0.0))
    camera_node['inputs']['distance'] = float(ag.get('distance', 1.0))
    camera_node['inputs']['extra_prompt'] = str(ag.get('extra_prompt', ''))
    camera_node['inputs']['sam3d_checkpoint'] = sam3d_checkpoint
    assembler.workflow[camera_id] = camera_node

    # 3. Encode -> positive conditioning + anygles_control
    vae_connection = _resolve_vae_connection(assembler, chain_definition)
    clip_connection = _resolve_clip_connection(
        assembler, chain_definition,
        chain_definition.get('pos_prompt_node', 'pos_prompt'))

    encode_id = assembler._get_unique_id()
    encode_node = create_node(assembler, "Krea2AnyblesEncode",
                              "Krea2 Anybles Encode")
    if clip_connection:
        encode_node['inputs']['clip'] = clip_connection
    if vae_connection:
        encode_node['inputs']['vae'] = vae_connection
    encode_node['inputs']['prompt'] = [camera_id, 2]   # camera prompt (STRING)
    encode_node['inputs']['source'] = [camera_id, 0]   # re-projected source
    encode_node['inputs']['target_normal'] = [camera_id, 1]
    encode_node['inputs']['reference_max_edge'] = int(
        ag.get('reference_max_edge',
               chain_definition.get('anygles_reference_max_edge', 384)))
    encode_node['inputs']['vlm_reference'] = bool(
        ag.get('vlm_reference',
               chain_definition.get('anygles_vlm_reference', True)))
    assembler.workflow[encode_id] = encode_node

    # 4. Model patch -> patched MODEL
    patch_id = assembler._get_unique_id()
    patch_node = create_node(assembler, "Krea2AnyblesModelPatch",
                             "Krea2 Anybles Model Patch")
    patch_node['inputs']['model'] = [lora_id, 0]
    patch_node['inputs']['anygles_control'] = [encode_id, 1]
    patch_node['inputs']['anygles_projection'] = [lora_id, 1]
    patch_node['inputs']['kv_cache'] = bool(
        ag.get('kv_cache', chain_definition.get('anygles_kv_cache', True)))
    assembler.workflow[patch_id] = patch_node

    model_ref = [patch_id, 0]
    positive_ref = [encode_id, 0]
    return model_ref, positive_ref


def inject(assembler, chain_definition, chain_items):
    if not chain_items:
        return

    ksampler_name = chain_definition.get('ksampler_node', 'ksampler')
    if ksampler_name not in assembler.node_map:
        print("Multiangle: sampler node not found; skipping.")
        return
    ksampler_id = assembler.node_map[ksampler_name]

    # Existing connections to preserve / fold into.
    existing_positive = assembler.workflow[ksampler_id]['inputs'].get('positive')
    if not existing_positive:
        print("Multiangle: sampler has no positive input; skipping.")
        return

    extra_positives = []   # conditioning refs to fold with existing positive
    model_ref_override = None

    for item in chain_items:
        if not isinstance(item, dict):
            continue

        # --- qwenmultiangle sub-path (no source needed) ---
        qwm = item.get('qwenmultiangle')
        if qwm and (qwm.get('horizontal_angle') is not None
                    or qwm.get('vertical_angle') is not None
                    or qwm.get('zoom') is not None):
            ref = _inject_qwenmultiangle(assembler, chain_definition, qwm)
            if ref:
                extra_positives.append(ref)

        # --- krea2-anygles sub-path (needs a source image) ---
        ag = item.get('anygles')
        if ag:
            source_filename = ag.get('source')
            if not source_filename:
                print("Multiangle: anygles inputs present but no source image; "
                      "skipping anygles reprojection (camera needs source).")
                continue
            source_ref = [assembler._get_unique_id(), 0]
            # LoadImage node feeding the camera's source input.
            load_id = source_ref[0]
            load_node = create_node(assembler, "LoadImage",
                                    "Load Image (Anybles Source)")
            load_node['inputs']['image'] = source_filename
            assembler.workflow[load_id] = load_node
            source_ref = [load_id, 0]
            model_ref, positive_ref = _inject_krea2_anybles(
                assembler, chain_definition, ag, source_ref)
            if model_ref:
                model_ref_override = model_ref
            if positive_ref:
                extra_positives.append(positive_ref)

    # Fold every produced conditioning into the existing positive (the user
    # prompt's CLIPTextEncode output stays intact -- purely additive).
    fold_refs = ([existing_positive] + extra_positives) if extra_positives else []
    final_positive = _combine_conditioning(assembler, fold_refs)
    if final_positive:
        assembler.workflow[ksampler_id]['inputs']['positive'] = final_positive

    # Replace the sampler model with the patched model (anygles path only).
    if model_ref_override:
        assembler.workflow[ksampler_id]['inputs']['model'] = model_ref_override

    if extra_positives or model_ref_override:
        print(f"Multiangle injector applied: {len(extra_positives)} conditioning "
              f"path(s) combined into positive"
              + (", sampler model re-routed through anybles patch" if model_ref_override else "")
              + ". pos_prompt/neg_prompt preserved.")
