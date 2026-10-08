# Contributing to MiteCoder

MiteCoder welcomes focused fixes, resource measurements, model compatibility reports, and
negative benchmark results. Please keep changes reproducible and preserve the project's offline,
CPU-first design.

## Development setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# POSIX: source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests
```

Before opening a pull request, include tests for behavior changes and run both checks above. Do not
commit model weights, generated run artifacts, benchmark outputs, credentials, or user repository
contents. Benchmark claims should state the model file and checksum, quantization, configuration,
hardware, operating system, and exact command used.

## Scope and design constraints

- Runtime operation must remain local and must not silently download models or contact services.
- File operations must stay inside the selected workspace.
- The agent may execute only test commands supplied by trusted configuration.
- Model output is untrusted; new actions must use explicit schemas and bounded observations.
- Prefer measurable improvements over adding dependencies or increasing the default context.

By contributing, you agree that your contribution is licensed under the Apache License 2.0.
