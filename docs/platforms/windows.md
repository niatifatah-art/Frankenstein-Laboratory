# ourTTS on Windows

This document covers the **native Windows** path. WSL2 remains a valid alternative, but it is not required for the product path described here.

## Supported baseline

- Windows 10/11 x64
- Python 3.12 recommended for the broadest worker compatibility
- PowerShell 5.1+ or PowerShell 7+
- Git for cloning the repository
- Internet access on the first run for Python packages and model files

The Core deliberately keeps heavyweight TTS engines in isolated `uv` projects. One backend's PyTorch/Transformers requirements should not contaminate the main ourTTS environment.

## Fastest install

Open PowerShell in the repository root and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-windows.ps1
```

For a real audio smoke during setup:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-windows.ps1 -TestAudio
```

The installer creates `.venv`, installs `uv`, ourTTS and the local API/Studio extra, then runs the environment doctor and a product planning smoke.

You do **not** need to activate the virtual environment for the documented commands. The worker launcher can locate the `uv.exe` installed next to the active ourTTS interpreter.

## Generate speech

```powershell
.\.venv\Scripts\ourtts.exe generate `
  --text "Hello from ourTTS on Windows." `
  --language en `
  --quality fast `
  --output .\hello.wav
```

The first real generation may download model files. Later runs reuse the worker environment/cache.

## Local Studio

Double-click:

```text
start-ourtts-studio.cmd
```

or run:

```powershell
.\.venv\Scripts\ourtts-api.exe
```

Then open:

```text
http://127.0.0.1:7860/
```

The Studio and API run locally. The current product path does not require a cloud account.

## Diagnostics

```powershell
.\.venv\Scripts\python.exe -m ttslab doctor
.\.venv\Scripts\ourtts.exe --json
.\.venv\Scripts\ourtts.exe plan --text "hello" --language en --quality fast --json
```

If `uv` is reported missing, reinstall it into the same venv:

```powershell
.\.venv\Scripts\python.exe -m pip install -U uv
```

## Model/back-end notes

Cross-platform Core support and a real native Windows product E2E are separate claims from saying every experimental engine is certified on Windows.

The Windows CI pass should keep these states explicit:

- **certified on Windows**: real model loaded and a valid WAV was generated on a Windows runner;
- **Core-compatible**: the adapter/worker contract is portable but its heavy model has not been re-qualified on Windows yet;
- **research-only / external**: no Windows product guarantee.

Do not promote an engine to Windows-certified from Linux evidence alone.

## Voice cloning and model access

Voice/reference rights remain separate from OS support. A Windows install does not weaken consent/provenance gates.

Some upstream model weights may also require accepting their own terms or authenticating with a provider such as Hugging Face. ourTTS should surface that requirement explicitly instead of treating missing access as a generic Windows failure.

## Uninstall / clean reset

The product install is intentionally local to the repository. To reset the main environment:

```powershell
Remove-Item -Recurse -Force .\.venv
```

Individual worker environments live under their engine directories and can be recreated by `uv` when needed. Model caches may live outside the repository depending on the upstream library; deleting `.venv` alone does not necessarily delete downloaded model weights.
