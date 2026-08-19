param(
    [switch]$TestAudio,
    [switch]$Dev
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Find-Python312 {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -c "import sys; assert sys.version_info[:2] == (3, 12)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return @{ Command = "py"; Prefix = @("-3.12") }
        }
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python -c "import sys; assert sys.version_info[:2] == (3, 12)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return @{ Command = "python"; Prefix = @() }
        }
    }

    throw "Python 3.12 (64-bit recommended) was not found. Install Python 3.12, then run this script again."
}

Write-Host ""
Write-Host "ourTTS Windows setup" -ForegroundColor Cyan
Write-Host "Repository: $Root"

$Launcher = Find-Python312
$Venv = Join-Path $Root ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"
$OurTTS = Join-Path $Venv "Scripts\ourtts.exe"
$OurTTSApi = Join-Path $Venv "Scripts\ourtts-api.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating .venv with Python 3.12..."
    $CreateVenvArgs = @($Launcher.Prefix) + @("-m", "venv", $Venv)
    & $Launcher.Command @CreateVenvArgs
    if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
} else {
    Write-Host "Using existing .venv"
}

Write-Host "Installing/updating pip and uv..."
& $VenvPython -m pip install --upgrade pip uv
if ($LASTEXITCODE -ne 0) { throw "Could not install pip/uv." }

$Extra = if ($Dev) { ".[dev,api]" } else { ".[api]" }
Write-Host "Installing ourTTS ($Extra)..."
& $VenvPython -m pip install -e $Extra
if ($LASTEXITCODE -ne 0) { throw "Could not install ourTTS." }

Write-Host "Running environment doctor..."
& $VenvPython -m ttslab doctor
if ($LASTEXITCODE -ne 0) {
    throw "Environment doctor failed. See the output above."
}

Write-Host "Checking the product CLI..."
& $OurTTS plan --text "Hello from ourTTS on Windows." --language en --quality fast --json | Out-Null
if ($LASTEXITCODE -ne 0) { throw "ourTTS planning smoke failed." }

if ($TestAudio) {
    $OutputDir = Join-Path $Root "outputs"
    New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
    $Output = Join-Path $OutputDir "windows-first-voice.wav"
    Write-Host "Generating a real Windows audio smoke. First run may download model files..."
    & $OurTTS generate --text "Hello from ourTTS running natively on Windows." --language en --quality fast --output $Output --json
    if ($LASTEXITCODE -ne 0) { throw "Real Windows audio generation failed." }
    Write-Host "Generated: $Output" -ForegroundColor Green
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Generate speech:"
Write-Host "  .\.venv\Scripts\ourtts.exe generate --text \"Hello world\" --language en --quality fast --output hello.wav"
Write-Host ""
Write-Host "Open the local Studio:"
Write-Host "  .\start-ourtts-studio.cmd"
Write-Host ""
Write-Host "No virtual-environment activation is required for the commands above."
