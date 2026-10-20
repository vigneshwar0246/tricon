# Carrot wake-word workbench

## Status

Carrot activation is **not active**. The repository has no trained Carrot model, labeled evaluation recordings, or openWakeWord dependency installed. The app currently uses continuous browser speech capture, not acoustic wake-word detection. No model or dataset has been downloaded or fabricated.

The intended local detector is openWakeWord, which supports custom ONNX models and streaming 16 kHz signed 16-bit mono audio. The inference library is Apache-2.0; individual pre-trained model files have their own licenses (the upstream pre-trained models are CC BY-NC-SA 4.0 and are not a substitute for Carrot). See the [upstream repository](https://github.com/dscripka/openWakeWord) and [training configuration](https://github.com/dscripka/openWakeWord/blob/main/examples/custom_model.yml).

## Data prerequisite

Before training, provide or approve sources for:

- Positive recordings containing the exact word “Carrot”, from multiple speakers, distances, speaking rates, and realistic microphone levels. A user-recorded set can be used only with the speaker's consent. Synthetic speech may augment, but should not replace independent human evaluation.
- Negative recordings with ordinary conversation, similar-sounding words, silence, and representative room noise. Recordings must have documented provenance and licenses/permissions.
- Room impulse responses and background audio for augmentation, plus the feature and false-positive validation datasets expected by the upstream training workflow. Review each source's license and redistribution terms before use.

No dataset is currently bundled. In particular, Common Voice is not downloaded here: access and redistribution follow Mozilla Data Collective terms. The existing Piper Norman voice card states the voice model is MIT-licensed and its underlying LibriVox recordings are public domain, but it is one English male speaker; it is not enough for a diverse positive set or independent evaluation. See the [voice model card](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/norman/medium/MODEL_CARD).

## Reproducible workflow (after data and dependencies are approved)

Use a reviewed local checkout of upstream openWakeWord; do not run an unreviewed setup script. The training implementation requires a separate training environment (including PyTorch, PyYAML, and the upstream Piper sample generator). It is intentionally not part of the lightweight FastAPI requirements. `carrot-training.yml` is a configuration template, not runnable until every dataset path is supplied and checked. Its initial 20,000 positive sample target follows upstream's stated minimum recommendation; expand it only with enough licensed and varied data.

From the repository root, after configuring the YAML paths and installing the documented upstream training dependencies:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\backend\wakeword\train.ps1 -OpenWakeWordRepo D:\path\to\reviewed\openWakeWord
```

The script runs the upstream generation, augmentation, and training stages and does not download datasets itself. Verify the resulting `.onnx` file and metadata, then copy the accepted model to `backend/models/wakeword/carrot.onnx`. Do not label it active until it is evaluated independently and the streaming client/backend integration is implemented and tested.

Install inference support only when approved; this is separate from the main backend environment and does not download a model:

```powershell
python -m pip install "openwakeword==0.6.0" "onnxruntime==1.23.2"
```

These packages add ONNX Runtime and its native runtime libraries. Confirm compatible wheels for the selected Python version before installation. The web UI cannot detect a Carrot model just because these packages are installed.

## Evaluation

Prepare separate positive and negative folders containing only mono, 16 kHz, signed 16-bit PCM WAV files. Positive clips should include known leading silence so reported detection latency has a defined reference. Choose the threshold on a separate validation split, then run the held-out test:

```powershell
python .\backend\wakeword\evaluate.py `
  --model .\backend\models\wakeword\carrot.onnx `
  --positive .\backend\wakeword\data\heldout-positive `
  --negative .\backend\wakeword\data\heldout-negative `
  --threshold 0.5
```

The threshold above is only an example and must be selected from validation data. The evaluator reports clip recall, negative clip rate, threshold-crossing false activations per hour, median time from clip start to first detection, model file size, model-load and inference time, average process CPU use, and process working-set memory. It does not measure wake latency with microphone hardware or compare controlled noise conditions. Report speaker counts, noise conditions, and test duration alongside the JSON output. No evaluation results exist yet because no Carrot model or labeled recordings are available.

## Integration boundary

The app currently exposes continuous browser speech capture and silence-based turn detection. There is no wake-word WebSocket route or browser-to-detector audio stream in the current app, so installing a model alone will not activate Carrot. Keep the UI's unavailable wording until a local detector service, audio stream, lifecycle controls, and regression tests are implemented and a verified model is present.
