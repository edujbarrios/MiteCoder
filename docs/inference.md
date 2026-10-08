# Local inference

`LlamaCppBackend` is an optional adapter. Importing MiteCoder does not require llama-cpp-python.
Models are installed explicitly and must pass local manifest verification. Runtime has no
download, cloud fallback, telemetry, or remote configuration path. Deterministic settings reduce
variation but do not guarantee bit-identical output across CPUs or llama.cpp builds.
