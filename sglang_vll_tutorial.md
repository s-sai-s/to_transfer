# Running LLM Inference Engines on Apple Silicon: A Complete Guide

**Machine:** MacBook Pro M4 Pro (arm64, 24 GB unified memory)  
**OS:** macOS 26.x  
**Status:** All steps verified hands-on.

---

## Problem Statement

You want to run large language models locally on your MacBook. You've heard of tools like Ollama and LM Studio — they work, but they're black boxes. You want to understand what's actually happening underneath: how models are loaded, how requests are batched, why some engines are faster than others, and how to wire them into your own Python code.

Specifically, you want to answer these questions through hands-on experimentation:

- What is the difference between **vLLM**, **SGLang**, **Ollama**, and **LM Studio**?
- What metrics actually matter for LLM serving — and how do I measure them?
- What does "offline batch inference" mean vs. running a server?
- How do I call any of these from **LangChain**?
- Can I run multiple engines at the same time and route traffic between them?
- When should I use a **Jupyter notebook** vs. a Python script for LLM work?

By the end of this guide you will have:
1. Two production-grade inference engines running natively on Apple Silicon
2. A benchmarking script that measures real performance numbers
3. Offline batch scripts, a LangChain demo, and a router proxy
4. An interactive Jupyter notebook tying it all together
5. A mental model for when to use each tool

---

## Prerequisites

**You need:**
- macOS on Apple Silicon (M1/M2/M3/M4)
- Xcode Command Line Tools: `xcode-select --install`
- `uv` package manager (replaces pip + virtualenv): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- ~15 GB free disk space (model weights + venvs)
- ~30 minutes of active time, plus model download time

**You do NOT need:**
- An NVIDIA GPU
- CUDA
- Docker
- Any prior experience with inference engines

**Check your setup:**
```bash
uname -m          # must print: arm64
sw_vers           # confirms macOS version
xcode-select -p   # confirms CLT: /Library/Developer/CommandLineTools
uv --version      # confirms uv is installed
```

---

## A Quick Concept Map

Before touching any code, here is how all the pieces relate:

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your Python Code                         │
│          (LangChain, httpx, requests, notebook cells)           │
└──────────────────────┬──────────────────────────────────────────┘
                       │  HTTP POST /v1/chat/completions
                       │  (OpenAI-compatible API — same for all)
          ┌────────────▼─────────────┐
          │    Inference Engine      │  ← the thing this guide teaches
          │  (vLLM / SGLang /        │
          │   Ollama / LM Studio)    │
          └────────────┬─────────────┘
                       │
          ┌────────────▼─────────────┐
          │     Model Weights        │
          │  (e.g. Qwen3-0.6B-4bit)  │
          │  stored in ~/.cache/     │
          └──────────────────────────┘
```

**Key insight:** All four engines expose the exact same HTTP API (OpenAI's `/v1/chat/completions`). Your application code doesn't change when you swap engines — only the `base_url` and `model` name change. What differs between engines is *how efficiently* they serve requests (batching, memory management, scheduling).

---

## Part 1: Environment Setup

### Why isolated environments?

Every tool in this space has different Python version requirements and conflicting dependencies. vLLM needs Python 3.12; SGLang's Apple Silicon path requires Python 3.11. If you install everything into one environment, they'll break each other.

The rule: **one venv per tool, all inside the project folder**.

### Create the project folder and venvs

```bash
mkdir -p ~/Work/Learning/Experiments/llm_inference_engines
cd ~/Work/Learning/Experiments/llm_inference_engines

# vLLM needs Python 3.12
uv venv venv-vllm-metal --python 3.12

# SGLang's Apple Silicon MLX path needs Python 3.11
uv venv venv-sglang-mlx --python 3.11

# Verify both are arm64 (not Rosetta x86_64)
venv-vllm-metal/bin/python -c "import platform; print(platform.machine())"  # -> arm64
venv-sglang-mlx/bin/python -c "import platform; print(platform.machine())"   # -> arm64
```

> **Why `uv`?** It resolves packages faster than pip, handles arm64 wheel selection correctly, and makes venv creation a single command. `uv pip install` is a drop-in replacement for `pip install`.

---

## Part 2: vLLM on Apple Silicon

### What is vLLM?

vLLM is an open-source LLM inference library from UC Berkeley. Its main innovation is **PagedAttention**: instead of pre-allocating a fixed chunk of memory for each request's KV cache, it manages memory in small fixed-size pages (like virtual memory in an OS). This lets many requests share memory dynamically, so you can batch more requests simultaneously without running out of memory.

On NVIDIA GPUs, vLLM uses CUDA. On Apple Silicon, the community has built **vllm-metal** — a plugin that routes the compute through MLX (Apple's ML framework) and Metal (Apple's GPU API) instead of CUDA.

### Install vLLM with the Metal plugin

```bash
# Install vLLM core
uv pip install --python venv-vllm-metal/bin/python vllm

# Install the Apple Silicon plugin
uv pip install --python venv-vllm-metal/bin/python vllm-metal

# Verify
venv-vllm-metal/bin/python -c "
import vllm, vllm_metal
print('vLLM:', vllm.__version__)
print('vllm-metal: OK')
"
```

### Download and serve a model

We'll use **Qwen3-0.6B** throughout this guide — it's small enough to load in seconds, but smart enough to give real answers.

```bash
# Start the vLLM server (this downloads ~400MB of weights on first run)
venv-vllm-metal/bin/python -m vllm.entrypoints.openai.api_server \
  --model mlx-community/Qwen3-0.6B-4bit \
  --port 8000 \
  --max-model-len 4096
```

You'll see log output like:
```
Platform plugin metal is activated
Metal memory: 25.8GB total, 12.2GB available
KV cache: 15915.0 MB (28 layers, 8673 blocks)
Warming up model...
Application startup complete.
```

What just happened:
- `mlx-community/Qwen3-0.6B-4bit` is a 4-bit quantized version of Qwen3 — weights stored at ~0.4 bytes per parameter instead of 2 bytes, so it fits easily
- vLLM allocated 15.9 GB for the KV cache (storing past attention computations for fast generation)
- It's now listening on `http://localhost:8000` with the OpenAI API

### Verify it works

In a second terminal (keep the server running):

```bash
curl -s http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mlx-community/Qwen3-0.6B-4bit",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "max_tokens": 50
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
```

You should get an answer. The server is working.

> **Apple Silicon note:** The `mx.metal.device_info is deprecated` warning is harmless — it comes from MLX internals. The `Triton not installed` message is expected — Triton is a CUDA-only kernel compiler that vLLM falls back from gracefully on Metal.

---

## Part 3: SGLang on Apple Silicon

### What is SGLang?

SGLang (Structured Generation Language) is an LLM serving framework from the SGLang team. Its key innovation is **RadixAttention**: a prefix tree (radix trie) that caches common prompt prefixes across requests. If 100 requests share the same system prompt, SGLang computes the KV for that prefix once and reuses it. This dramatically reduces compute for multi-turn conversations and prompt-heavy workloads.

SGLang is also known for excellent support for **structured outputs** (JSON schemas, grammars), making it popular for agents and tool-calling workflows.

### The Apple Silicon challenge

SGLang's primary target is NVIDIA CUDA. It has an **experimental MLX path** for Apple Silicon (`SGLANG_USE_MLX=1`), but as of mid-2026 this requires:
1. Building from source (no pre-built arm64 wheels)
2. Several patches to work around CUDA-only assumptions in the codebase

You'll learn what each patch does and why it's needed — this is a good lesson in how ML frameworks make platform assumptions.

### Install from source

```bash
# Clone the SGLang repo into the project folder
git clone https://github.com/sgl-project/sglang.git

# Install SGLang with the Apple Silicon extras
uv pip install --python venv-sglang-mlx/bin/python \
  -e "sglang/python[all_mps]" \
  --extra-index-url https://download.pytorch.org/whl/cpu
```

### Patch 1: The `triton` import problem

SGLang imports `triton` (a CUDA kernel compiler) at the top of `sglang/srt/utils/common.py`. On Apple Silicon, triton doesn't exist. The fix: create a stub package that satisfies all the imports without actually doing anything.

**Create the stub directory:**
```bash
mkdir -p venv-sglang-mlx/lib/python3.11/site-packages/triton/{language,runtime,compiler,backends}
```

**Create `venv-sglang-mlx/lib/python3.11/site-packages/triton/__init__.py`:**

This is the core stub. It defines minimal versions of triton's classes and — critically — installs a **meta-path finder** that intercepts any `import triton.*` and returns an empty stub module. This way, all 45+ files in SGLang that import triton submodules get safe stubs without needing to be patched individually.

```python
"""Minimal triton stub for Apple Silicon (no CUDA)."""
import inspect as _inspect
import sys
import types

__version__ = "3.0.0+stub"

class _AttrBag:
    """Universal stub — attribute access, calling, and inspect.signature all work."""
    def __init__(self, _name="stub"):
        object.__setattr__(self, "_stub_name", _name)
        object.__setattr__(self, "__name__", _name)
        object.__setattr__(self, "__doc__", None)
        object.__setattr__(self, "__signature__", _inspect.Signature([]))
    def __call__(self, *args, **kwargs): return _AttrBag()
    def __getattr__(self, name):
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        return _AttrBag(name)
    def __repr__(self): return f"<triton-stub {object.__getattribute__(self, '_stub_name')}>"

class _JITFunction:
    """Stub returned by @triton.jit — never invoked on Apple Silicon."""
    def __init__(self, fn):
        self.fn = fn
        self.__name__ = getattr(fn, "__name__", repr(fn))
        self.__doc__ = getattr(fn, "__doc__", None)
        self.__annotations__ = getattr(fn, "__annotations__", {})
        try: self.__signature__ = _inspect.signature(fn)
        except (ValueError, TypeError): self.__signature__ = _inspect.Signature([])
    def __call__(self, *args, **kwargs):
        raise RuntimeError(f"Triton kernel '{self.__name__}' cannot run on Apple Silicon.")
    def __getitem__(self, grid): return self

def jit(fn=None, **kwargs):
    if fn is not None: return _JITFunction(fn)
    def decorator(f): return _JITFunction(f)
    return decorator

def cdiv(a, b): return (a + b - 1) // b
def next_power_of_2(n):
    n -= 1
    for shift in (1, 2, 4, 8, 16, 32): n |= n >> shift
    return n + 1
def heuristics(*args, **kwargs):
    def decorator(fn): return fn
    return decorator
def autotune(*args, **kwargs):
    def decorator(fn): return fn
    return decorator
class Config:
    def __init__(self, *args, **kwargs): pass

class _TritonStubFinder:
    """Fallback finder: any triton.* import gets an empty stub module."""
    def find_module(self, fullname, path=None):
        if fullname.startswith("triton.") and fullname not in sys.modules:
            return self
        return None
    def load_module(self, fullname):
        if fullname in sys.modules: return sys.modules[fullname]
        mod = types.ModuleType(fullname)
        parent_name, _, child_name = fullname.rpartition(".")
        mod.__package__ = parent_name or fullname
        mod.__loader__ = self
        mod.__spec__ = None
        mod.__path__ = []
        sys.modules[fullname] = mod
        if parent_name in sys.modules:
            setattr(sys.modules[parent_name], child_name, mod)
        return mod

_finder = _TritonStubFinder()
if not any(isinstance(f, _TritonStubFinder) for f in sys.meta_path):
    sys.meta_path.append(_finder)

from . import language, runtime, backends, compiler  # noqa: E402
```

**Create `triton/language/__init__.py`:**
```python
from triton import _AttrBag

class constexpr:
    def __init__(self, value=None): self.value = value
    def __int__(self): return int(self.value) if self.value is not None else 0
    def __index__(self): return int(self)

class dtype:
    """tl.dtype stub — torch._dynamo does isinstance checks against this."""
    pass

math  = _AttrBag("math")   # tl.math.exp2, etc.
extra = _AttrBag("extra")  # tl.extra.libdevice, etc.
core  = _AttrBag("core")   # triton.language.core.view (inspected by torch._inductor)

def _getattr(name):
    if name.startswith("__") and name.endswith("__"):
        raise AttributeError(name)
    return _AttrBag(name)

import sys as _sys
_sys.modules[__name__].__getattr__ = _getattr
```

**Create `triton/runtime/__init__.py`:**
```python
from . import jit
from .jit import JITFunction, KernelInterface
```

**Create `triton/runtime/jit.py`:**
```python
from triton import _JITFunction, _AttrBag
JITFunction = _JITFunction

class KernelInterface(_AttrBag):
    """Base class for triton kernel wrappers — used by torch._inductor."""
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
```

**Create `triton/compiler/__init__.py`:**
```python
from . import compiler
```

**Create `triton/compiler/compiler.py`** and **`triton/backends/__init__.py`** and **`triton/backends/compiler.py`** — all empty files:
```bash
touch venv-sglang-mlx/lib/python3.11/site-packages/triton/compiler/compiler.py
touch venv-sglang-mlx/lib/python3.11/site-packages/triton/backends/__init__.py
touch venv-sglang-mlx/lib/python3.11/site-packages/triton/backends/compiler.py
```

> **Why this works:** Python's import system lets you insert custom finders into `sys.meta_path`. When Python encounters `import triton.language.core`, it walks the finder list. Our `_TritonStubFinder.find_module` returns `self` for any `triton.*` import not already in `sys.modules`, and `load_module` returns an empty `ModuleType`. This satisfies all import statements without any triton code actually running.

### Patch 2: The `GraphCaptureContext.stream` type annotation

In `sglang/python/sglang/srt/distributed/parallel_state.py`, around line 104, there is:

```python
@dataclass
class GraphCaptureContext:
    stream: torch.get_device_module().Stream
```

Python evaluates dataclass field annotations at **class definition time**, not at runtime. On Apple Silicon, `torch.get_device_module()` returns `torch.mps`, which has no `Stream` type. This crashes at import time, before any model is loaded.

**Fix:** Open that file and change the annotation:
```python
# Before:
stream: torch.get_device_module().Stream

# After (Any is already imported at the top of the file):
stream: Any  # torch.get_device_module().Stream — MPS has no Stream type
```

### Patch 3: Missing `torch.mps` attributes

In `sglang/python/sglang/srt/hardware_backend/mlx/model_runner_stub.py`, the `MlxModelRunnerStub.__init__` method calls `super().__init__()`, which eventually calls code that does:

```python
torch.get_device_module(self.device).set_device(self.gpu_id)
torch.get_device_module(self.device).Stream()
```

`torch.mps` doesn't have `set_device` or `Stream`. Add this monkey-patch at the top of `MlxModelRunnerStub.__init__`, before `super().__init__()`:

```python
def __init__(self, *args, mlx_pool_size=None, **kwargs):
    self._mlx_pool_size = mlx_pool_size
    _mps = torch.get_device_module("mps")
    if not hasattr(_mps, "set_device"):
        _mps.set_device = lambda n: None
    if not hasattr(_mps, "Stream"):
        class _MpsStream:
            def __enter__(self): return self
            def __exit__(self, *a): pass
        _mps.Stream = _MpsStream
    if not hasattr(_mps, "stream"):
        _mps.stream = lambda s: _mps.Stream()
    super().__init__(*args, **kwargs)
```

> **Why monkey-patch instead of a proper fix?** These CUDA APIs (`set_device`, `Stream`) are never actually *called* in the MLX inference path — they're just referenced during initialisation. A monkey-patch that returns no-ops is safe here. A proper fix would require an upstream PR to make the CUDA assumptions conditional.

### Serve with SGLang

```bash
SGLANG_USE_MLX=1 venv-sglang-mlx/bin/python -m sglang.launch_server \
  --model-path Qwen/Qwen3-0.6B \
  --port 43440 \
  --trust-remote-code \
  --disable-radix-cache \
  --disable-cuda-graph \
  --tp-size 1
```

Wait until you see:
```
The server is fired up and ready to roll!
```

**Verify:**
```bash
curl -s http://localhost:43440/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-0.6B",
    "messages": [{"role": "user", "content": "What is 2+2?"}],
    "max_tokens": 50
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
```

> **Known limitations of SGLang MLX path:** RadixAttention (prefix caching) is disabled because it requires CUDA IPC. Greedy decoding only (temperature=0). The `enable_thinking` parameter is ignored. These are known gaps in the experimental path — not bugs in your setup.

---

## Part 4: Baselines — Ollama, LM Studio, Raw mlx-lm

Before comparing engines, establish baselines with simpler tools. This gives you intuition for what "good" performance looks like, and something to compare against.

### Why baselines matter

You need a reference point. If vLLM gives you 200 tok/s and raw mlx-lm gives you 347 tok/s, something is wrong (or mlx-lm is being measured differently). Baselines catch misconfiguration.

### Ollama

Ollama wraps llama.cpp in a simple server. It handles model management and serves the OpenAI API. Easiest to get started but no real batching — each request is serialised.

```bash
# Install: https://ollama.com/download (macOS .dmg)
ollama serve           # starts server on port 11434
ollama pull qwen3:0.6b # downloads the model (~500MB)

# Test
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:0.6b","messages":[{"role":"user","content":"What is 2+2?"}],"max_tokens":50}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['choices'][0]['message']['content'])"
```

> **Gotcha:** Qwen3 is a "thinking" model — it generates a `<think>...</think>` block before its final answer. Ollama counts those tokens but puts them in `delta.reasoning` (not `delta.content`) in the SSE stream. Set `max_tokens` to at least 200 or you'll get cut off mid-think.

### LM Studio

LM Studio is a GUI app that also exposes an OpenAI-compatible local server.

```bash
# Install: https://lmstudio.ai (macOS .dmg)
# 1. Download qwen/qwen3-0.6b model inside the app
# 2. Go to Local Server tab → Start Server
# Server runs on port 1234

# Or via CLI (if lms is installed):
lms server start
lms load qwen/qwen3-0.6b
```

LM Studio uses `delta.reasoning_content` for Qwen3 thinking tokens (different from Ollama's `delta.reasoning`). This matters for your benchmark script.

### Raw mlx-lm (no server)

mlx-lm is Apple's own inference library — it runs the model directly in Python without any server overhead. It gives you the theoretical ceiling for this hardware.

```bash
uv pip install --python venv-vllm-metal/bin/python mlx-lm

venv-vllm-metal/bin/python -c "
import time
import mlx.core as mx
from mlx_lm import load, generate

model, tokenizer = load('mlx-community/Qwen3-0.6B-4bit')
prompt = 'Explain transformer attention in 3 sentences.'
prompt_tokens = tokenizer.encode(prompt)

t0 = time.perf_counter()
response = generate(model, tokenizer, prompt=prompt, max_tokens=200, verbose=False)
elapsed = time.perf_counter() - t0

# Count only the generated tokens (not prompt)
n_tokens = len(tokenizer.encode(response)) - len(prompt_tokens)
print(f'{n_tokens / elapsed:.1f} tok/s')
print(response[:300])
"
```

This gives you the **raw hardware ceiling** — what the GPU is actually capable of when there's no batching overhead, scheduler, or HTTP layer in the way. Everything else should be compared against this number.

---

## Part 5: Benchmarking — Measuring What Matters

### The three metrics

**TTFT — Time to First Token (ms)**  
How long from sending the request to receiving the first character back. This is what users feel as "latency". A TTFT of 30ms feels instant; 1000ms feels slow.

**ITL — Inter-Token Latency (ms)**  
Average time between consecutive tokens. Determines how fast text streams to the screen once it starts. Related to the model's decoding speed.

**Throughput (tok/s)**  
Total output tokens generated per wall-clock second, summed across all concurrent requests. This is the key metric for batch workloads — how much work the engine can do in total. At concurrency=8, a good engine parallelises across all 8 requests and beats single-request throughput.

### Why concurrency matters

When you send 8 requests simultaneously:
- **Bad engine (Ollama):** processes them one by one → throughput barely increases with concurrency
- **Good engine (vLLM with PagedAttention):** interleaves token generation across all 8 requests → throughput scales close to linearly

### The benchmark script

The project folder contains `benchmark.py`. It:
1. Sends `max_tokens=250` streaming requests to the target engine
2. Parses each SSE event to measure when the first token arrives (TTFT) and gaps between tokens (ITL)
3. Repeats at concurrency levels C=1, C=4, C=8
4. Runs 5 rounds per concurrency level and averages

```bash
# Start the engine first (e.g. vLLM on port 8000), then:
venv-vllm-metal/bin/python benchmark.py vllm

# Or all at once (tests whichever are running):
venv-vllm-metal/bin/python benchmark.py all --concurrencies 1 4 8 --rounds 5
```

### Reading the results

Results from this machine (Qwen3-0.6B, M4 Pro 24GB):

| Engine | C=1 TTFT | C=1 Tput | C=4 Tput | C=8 Tput |
|--------|----------|----------|----------|----------|
| vLLM-metal | 32ms | 184 tok/s | 488 tok/s | **603 tok/s** |
| SGLang-MLX | 24ms | 172 tok/s | 254 tok/s | 454 tok/s |
| LM Studio | 51ms | 222 tok/s | 410 tok/s | 411 tok/s |
| Ollama | 103ms | 253 tok/s | 271 tok/s | 274 tok/s |
| Raw mlx-lm | — | **347 tok/s** | — | — |

**What to notice:**
- vLLM at C=8 (603 tok/s) exceeds raw mlx-lm (347 tok/s). How? Because it's processing 8 requests in parallel — summed throughput exceeds single-threaded ceiling.
- Ollama's throughput barely moves from C=1 to C=8 (253 → 274) — it serialises requests.
- LM Studio plateaus at C=4 → C=8 (similar to Ollama's underlying llama.cpp).
- SGLang scales well (172 → 454) but trails vLLM because the MLX path is experimental.
- Raw mlx-lm is fastest at C=1 because it has zero overhead — but it can't batch.

> **The SSE field gotcha:** Qwen3's thinking tokens appear in different fields depending on the engine:
> - vLLM / SGLang → `delta.content`  
> - Ollama → `delta.reasoning`  
> - LM Studio → `delta.reasoning_content`
>
> Your benchmark (or any streaming parser) must handle all three, or you'll report 0 tokens for some engines.

---

## Part 6: Offline Batch Inference

### Server mode vs. offline mode

Everything so far has been **server mode**: start a long-running process, send HTTP requests, get responses. This makes sense for APIs and interactive apps.

**Offline mode** loads the model directly into your Python process — no HTTP server, no network round-trip. You write:

```python
from vllm import LLM, SamplingParams
llm = LLM(model="mlx-community/Qwen3-0.6B-4bit")
outputs = llm.generate(["prompt 1", "prompt 2", "prompt 3"], SamplingParams(max_tokens=150))
```

Use offline mode when:
- You have a fixed batch of inputs to process (data pipelines, eval scripts)
- You don't want the overhead of a server process
- You're running in a notebook or script that owns the full runtime

### The macOS multiprocessing requirement

Both `LLM` (vLLM) and `Engine` (SGLang) spawn internal subprocesses to handle model execution. On macOS, Python's default multiprocessing start method is `spawn` — which works by re-importing your script in the new process.

If your code runs at module level (outside any function), the subprocess re-imports the script and tries to create *another* engine, causing a deadlock.

**The fix is mandatory:** wrap all engine code in `if __name__ == '__main__':`.

```python
# WRONG — crashes on macOS
from vllm import LLM, SamplingParams
llm = LLM(model="mlx-community/Qwen3-0.6B-4bit")  # runs at import time → deadlock

# CORRECT
from vllm import LLM, SamplingParams

def main():
    llm = LLM(model="mlx-community/Qwen3-0.6B-4bit")
    outputs = llm.generate(["prompt 1", "prompt 2"], SamplingParams(max_tokens=150))
    for o in outputs:
        print(o.outputs[0].text)

if __name__ == "__main__":
    main()
```

### vLLM offline batch

```bash
# Run the pre-built script:
venv-vllm-metal/bin/python vllm_offline.py
```

**What the script does:**
1. `LLM(model=..., max_model_len=2048)` — loads model, allocates KV cache
2. `SamplingParams(temperature=0, max_tokens=150)` — greedy decoding, 150 token cap
3. `llm.generate(PROMPTS, params)` — submits all 5 prompts as a single batch
4. PagedAttention interleaves decoding across all 5 requests
5. Returns a list of `RequestOutput` objects with `.outputs[0].text` and `.outputs[0].token_ids`

**API reference:**
```python
from vllm import LLM, SamplingParams

llm = LLM(
    model="mlx-community/Qwen3-0.6B-4bit",
    max_model_len=2048,   # max context length (prompt + output)
)
params = SamplingParams(
    temperature=0,        # 0 = greedy (deterministic)
    max_tokens=150,       # max output tokens per request
    top_p=1.0,
)
outputs = llm.generate(["prompt 1", "prompt 2"], params)
for o in outputs:
    print(o.outputs[0].text)          # decoded string
    print(len(o.outputs[0].token_ids)) # token count
```

### SGLang offline batch

```bash
# Run the pre-built script:
SGLANG_USE_MLX=1 venv-sglang-mlx/bin/python sglang_offline.py
```

> **Important:** `SGLANG_USE_MLX=1` must be set *before* importing sglang. The env var is read at module load time to decide which backend to use.

**API reference:**
```python
import os
os.environ["SGLANG_USE_MLX"] = "1"   # must come before import

from sglang.srt.entrypoints.engine import Engine

engine = Engine(
    model_path="Qwen/Qwen3-0.6B",
    trust_remote_code=True,
    context_length=2048,
)
outputs = engine.generate(
    prompt=["prompt 1", "prompt 2"],      # list = batch
    sampling_params={"max_new_tokens": 150, "temperature": 0},
    # Note: SGLang uses "max_new_tokens", not "max_tokens"
)
for out in outputs:
    print(out["text"])                       # decoded string
    print(out["meta_info"]["completion_tokens"])  # token count

engine.shutdown()   # cleanly terminate internal processes
```

**Results (5-prompt batch, max_tokens=150 each):**

| Engine | Load time | Gen time | Throughput |
|--------|-----------|----------|------------|
| vLLM offline | 25.8s | 2.10s | 357 tok/s |
| SGLang offline | 11.5s | 2.76s | 271 tok/s |

SGLang loads faster because the MLX stub skips PyTorch KV-cache allocation. vLLM generates faster because its Metal kernels are more optimised.

---

## Part 7: LangChain Integration

### What LangChain adds

LangChain gives you composable building blocks for LLM applications:
- `ChatOpenAI` — wraps any OpenAI-compatible endpoint
- `ChatPromptTemplate` — parameterised prompt templates
- `StrOutputParser` — unwraps `AIMessage` to plain string
- LCEL (LangChain Expression Language) — the `|` pipe operator for composing chains

The key insight: because all our engines speak the OpenAI API, `ChatOpenAI` with a custom `base_url` connects to any of them. The chain code doesn't change when you swap backends.

### Setup

```bash
# Create a general-purpose venv for tools that only need HTTP (no GPU)
uv venv venv-langchain --python 3.12
uv pip install --python venv-langchain/bin/python \
  langchain==0.3.25 langchain-openai==0.3.3
```

### Run the demo

```bash
# Start an engine first (e.g. vLLM on :8000 or Ollama on :11434), then:
venv-langchain/bin/python langchain_demo.py --engine vllm
venv-langchain/bin/python langchain_demo.py --engine all
```

### Core patterns

**Pattern 1: invoke() — single synchronous call**
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",   # ← only thing that changes per engine
    api_key="no-key",                       # required but unused for local servers
    model="mlx-community/Qwen3-0.6B-4bit",
    temperature=0,
    max_tokens=200,
)
result = llm.invoke("Explain KV cache in one sentence.")
print(result.content)   # result is an AIMessage object
```

**Pattern 2: stream() — token-by-token**
```python
for chunk in llm.stream("Explain KV cache in one sentence."):
    print(chunk.content, end="", flush=True)  # prints as tokens arrive
```

**Pattern 3: LCEL chain**
```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a concise technical assistant. Answer in {n} sentences."),
    ("human",  "{question}"),
])
chain = prompt | llm | StrOutputParser()
# The | operator composes runnables — nothing runs until .invoke() is called
answer = chain.invoke({"n": "two", "question": "What is paged attention?"})
print(answer)   # plain string, not AIMessage
```

**Swapping backends:** change only `base_url` and `model`:
```python
ENGINES = {
    "vllm":   ("http://localhost:8000/v1",  "mlx-community/Qwen3-0.6B-4bit"),
    "sglang": ("http://localhost:43440/v1", "Qwen/Qwen3-0.6B"),
    "ollama": ("http://localhost:11434/v1", "qwen3:0.6b"),
}
for name, (url, model) in ENGINES.items():
    llm = ChatOpenAI(base_url=url, api_key="no-key", model=model, ...)
    result = chain.invoke(...)   # same chain, different backend
```

> **Qwen3 thinking token budget:** With `max_tokens=120`, you'll often only get `<think>...</think>` output and no final answer — the thinking block alone can consume 80-120 tokens. Use `max_tokens=400+` in practice, or disable thinking mode per engine's documentation.

---

## Part 8: Running Multiple Engines Together

### Why run multiple engines at once?

- **High availability:** if one engine crashes, traffic automatically goes to the other
- **Load spreading:** distribute requests so one engine isn't overwhelmed
- **Latency optimisation:** send to all engines simultaneously, use the first response

### The router script

The project contains `router.py` — a lightweight asyncio HTTP proxy that implements both patterns.

```bash
# Install the async HTTP library
uv pip install --python venv-langchain/bin/python aiohttp==3.11.18

# Start at least two engines, then:
venv-langchain/bin/python router.py   # listens on port 9000
```

The router exposes:
```
POST /v1/chat/completions  → round-robin to a healthy backend
POST /v1/fastest           → fan-out to all backends; return first reply
GET  /v1/models            → merged model list from all backends
GET  /router/status        → health + request counts per backend
```

### Pattern 1: Round-robin routing

```bash
# Check which engines the router found
curl -s http://localhost:9000/router/status | python3 -c "
import sys,json; d=json.load(sys.stdin)
print('Healthy:', d['healthy_count'])
for b in d['backends']:
    print(' ', '✓' if b['healthy'] else '✗', b['name'], 'handled=', b['requests_handled'])
"

# Send requests through the router — it alternates backends automatically
curl -s http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"any","messages":[{"role":"user","content":"ping"}],"max_tokens":10,"stream":false}'
```

Or from LangChain — point it at the router instead of a specific engine:
```python
router_llm = ChatOpenAI(
    base_url="http://localhost:9000/v1",
    api_key="no-key",
    model="any",   # router rewrites the model name per backend
)
```

### Pattern 2: Fastest-wins (parallel fan-out)

```bash
curl -s http://localhost:9000/v1/fastest \
  -H "Content-Type: application/json" \
  -d '{"model":"any","messages":[{"role":"user","content":"ping"}],"max_tokens":10}' | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print('Winner:', d.get('_router_winner'))"
```

The router sends the prompt to all healthy backends simultaneously using `asyncio.as_completed`. The first success wins; the others are cancelled. The response includes `"_router_winner": "ollama"` (or whichever was fastest) so you can see who answered.

### How the round-robin works (the key code)

```python
import itertools
_rr_cycle = itertools.cycle(BACKENDS)   # infinite cycle through the list

def next_backend():
    seen = 0
    while seen < len(BACKENDS):
        b = next(_rr_cycle)
        if b.healthy:
            return b
        seen += 1
    return None   # all down
```

`itertools.cycle` creates an infinite iterator. Each call to `next()` advances it by one, wrapping around. The while loop skips unhealthy backends.

### How the fastest-wins works

```python
tasks = [asyncio.create_task(race_one(backend)) for backend in healthy_backends()]

for coro in asyncio.as_completed(tasks):   # yields tasks as they finish
    backend, status, data = await coro
    if status < 400:
        winner = backend
        break                              # got a good response

for t in tasks:
    if not t.done():
        t.cancel()                         # cancel the rest
```

`asyncio.as_completed` is the key — it's like Python's `concurrent.futures.as_completed` but for async tasks. Tasks run truly in parallel (well, concurrently on the event loop); the first to complete yields from the iterator.

---

## Part 9: Notebooks vs. Scripts

### When to use a Jupyter notebook

Use a notebook when you're **exploring**, **iterating**, or **communicating**:
- Trying out a new API call and immediately seeing the response
- Comparing outputs from two different engines side-by-side in separate cells
- Measuring latency across engines and plotting a bar chart inline
- Writing a report where code, output, and explanation live together

### When to use a standalone script

Use a script when you're **running reliably**, **operating infrastructure**, or **deploying**:
- Long-running server processes (`python -m vllm.entrypoints.openai.api_server`)
- Offline batch jobs that run unattended
- CI/CD pipelines
- Code that needs the `if __name__ == '__main__':` guard (offline `LLM`/`Engine`)

### Why offline batch breaks in notebooks

`LLM()` and `Engine()` use Python's `spawn` multiprocessing method to launch their internal worker processes. When a new process spawns, Python re-imports the main module. In a regular script, the `if __name__ == '__main__':` guard prevents the re-import from re-running the engine constructor.

In a Jupyter kernel, `__name__` is `'__main__'` for every cell execution. There's no way to guard against re-import cleanly inside a notebook kernel. The result is that the spawned subprocess tries to create a second engine instance while the first one is still starting — deadlock.

**Workaround:** call the offline script as a subprocess from a notebook cell:
```python
import subprocess, os

result = subprocess.run(
    ["venv-vllm-metal/bin/python", "vllm_offline.py"],
    capture_output=True, text=True,
)
# Filter out vLLM startup INFO noise
for line in result.stdout.splitlines():
    if not line.startswith("INFO ") and not line.startswith("(Engine"):
        print(line)
```

### Setup and open the notebook

```bash
# Install Jupyter in the langchain venv
uv pip install --python venv-langchain/bin/python jupyterlab ipykernel

# Register the venv as a named kernel
venv-langchain/bin/python -m ipykernel install \
  --user --name inference-lab --display-name "Inference Lab (langchain)"

# Open the lab
cd /Users/sai/Work/Learning/Experiments/llm_inference_engines
venv-langchain/bin/jupyter lab
# → open inference_lab.ipynb
# → Kernel → Change Kernel → "Inference Lab (langchain)"
```

The notebook `inference_lab.ipynb` covers all four patterns (raw HTTP, LangChain, router, offline-via-subprocess) in executable cells, with explanations between each section.

---

## Quick Reference

### Start each engine

```bash
# vLLM (port 8000)
venv-vllm-metal/bin/python -m vllm.entrypoints.openai.api_server \
  --model mlx-community/Qwen3-0.6B-4bit --port 8000 --max-model-len 4096

# SGLang (port 43440)
SGLANG_USE_MLX=1 venv-sglang-mlx/bin/python -m sglang.launch_server \
  --model-path Qwen/Qwen3-0.6B --port 43440 \
  --trust-remote-code --disable-radix-cache --disable-cuda-graph --tp-size 1

# Ollama (port 11434)
ollama serve

# LM Studio (port 1234) — start via the app's Local Server tab
```

### Run each script

```bash
# Benchmark (server must be running)
venv-vllm-metal/bin/python benchmark.py vllm
venv-vllm-metal/bin/python benchmark.py all

# Offline batch
venv-vllm-metal/bin/python vllm_offline.py
SGLANG_USE_MLX=1 venv-sglang-mlx/bin/python sglang_offline.py

# LangChain demo (server must be running)
venv-langchain/bin/python langchain_demo.py --engine vllm

# Router (start engines first)
venv-langchain/bin/python router.py

# Notebook
venv-langchain/bin/jupyter lab
```

### Check which servers are running

```bash
for port in 8000 43440 11434 1234; do
  curl -sf http://localhost:$port/v1/models > /dev/null 2>&1 \
    && echo "port $port: UP" || echo "port $port: down"
done
```

### Stop a server

```bash
kill $(lsof -ti:8000)   # vLLM
kill $(lsof -ti:43440)  # SGLang
kill $(lsof -ti:11434)  # Ollama
kill $(lsof -ti:9000)   # router
```

---

## Troubleshooting

**"No module named 'triton'"** — The triton stub isn't installed. See Part 3, Patch 1. Make sure all files are in `venv-sglang-mlx/lib/python3.11/site-packages/triton/`.

**"module 'torch.mps' has no attribute 'Stream'"** — The `parallel_state.py` annotation patch (Patch 2) hasn't been applied.

**"RuntimeError: An attempt has been made to start a new process before the current process has finished its bootstrapping phase"** — Missing `if __name__ == '__main__':` guard in your script. Wrap everything in a `main()` function and call it under `if __name__ == '__main__':`.

**vLLM benchmark shows 0 tokens from some engines** — The SSE delta field differs per engine. Make sure your parser checks `delta.get("content") or delta.get("reasoning") or delta.get("reasoning_content")`.

**SGLang `EOFError` on startup** — The scheduler subprocess crashed. Check if the triton stub and `parallel_state.py` patches are applied. Run with `PYTHONFAULTHANDLER=1` for a stack trace.

**Router reports all backends DOWN** — The router's health check hits `/models`. Make sure your server is fully initialised (not just started). Check the individual server logs.

**Ollama TTFT looks like 1000ms+** — Ollama runs Qwen3 thinking mode; the first token is a `<think>` token, which is correct. If you're filtering `delta.reasoning` out of your parser, TTFT will appear inflated because you're measuring until the first *answer* token.
