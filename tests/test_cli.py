from ttslab.cli import main


def test_list_command_succeeds(capsys) -> None:
    assert main(["list"]) == 0
    output = capsys.readouterr().out
    assert "kokoro" in output
    assert "pocket_tts" in output
    assert "qwen3_custom_06b" in output


def test_run_refuses_unverified_adapter(capsys) -> None:
    assert main(["run", "chatterbox", "--text", "hello"]) == 3
    assert "planned" in capsys.readouterr().err


def test_registry_check_command(capsys) -> None:
    assert main(["registry-check"]) == 0
    assert "OK" in capsys.readouterr().out
