$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$artifacts = Join-Path $root "artifacts\demo"
$events = Get-Content -Raw (Join-Path $artifacts "browser-demo-results.json") | ConvertFrom-Json
$voice = New-Object -ComObject SAPI.SpVoice
$format = New-Object -ComObject SAPI.SpAudioFormat
$format.Type = 22
$manifest = @()
$index = 0
foreach ($event in ($events | Where-Object kind -eq "question")) {
    $destination = Join-Path $artifacts ("interviewer-{0:d2}.wav" -f $index)
    $stream = New-Object -ComObject SAPI.SpFileStream
    $stream.Format = $format
    $stream.Open($destination, 3, $false)
    $voice.AudioOutputStream = $stream
    $spokenQuestion = if ($event.step -match '[^\x00-\x7F]') { "What is the capital of India? Please answer in Hindi." } else { $event.step }
    [void]$voice.Speak($spokenQuestion)
    $stream.Close()
    $manifest += [pscustomobject]@{ file = Split-Path -Leaf $destination; offset_ms = $event.question_offset_ms; text = $event.step }
    $index++
}
$manifest | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 (Join-Path $artifacts "interviewer-audio-manifest.json")
