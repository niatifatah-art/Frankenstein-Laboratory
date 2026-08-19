import json

from ttslab.product import MODEL_FAMILY, PRODUCT_NAME, model_profile, product_manifest
from ttslab.product_cli import main


def test_product_brand_and_family_are_stable() -> None:
    assert PRODUCT_NAME == "ourTTS"
    assert [item.key for item in MODEL_FAMILY] == [
        "atom",
        "nano",
        "mini",
        "core",
        "pro",
        "omni",
    ]


def test_atom_is_deliberately_small_and_focused() -> None:
    atom = model_profile("ATOM")
    assert atom.target_parameters_millions == 80
    assert "naturalness" in atom.priority
    assert "voice_design" in atom.deliberately_not_required


def test_omni_is_not_falsely_presented_as_a_checkpoint() -> None:
    omni = model_profile("omni")
    assert omni.status == "system_target"
    assert omni.target_parameters_millions is None
    assert omni.target_weight_mb_fp16 is None


def test_manifest_distinguishes_targets_from_releases() -> None:
    manifest = product_manifest()
    assert manifest["product"] == "ourTTS"
    assert any("not a released checkpoint" in rule for rule in manifest["truth_rules"])


def test_friendly_cli_and_json_output(capsys) -> None:
    assert main([]) == 0
    text = capsys.readouterr().out
    assert "ourTTS Atom" in text
    assert "targets, not released checkpoints" in text

    assert main(["--model", "atom", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["key"] == "atom"
