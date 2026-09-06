param(
    [string]$PythonExe = ".\.venv\Scripts\python.exe",
    [string]$BackendDir = "backend",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$backendPath = (Resolve-Path (Join-Path $projectRoot $BackendDir)).Path
$outputPath = Join-Path $backendPath "private_media\listening"
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null

Push-Location $backendPath
try {
    $pythonPath = (Resolve-Path $PythonExe).Path
    $manifest = & $pythonPath -c "import json; from apps.content.listening_seed_data import LISTENING_SETS as b; from apps.content.listening_seed_data_v2 import LISTENING_SETS as v2; from apps.content.listening_seed_data_v3 import LISTENING_SETS as v3; from apps.content.mock_full_length_filler_data import LISTENING_FILLER_SETS as filler; from apps.content.listening_official_parts import LISTENING_OFFICIAL_SETS as official; from apps.content.listening_official_parts_v2 import LISTENING_OFFICIAL_SETS_V2 as official2; from apps.content.practice_bank_expansion import expand_practice_bank; sets = expand_practice_bank(b + v2 + v3, skill='listening') + filler + official + official2; print(json.dumps([{'slug': x['slug'], 'transcript': x['transcript'], 'speaker_genders': x.get('speaker_genders', {})} for x in sets]))"
    if ($LASTEXITCODE -ne 0) { throw "Could not load the Listening manifest." }
} finally {
    Pop-Location
}

Add-Type -AssemblyName System.Speech
$femaleVoice = "Microsoft Linda"
$maleVoice = "Microsoft Richard"
$entries = $manifest | ConvertFrom-Json

foreach ($entry in $entries) {
    $target = Join-Path $outputPath "$($entry.slug).wav"
    if ((Test-Path -LiteralPath $target) -and -not $Force) {
        Write-Host "Skipping existing $target"
        continue
    }
    $lines = $entry.transcript -split "`n"
    $speakerGenders = @{}
    if ($null -ne $entry.speaker_genders) {
        $entry.speaker_genders.psobject.Properties | ForEach-Object { $speakerGenders[$_.Name] = $_.Value }
    }
    $speakerLabels = [System.Collections.Generic.List[string]]::new()
    foreach ($line in $lines) {
        if ($line -match '^([^:]{1,40}):\s*') {
            $label = $Matches[1].Trim()
            if ($label -ne 'Several voices' -and -not $speakerLabels.Contains($label)) { $speakerLabels.Add($label) }
        }
    }
    $ssmlParts = [System.Collections.Generic.List[string]]::new()
    $ssmlParts.Add('<?xml version="1.0" encoding="utf-8"?>')
    $ssmlParts.Add('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-CA">')
    if ($speakerLabels.Count -eq 1) {
        $intro = "This listening passage is presented by $($speakerLabels[0])."
    } elseif ($speakerLabels.Count -eq 2) {
        $intro = "You will hear a conversation between $($speakerLabels[0]) and $($speakerLabels[1])."
    } elseif ($speakerLabels.Count -gt 2) {
        $intro = "You will hear a discussion featuring " + (($speakerLabels -join ', ') -replace ', ([^,]+)$', ', and $1') + "."
    }
    if ($intro) {
        $ssmlParts.Add("<voice name=`"$femaleVoice`"><prosody rate=`"-5%`">$([System.Security.SecurityElement]::Escape($intro))</prosody></voice><break time=`"700ms`"/>")
    }
    $currentSpeaker = $null
    foreach ($line in $lines) {
        if ($line -match '^([^:]{1,40}):\s*') { $currentSpeaker = $Matches[1].Trim() }
        $spoken = $line -replace '^[^:]{1,40}:\s*', ''
        if (-not $spoken.Trim()) { continue }
        $escaped = [System.Security.SecurityElement]::Escape($spoken)
        $voice = if ($currentSpeaker -and $speakerGenders[$currentSpeaker] -eq 'male') { $maleVoice } else { $femaleVoice }
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
    Write-Host "Generated $target with Canadian $($speakerLabels.Count)-speaker cue"
}
