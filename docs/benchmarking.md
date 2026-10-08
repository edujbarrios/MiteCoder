# Reproducible benchmarking

MicroSWE is an original small benchmark, not SWE-bench. The runner copies each fixture into a
new temporary directory. Results export to JSON and CSV. A serious published run should preserve
MiteCoder version and Git commit, config hash, model identifier/checksum/source/license,
quantization, CPU, RAM, architecture, OS, Python, llama-cpp-python version, seed, benchmark
version, raw results, and all failures. Exact bit-level output can vary between platforms.

Without `--model-path`, the CLI benchmark is a scripted framework smoke test. To run a real-model
experiment, pass a local GGUF explicitly:

```bash
mitecoder benchmark --suite microswe --config configs/balanced.yaml \
  --model-path models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf \
  --output benchmark-results/qwen-1.5b
```
