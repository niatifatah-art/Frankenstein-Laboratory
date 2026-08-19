from pathlib import Path

from ourtts.paths import AppPaths


def test_linux_default_paths_are_outside_source_tree(tmp_path: Path) -> None:
    paths = AppPaths.default(env={}, home=tmp_path, platform_name="linux")
    assert paths.root == tmp_path / ".local" / "share" / "ourtts"
    assert paths.database == paths.root / "ourtts.sqlite3"
    assert paths.artifacts == paths.history / "artifacts"


def test_windows_uses_local_app_data(tmp_path: Path) -> None:
    local = tmp_path / "Local App Data"
    paths = AppPaths.default(
        env={"LOCALAPPDATA": str(local)},
        home=tmp_path,
        platform_name="win32",
    )
    assert paths.root == local / "ourTTS"
    assert paths.voices == paths.root / "voices"


def test_macos_uses_application_support(tmp_path: Path) -> None:
    paths = AppPaths.default(env={}, home=tmp_path, platform_name="darwin")
    assert paths.root == tmp_path / "Library" / "Application Support" / "ourTTS"


def test_explicit_home_and_model_disk_overrides(tmp_path: Path) -> None:
    root = tmp_path / "portable" / "ourTTS"
    models = tmp_path / "Big SSD" / "models"
    paths = AppPaths.default(
        env={"OURTTS_HOME": str(root), "OURTTS_MODELS_DIR": str(models)},
        home=tmp_path,
        platform_name="win32",
    ).ensure()
    assert paths.root == root
    assert paths.models == models
    assert paths.models.is_dir()
    assert paths.projects.is_dir()
    assert paths.temp.is_dir()
