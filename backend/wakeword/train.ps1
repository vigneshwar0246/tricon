param(
  [Parameter(Mandatory = $true)]
  [string] $OpenWakeWordRepo,
  [string] $Config = (Join-Path $PSScriptRoot "carrot-training.yml")
)

$ErrorActionPreference = "Stop"
$trainScript = Join-Path $OpenWakeWordRepo "openwakeword\train.py"
if (-not (Test-Path -LiteralPath $trainScript -PathType Leaf)) {
  throw "OpenWakeWord training source not found: $trainScript. Use a reviewed local checkout of the upstream repository."
}
if (-not (Test-Path -LiteralPath $Config -PathType Leaf)) {
  throw "Training config not found: $Config"
}
Write-Host "Training requires reviewed positive/negative data, RIR/background audio, feature files, and the upstream Piper sample generator. This script does not download datasets or execute repository setup scripts."
& python $trainScript --training_config (Resolve-Path -LiteralPath $Config).Path --generate_clips --augment_clips --train_model
if ($LASTEXITCODE -ne 0) { throw "openWakeWord training exited with code $LASTEXITCODE" }
