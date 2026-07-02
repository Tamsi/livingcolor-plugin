from lc_server.moa.loader import load_bundled_presets, bundled_preset_version


def test_load_bundled_presets_contains_standard_and_premium():
    presets = load_bundled_presets()
    assert "lc-analyst" in presets
    assert "lc-developer-premium" in presets
    assert presets["lc-developer"]["aggregator"]["model"] == "anthropic/claude-opus-4.8"
    assert presets["lc-developer-premium"]["aggregator"]["model"] == "anthropic/claude-opus-4.8"
    assert bundled_preset_version() == "1.3.0"


def test_load_bundled_presets_contains_nemotron_tier():
    presets = load_bundled_presets()
    assert "lc-analyst-nemotron" in presets
    assert "lc-planner-nemotron" in presets
    assert "lc-developer-nemotron" not in presets
    assert presets["lc-planner-nemotron"]["aggregator"]["provider"] == "nvidia"
    assert presets["lc-planner-nemotron"]["aggregator"]["model"] == "nvidia/nemotron-3-super-120b-a12b"


def test_nemotron_presets_use_fast_references():
    presets = load_bundled_presets()
    expected_refs = [
        {"provider": "nvidia", "model": "nvidia/nemotron-3-nano-30b-a3b"},
        {"provider": "openrouter", "model": "z-ai/glm-5.2"},
    ]
    assert presets["lc-analyst-nemotron"]["reference_models"] == expected_refs
    assert presets["lc-planner-nemotron"]["reference_models"] == expected_refs


def test_developer_preset_has_two_references():
    presets = load_bundled_presets()
    assert presets["lc-developer"]["reference_models"] == [
        {"provider": "openrouter", "model": "openai/gpt-5.5"},
        {"provider": "openrouter", "model": "anthropic/claude-sonnet-4.6"},
    ]
