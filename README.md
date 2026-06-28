# Opus-ViP

Opus-ViP is a self-hosted MVP for an Opus Clip-style short-form video workflow. It turns a long-form transcript into ranked clip candidates with hook scoring, timing windows, rationale, captions, and JSON export.

## Features

- Dependency-free Python HTTP server and browser UI.
- Transcript parser for timestamped and plain-text input.
- Heuristic viral scoring based on hook words, questions, CTA signals, lexical density, and target-duration fit.
- File-backed project history under `data/projects`.
- Safe static-file serving and project-id validation to avoid path traversal.

## Run locally

```bash
python -m opus_vip.server
```

Open <http://127.0.0.1:8000> and paste a transcript. For imports without installation, run commands with `PYTHONPATH=src`.

## Test

```bash
PYTHONPATH=src pytest -q
```

## Product direction

This MVP proves the core loop: upload/paste transcript → identify promising moments → export an editable clip plan. Next competitive milestones:

1. Add FFmpeg-backed source-video cutting and vertical 9:16 layout rendering.
2. Add speech-to-text ingestion with speaker diarization.
3. Add face/scene detection and silence removal.
4. Add platform-specific templates, burn-in captions, and batch exports.
5. Add multi-tenant auth, quotas, billing, and background job processing.
