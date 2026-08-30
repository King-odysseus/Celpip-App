param(
    [string]$PythonExe = ".\.venv\Scripts\python.exe",
    [string]$BackendDir = "backend"
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendPath = (Resolve-Path (Join-Path $projectRoot $BackendDir)).Path
$outputPath = Join-Path $backendPath "private_media\listening"
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null

Push-Location $backendPath
try {
    $pythonPath = (Resolve-Path $PythonExe).Path
    $manifest = & $pythonPath -c "import json; from apps.content.listening_seed_data import LISTENING_SETS as base; from apps.content.listening_seed_data_v2 import LISTENING_SETS as v2; from apps.content.listening_seed_data_v3 import LISTENING_SETS as v3; sets = base + v2 + v3; print(json.dumps([{'slug': x['slug'], 'transcript': x['transcript']} for x in sets]))"
    if ($LASTEXITCODE -ne 0) { throw "Could not load the Listening manifest." }
} finally {
    Pop-Location
}

Add-Type -AssemblyName System.Speech
$voices = @("Microsoft Linda", "Microsoft Richard")
$entries = $manifest | ConvertFrom-Json

foreach ($entry in $entries) {
    $target = Join-Path $outputPath "$($entry.slug).wav"
    if (Test-Path -LiteralPath $target) {
        Write-Host "Skipping existing $target"
        continue
    }
    $lines = $entry.transcript -split "`n"
    $ssmlParts = [System.Collections.Generic.List[string]]::new()
    $ssmlParts.Add('<?xml version="1.0" encoding="utf-8"?>')
    $ssmlParts.Add('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-CA">')
    for ($index = 0; $index -lt $lines.Count; $index++) {
        $spoken = $lines[$index] -replace '^[^:]{1,40}:\s*', ''
        $escaped = [System.Security.SecurityElement]::Escape($spoken)
        $voice = $voices[$index % $voices.Count]
        $ssmlParts.Add("<voice name=`"$voice`"><prosody rate=`"-5%`">$escaped</prosody></voice><break time=`"450ms`"/>")
    }
    $ssmlParts.Add('</speak>')

    $synth = [System.Speech.Synthesis.SpeechSynthesizer]::new()
    try {
        $format = [System.Speech.AudioFormat.SpeechAudioFormatInfo]::new(16000, 16, 1)
        $synth.SetOutputToWaveFile($target, $format)
        $synth.SpeakSsml(($ssmlParts -join ""))
    } finally {
        $synth.Dispose()
    }
    Write-Host "Generated $target"
}
