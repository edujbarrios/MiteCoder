# Local models

Recommended setup:

```bash
mitecoder models
mitecoder download-model qwen2.5-coder-0.5b-q4
mitecoder verify-model qwen2.5-coder-0.5b-q4
```

`download-model` fetches the exact GGUF from the official upstream repository, verifies its
manifest SHA-256, and atomically installs it here. Use `--model-dir PATH` for another directory.
If an existing file is invalid, inspect it before using `--force` to replace that specific file.
The normal runtime remains offline; network access happens only for this explicit download command.

For an air-gapped transfer, copy the exact filename listed in `manifest.yaml` into this directory
and run `mitecoder verify-model MODEL`. Upstream model licenses still apply.
