$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$modelName = "vosk-model-small-en-us-0.15"
$voiceRoot = Join-Path $repoRoot "voice-models"
$modelPath = Join-Path $voiceRoot $modelName
$archivePath = Join-Path $voiceRoot "$modelName.zip"
$modelUrl = "https://alphacephei.com/vosk/models/$modelName.zip"

New-Item -ItemType Directory -Path $voiceRoot -Force | Out-Null

if (-not (Test-Path (Join-Path $modelPath "conf\model.conf")) -or
    -not (Test-Path (Join-Path $modelPath "am\final.mdl"))) {
    if (Test-Path $modelPath) {
        throw "An incomplete Vosk model folder already exists at '$modelPath'. Rename or remove that folder, then run setup again."
    }

    Write-Host "Downloading the official compact English Vosk model..."
    Invoke-WebRequest -Uri $modelUrl -OutFile $archivePath
    Expand-Archive -LiteralPath $archivePath -DestinationPath $voiceRoot -Force

    if (-not (Test-Path (Join-Path $modelPath "conf\model.conf")) -or
        -not (Test-Path (Join-Path $modelPath "am\final.mdl"))) {
        throw "The downloaded archive did not contain the expected Vosk model files. The archive was kept at '$archivePath'."
    }

    Remove-Item -LiteralPath $archivePath
}

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python was not found on PATH. Install Python 3.11 or later, add it to PATH, and run setup again."
}

Write-Host "Installing the optional Vosk and microphone packages with: $($python.Source)"
Push-Location $repoRoot
try {
    & $python.Source -m pip install -e ".[voice]"
    if ($LASTEXITCODE -ne 0) {
        throw "Installing the optional voice packages failed (exit code $LASTEXITCODE)."
    }
}
finally {
    Pop-Location
}

$localConfig = Join-Path $repoRoot "START-TULPAR.local.cmd"
if (-not (Test-Path $localConfig)) {
    Copy-Item -LiteralPath (Join-Path $repoRoot "START-TULPAR.local.example.cmd") -Destination $localConfig
    Write-Host "Created START-TULPAR.local.cmd from the example configuration."
}
else {
    Write-Host "Kept the existing START-TULPAR.local.cmd configuration."
}

Write-Host "Voice input setup completed. Start the interactive simulation with START-TULPAR.cmd."
Write-Host "The Webots console should report microphone ready. If it reports an error, check that Webots uses the Python environment shown above and that Windows permits microphone access."
