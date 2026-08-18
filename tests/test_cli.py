from ttslab.cli import main


def test_list_command_succeeds(capsys) -> None:
    assert main(["list"]) == 0
    output = capsys.readouterr().out
    assert "kokoro" in output
    assert "pocket_tts" in output


def test_run_refuses_unverified_adapter(capsys) -> None:
    assert main(["run", "kokoro", "--text", "hello"]) == 3
    error = capsys.readouterr().err
    assert "adapter_ready" in error
