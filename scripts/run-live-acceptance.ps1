param(
    [string]$ApiBase = "http://127.0.0.1:8000",
    [string]$Output = "artifacts/demo/live-question-results.json"
)

$ErrorActionPreference = "Stop"
$session = "acceptance-$([Guid]::NewGuid())"
$questions = @(
    @{ Text = "Introduce yourself and explain what this voice assistant can do."; Language = "en" },
    @{ Text = "Explain the difference between artificial intelligence and rule-based systems."; Language = "en" },
    @{ Text = "Give a simple real-world example of machine learning."; Language = "en" },
    @{ Text = "Explain the difference between CPU and GPU."; Language = "en" },
    @{ Text = "Explain how speech-to-text, an AI model, and text-to-speech work together."; Language = "en" },
    @{ Text = "What happens if the local Qwen model is unavailable?"; Language = "en" },
    @{ Text = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String("4KSt4KS+4KSw4KSkIOCkleClgCDgpLDgpL7gpJzgpKfgpL7gpKjgpYAg4KSV4KWN4KSv4KS+IOCkueCliD8g4KS44KSw4KSyIOCkueCkv+CkguCkpuClgCDgpK7gpYfgpIIg4KSJ4KSk4KWN4KSk4KSwIOCkpuCli+ClpA==")); Language = "hi" },
    @{ Text = "System status"; Language = "en" },
    @{ Text = "Tell me the system status"; Language = "en" },
    @{ Text = "Is everything working?"; Language = "en" },
    @{ Text = "Check all services"; Language = "en" },
    @{ Text = "Are the voice models ready?"; Language = "en" },
    @{ Text = "Check the system requirements"; Language = "en" },
    @{ Text = "Explain the current limitations of this assistant honestly."; Language = "en" }
)

$results = foreach ($item in $questions) {
    $timer = [Diagnostics.Stopwatch]::StartNew()
    try {
        $body = @{ message = $item.Text; session_id = $session; language = $item.Language } | ConvertTo-Json
        $response = Invoke-RestMethod -Method Post -Uri "$ApiBase/api/chat" -ContentType "application/json" -Body $body
        $timer.Stop()
        [pscustomobject]@{
            question = $item.Text; language = $item.Language; result = "PASS"; elapsed_ms = $timer.ElapsedMilliseconds
            answer = $response.response; server_metrics = $response.metrics; session_id = $response.session_id
        }
    } catch {
        $timer.Stop()
        [pscustomobject]@{ question = $item.Text; language = $item.Language; result = "FAIL"; elapsed_ms = $timer.ElapsedMilliseconds; error = $_.Exception.Message }
    }
}

$parent = Split-Path -Parent $Output
New-Item -ItemType Directory -Force -Path $parent | Out-Null
$results | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 $Output
$results | Format-Table result, language, elapsed_ms, question -AutoSize
if ($results.result -contains "FAIL") { exit 1 }
