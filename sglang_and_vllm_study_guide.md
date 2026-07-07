# Building a Local AI Assistant on Apple Silicon — A Problem-Driven Guide

**Machine you're working on:** MacBook Pro M4 Pro, 24 GB unified memory, arm64  
**Everything runs in:** `/Users/sai/Work/Learning/Experiments/llm_inference_engines`

---

## The Situation

You want an AI assistant that runs entirely on your laptop. No API keys, no monthly bills, no data leaving your machine. You've heard this is possible now — modern MacBooks are fast enough to run small models locally at useful speeds.

You install Ollama, pull a model, and it works. You ask it questions and it answers. Great.

But over the next few days you start noticing things. When you're deep in a debugging session and you ask a quick question, sometimes it takes two seconds before the first word appears. When you have two terminal windows open and you query it from both at the same time, it gets even slower. You have a folder of notes you want to summarize in bulk — the server approach feels clunky for that.

You don't know if these are fundamental limitations of running models locally, limitations of Ollama specifically, or just configuration issues. You can't tell because you've never *measured* any of it.

That's the problem. And solving it — properly, with numbers — is what this guide is about.

---

## What You'll Build

By the end, you'll have:

- Real performance numbers for four different inference engines on your hardware
- Two production-grade engines (vLLM, SGLang) running natively on Apple Silicon
- A benchmarking script that measures the metrics that actually matter
- A batch processing script for offline jobs (no server needed)
- A LangChain integration so your Python code doesn't care which engine is running
- A router that distributes traffic across engines and fails over automatically
- A Jupyter notebook for interactive exploration

More importantly, you'll understand *why* each piece exists and when to use it.

---

## Prerequisites

Before starting:

```bash
# Confirm you're on Apple Silicon
uname -m    # must print: arm64

# Confirm Xcode Command Line Tools are installed
xcode-select -p    # must print a path

# Install uv (faster than pip, handles arm64 wheels correctly)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Confirm
uv --version
```

---

## Chapter 1: You Can't Improve What You Can't Measure

### The problem

Ollama feels slow sometimes. But "feels slow" is useless. You need numbers. Specifically, you need to answer:

1. How long does it take before the *first word* appears? (This is what you feel as lag)
2. How fast does text stream after that first word?
3. What happens when two requests arrive at the same time?

These are three different things. Getting them confused leads to wrong conclusions.

### The concepts you need

**TTFT — Time to First Token**  
The time from when you send a request to when you receive the first character back. This is latency as a human experiences it. 30ms feels instant. 1000ms feels like the app froze.

**Throughput — tokens per second**  
How many tokens the engine generates per wall-clock second, summed across all active requests. This matters for batch jobs and for concurrent users.

**Concurrency**  
What happens when N requests arrive simultaneously? A naive engine processes them one at a time — request 2 waits for request 1 to finish. A good engine interleaves them. The difference shows up in the numbers: at C=8 (8 simultaneous requests), a serializing engine barely improves over C=1, while a proper batching engine can multiply throughput.

**SSE — Server-Sent Events**  
All four engines stream responses using the same protocol: a long-lived HTTP connection that sends newline-separated `data: {...}` JSON chunks, one per token. Your benchmark needs to read these chunks and timestamp each one to measure TTFT and inter-token gaps.

### What to do

**Step 1: Set up an isolated environment**

You'll use separate Python environments for each tool — their dependencies conflict.

```bash
cd /Users/sai/Work/Learning/Experiments/llm_inference_engines

# Python 3.12 for vLLM (needed later), used here for benchmarking too
uv venv venv-vllm-metal --python 3.12

# Install httpx (async HTTP client, used in benchmark.py)
uv pip install --python venv-vllm-metal/bin/python httpx
```

**Step 2: Start Ollama**

```bash
ollama serve                  # starts server on port 11434
ollama pull qwen3:0.6b        # download the model (~500MB)
```

We use Qwen3-0.6B throughout this guide — it's small enough to load quickly but smart enough to give real answers. The `0.6b` means 0.6 billion parameters; the 4-bit quantized version uses about 500MB of memory.

> **One important thing about Qwen3:** It's a "thinking" model. Before giving you its answer, it generates a `<think>...</think>` block where it reasons through the problem. These thinking tokens are real tokens that count toward your token budget and your TTFT. Each engine puts them in a different field in the SSE stream:
> - Ollama → `delta.reasoning`
> - LM Studio → `delta.reasoning_content`
> - vLLM / SGLang → `delta.content`
>
> If your parser doesn't check all three fields, you'll report 0 tokens for some engines. Keep this in mind when you read `benchmark.py`.

**Step 3: Run the benchmark against Ollama**

The project folder contains `benchmark.py`. Look at how it works before running it:

```bash
# Read the top of the file to understand what it measures
head -25 benchmark.py
```

The key loop inside the benchmark:
1. Sends a streaming POST to `/v1/chat/completions`
2. For each `data: {...}` line received, extracts `delta.content` / `delta.reasoning` / `delta.reasoning_content`
3. Records a timestamp on the first non-empty chunk (that's TTFT)
4. Records gaps between subsequent chunks (that's ITL — inter-token latency)
5. Repeats at C=1, C=4, C=8 simultaneous requests

Run it:
```bash
venv-vllm-metal/bin/python benchmark.py ollama --concurrencies 1 4 8 --rounds 3
```

Note down your numbers. You'll compare them against other engines in a moment.

### What you learned

You now have real TTFT and throughput numbers for Ollama on your hardware. You probably noticed that at C=4 and C=8, the throughput barely improved. That's not a bug — it's how Ollama works. It uses llama.cpp underneath, which processes requests sequentially. Request 2 genuinely waits for request 1 to finish.

This answers your first question: the slowness you felt wasn't your imagination or a misconfiguration. Ollama serializes requests by design.

The question now: does it have to be this way, or is there an engine that actually batches?

---

## Chapter 2: Discovering That Batching Changes Everything

### The problem

You now know Ollama serializes. You want to know if there's an engine that batches requests properly — and if so, how much faster it is.

### The concept you need

**PagedAttention**  
Every token generated by a transformer model requires access to the attention keys and values from all previous tokens in the conversation. This is called the KV cache. Naively, you'd pre-allocate a fixed chunk of memory per request — but this is wasteful because requests have different lengths, and you don't know the final length upfront.

vLLM's PagedAttention treats KV cache memory like virtual memory in an operating system. It allocates memory in small fixed-size pages (e.g., 16 tokens each). Pages are assigned to requests as needed and freed when requests complete. This means:

1. You can fit more simultaneous requests in memory (no wasted pre-allocation)
2. Requests can share pages if they have identical prompt prefixes
3. The engine can genuinely interleave token generation across all active requests

The result: at C=8, vLLM's total throughput can *exceed* the single-request ceiling. It's generating tokens for 8 conversations at once, and the sum is more than what any one conversation could achieve alone.

### What to do

**Step 1: Install vLLM with the Apple Silicon plugin**

vLLM was originally built for NVIDIA CUDA. The community-built `vllm-metal` plugin routes the compute through Apple's MLX framework and Metal GPU API instead.

```bash
uv pip install --python venv-vllm-metal/bin/python vllm
uv pip install --python venv-vllm-metal/bin/python vllm-metal

# Verify the plugin loads
venv-vllm-metal/bin/python -c "
import vllm
print('vLLM version:', vllm.__version__)
# Should see 'Platform plugin metal is activated' in logs
"
```

**Step 2: Start the vLLM server**

```bash
venv-vllm-metal/bin/python -m vllm.entrypoints.openai.api_server \
  --model mlx-community/Qwen3-0.6B-4bit \
  --port 8000 \
  --max-model-len 4096
```

Watch the startup output:
```
Platform plugin metal is activated
Metal memory: 25.8GB total, 12.2GB available
KV cache: 15915.0 MB (28 layers, 8673 blocks, 16 tokens/block)
Warming up Metal kernels...
Application startup complete.
```

It's allocated 15.9 GB for the KV cache — those are the 8673 pages of PagedAttention. The `16 tokens/block` tells you each page holds 16 tokens of KV state.

The `Triton not installed` warning is expected — Triton is a CUDA-only kernel compiler. vLLM falls back to its native Metal kernels automatically.

**Step 3: Benchmark vLLM and compare**

```bash
venv-vllm-metal/bin/python benchmark.py vllm --concurrencies 1 4 8 --rounds 3
```

Look at your numbers side by side with Ollama's. The pattern you'll see:

| Engine | C=1 Tput | C=4 Tput | C=8 Tput |
|--------|----------|----------|----------|
| Ollama | ~253 tok/s | ~271 tok/s | ~274 tok/s |
| vLLM | ~184 tok/s | ~488 tok/s | ~603 tok/s |

Ollama barely moves. vLLM at C=8 produces more total throughput than even raw mlx-lm (the theoretical hardware ceiling for a single request) — because batching lets it utilize the GPU more fully across multiple requests simultaneously.

vLLM's single-request throughput (C=1) is actually *lower* than Ollama's. This is the tradeoff: vLLM adds scheduling overhead for single requests, but that investment pays off massively at higher concurrency.

**Step 4: Establish the hardware ceiling with raw mlx-lm**

Before going further, answer the question: how fast *could* this hardware go with zero framework overhead?

```bash
uv pip install --python venv-vllm-metal/bin/python mlx-lm

venv-vllm-metal/bin/python - <<'EOF'
import time
from mlx_lm import load, generate

model, tokenizer = load("mlx-community/Qwen3-0.6B-4bit")
prompt = "Explain transformer attention in 3 sentences."
t0 = time.perf_counter()
response = generate(model, tokenizer, prompt=prompt, max_tokens=200, verbose=False)
elapsed = time.perf_counter() - t0
n_out = len(tokenizer.encode(response)) - len(tokenizer.encode(prompt))
print(f"Raw mlx-lm: {n_out/elapsed:.1f} tok/s")
EOF
```

This bypasses every framework layer and calls the MLX compute graph directly. You'll get ~347 tok/s. This is your ceiling. Note that vLLM at C=8 exceeds it — that's not magic, it's because "total tokens across 8 requests per second" can exceed "tokens for 1 request per second" when the GPU would otherwise be idle between requests.

### What you learned

PagedAttention is the specific mechanism that makes batching work. Without it, you're limited to processing one request at a time and your throughput is bounded by single-request speed. With it, the GPU stays busy across many requests simultaneously.

Your original frustration — "it gets slower when I have two windows open" — is now fully explained and measured. And you have a concrete alternative.

---

## Chapter 3: What Does the Competition Look Like?

### The problem

You've seen vLLM. Before committing to it, you want to know: is there another engine that works differently, solves different problems, or is better for certain use cases?

### The concept you need

**RadixAttention and prefix caching**  
Imagine your application always starts every conversation with a 500-token system prompt. With standard attention, every new request has to re-compute the KV cache for those 500 tokens from scratch. SGLang's RadixAttention builds a prefix tree (radix trie) of all previously seen prompts. If two requests share a common prefix, the KV computation for that prefix is done once and reused. For applications with long shared prefixes (agents, RAG systems), this is a massive speedup.

SGLang is also the go-to engine for structured outputs — constraining the model to produce valid JSON, specific formats, or follow a grammar. It has strong support for tool-calling workflows.

**The Apple Silicon complication**  
SGLang's primary target is NVIDIA CUDA. It has an experimental MLX path (`SGLANG_USE_MLX=1`) for Apple Silicon, but it makes several assumptions about the environment that don't hold on macOS. Setting it up teaches you something important: how ML frameworks make platform assumptions, and how to work around them when you're operating outside the intended environment.

### What to do

**Step 1: Install SGLang from source**

SGLang doesn't publish pre-built arm64 wheels, so you build from source. It also needs Python 3.11 (not 3.12) for the Apple Silicon path:

```bash
uv venv venv-sglang-mlx --python 3.11

# Clone into the project folder
git clone https://github.com/sgl-project/sglang.git

# Install with the Apple Silicon MPS extras
uv pip install --python venv-sglang-mlx/bin/python \
  -e "sglang/python[all_mps]" \
  --extra-index-url https://download.pytorch.org/whl/cpu
```

**Step 2: Fix the broken platform assumptions**

When you try to start SGLang, it will fail. Each failure teaches you something about how the framework was built.

**Problem A — triton import fails**

SGLang imports `triton` (a CUDA kernel compiler) in over 45 source files. On Apple Silicon, triton doesn't exist. You need to create a stub package that satisfies all those imports without doing anything:

```bash
mkdir -p venv-sglang-mlx/lib/python3.11/site-packages/triton/{language,runtime,compiler,backends}
```

The trick is a **meta-path finder** — a Python mechanism that lets you intercept import statements before the normal file-based lookup. You create one that catches any `import triton.*` and returns an empty stub module. This means all 45+ files that import triton submodules get safe stubs without you having to patch each file.

The stub package files are already in `venv-sglang-mlx/lib/python3.11/site-packages/triton/` if you're working in this project. If you're starting fresh, see the `lab_log.md` for the full file contents.

The core of what makes this work (`triton/__init__.py`):

```python
class _TritonStubFinder:
    def find_module(self, fullname, path=None):
        # Intercept any import that starts with "triton."
        if fullname.startswith("triton.") and fullname not in sys.modules:
            return self  # "I'll handle this import"
        return None

    def load_module(self, fullname):
        # Return an empty module instead of raising ImportError
        mod = types.ModuleType(fullname)
        sys.modules[fullname] = mod
        return mod

sys.meta_path.append(_TritonStubFinder())
```

**Problem B — type annotation crashes at import time**

In `sglang/python/sglang/srt/distributed/parallel_state.py`, around line 104:

```python
@dataclass
class GraphCaptureContext:
    stream: torch.get_device_module().Stream   # ← crashes
```

Python evaluates dataclass field annotations at *class definition time*, not when you actually create an instance. `torch.get_device_module()` on Apple Silicon returns `torch.mps`, which has no `Stream` type. This crashes before any model loads.

Fix: change `Stream` to `Any` (already imported at the top of that file):

```python
stream: Any   # was: torch.get_device_module().Stream
```

**Problem C — missing torch.mps methods**

During initialisation, `ModelRunner` calls:
```python
torch.get_device_module(self.device).set_device(self.gpu_id)
torch.get_device_module(self.device).Stream()
```

`torch.mps` doesn't have `set_device` or `Stream`. In `sglang/python/sglang/srt/hardware_backend/mlx/model_runner_stub.py`, at the top of `MlxModelRunnerStub.__init__`, add:

```python
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
```

These are no-ops — the CUDA APIs are never actually *called* in the MLX inference path, only referenced during initialisation. Stubbing them out is safe.

**Step 3: Start SGLang and benchmark it**

```bash
SGLANG_USE_MLX=1 venv-sglang-mlx/bin/python -m sglang.launch_server \
  --model-path Qwen/Qwen3-0.6B \
  --port 43440 \
  --trust-remote-code \
  --disable-radix-cache \
  --disable-cuda-graph \
  --tp-size 1
```

Wait for `The server is fired up and ready to roll!`, then:

```bash
venv-vllm-metal/bin/python benchmark.py sglang --concurrencies 1 4 8 --rounds 3
```

**Step 4: If you have LM Studio installed, benchmark that too**

```bash
# Start LM Studio → Local Server → Start Server → Load qwen/qwen3-0.6b
venv-vllm-metal/bin/python benchmark.py lmstudio --concurrencies 1 4 8 --rounds 3
```

**Step 5: Run all at once to get the final comparison table**

```bash
venv-vllm-metal/bin/python benchmark.py all --concurrencies 1 4 8 --rounds 5
```

Your results (reference numbers from this machine):

| Engine | C=1 TTFT | C=1 Tput | C=4 Tput | C=8 Tput |
|--------|----------|----------|----------|----------|
| vLLM-metal | 32ms | 184 tok/s | 488 tok/s | **603 tok/s** |
| SGLang-MLX | 24ms | 172 tok/s | 254 tok/s | 454 tok/s |
| LM Studio | 51ms | 222 tok/s | 410 tok/s | 411 tok/s |
| Ollama | 103ms | 253 tok/s | 271 tok/s | 274 tok/s |
| Raw mlx-lm | — | 347 tok/s | — | — |

### What you learned

You can now make an informed engine choice based on your actual use case:

- **Interactive single queries** (C=1 TTFT): SGLang has the best first-token latency (24ms)
- **Concurrent users / batch serving**: vLLM wins clearly at C=8 (603 tok/s)
- **Simplest setup with decent performance**: LM Studio or Ollama
- **Structured outputs / JSON schemas**: SGLang (even though RadixAttention is disabled on Apple Silicon, structured generation still works)
- **Experimental / learning**: all of the above are worth understanding

You also learned something broader: even well-maintained open-source projects make platform assumptions. Understanding *why* a platform assumption exists (e.g., "this code expects CUDA's `Stream` type") and how to stub it out safely (rather than patching the source everywhere) is a transferable skill.

---

## Chapter 4: Wiring This Into Your Own Code

### The problem

You've been testing with curl. That's not how you'll actually use this in an application. You want your Python code to talk to whichever engine is running, without being tied to a specific one. Ideally, you want to swap backends by changing one line.

### The concept you need

**The OpenAI-compatible API standard**  
All four engines expose the exact same HTTP API format: `POST /v1/chat/completions` with the same JSON schema. This is intentional — it's the de-facto standard for LLM serving, originally defined by OpenAI and adopted by everyone else. It means any client built for OpenAI's API works with all four engines.

**LangChain's `ChatOpenAI` class**  
LangChain's `ChatOpenAI` was built to talk to OpenAI's servers. It accepts a `base_url` parameter so you can point it at any OpenAI-compatible server instead. This gives you access to LangChain's entire ecosystem — chains, parsers, tools — against any local engine.

**LCEL — LangChain Expression Language**  
The `|` pipe operator composes LangChain components. `prompt | llm | parser` declares a pipeline: run prompt first, feed output to llm, feed output to parser. Nothing executes until you call `.invoke()`. This lets you build reusable, composable processing pipelines.

### What to do

**Step 1: Create the LangChain environment**

Since LangChain only makes HTTP calls (no GPU compute), it doesn't need the GPU-specific venvs:

```bash
uv venv venv-langchain --python 3.12
uv pip install --python venv-langchain/bin/python \
  langchain==0.3.25 langchain-openai==0.3.3
```

**Step 2: Explore the demo script**

```bash
# Start any engine first (e.g. vLLM on :8000), then:
venv-langchain/bin/python langchain_demo.py --engine vllm
```

Look at the three patterns in `langchain_demo.py`:

**Pattern 1 — invoke():** A single synchronous call. Returns an `AIMessage` object with a `.content` attribute.

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8000/v1",  # ← change this to swap engines
    api_key="no-key",                     # required field; ignored by local servers
    model="mlx-community/Qwen3-0.6B-4bit",
    temperature=0,
    max_tokens=200,
)
result = llm.invoke("What is KV cache?")
print(result.content)
```

**Pattern 2 — stream():** Returns a generator of `AIMessageChunk` objects. Each chunk has a `.content` attribute with the token text. Use this for interactive applications where you want text to appear as it's generated.

```python
for chunk in llm.stream("What is KV cache?"):
    print(chunk.content, end="", flush=True)
```

**Pattern 3 — LCEL chain:** Build a processing pipeline. The `|` operator creates a chain that runs left to right. `StrOutputParser` is a simple component that unwraps `AIMessage` → plain string.

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_messages([
    ("system", "Answer in {style}."),
    ("human", "{question}"),
])
chain = prompt | llm | StrOutputParser()
answer = chain.invoke({"style": "one sentence", "question": "What is paged attention?"})
print(answer)   # plain string, no unwrapping needed
```

**Step 3: Run against all available engines**

```bash
venv-langchain/bin/python langchain_demo.py --engine all
```

Notice: the chain code is identical for all four engines. The only difference is the `base_url` and `model` name in the `ChatOpenAI` constructor.

### What you learned

This is the practical payoff of the OpenAI-compatible API standard: you write application logic once and it works with any engine. When you decide to move from Ollama to vLLM (because you now know vLLM is faster under load), your application code doesn't change. You update one URL.

LCEL's pipe syntax also solves a real problem: chains are declared separately from execution. You can build a chain once, pass it around as an object, and invoke it repeatedly with different inputs — or swap out the `llm` component without touching the prompt or parser.

---

## Chapter 5: Batch Jobs Without a Server

### The problem

You have a folder with 50 markdown notes you want to summarize. Running a server for this feels heavyweight — you'd have to start it, send 50 HTTP requests, then shut it down. And there's HTTP overhead on every request. Is there a simpler way?

### The concept you need

**Offline inference**  
Both vLLM and SGLang have an "offline" mode where the model loads directly into your Python process. No HTTP server, no network round-trip. You pass a batch of prompts as a Python list and get a list of results back.

vLLM's offline API:
```python
from vllm import LLM, SamplingParams
llm = LLM(model="...")
outputs = llm.generate(["prompt 1", "prompt 2", "prompt 3"], SamplingParams(...))
```

SGLang's offline API:
```python
from sglang.srt.entrypoints.engine import Engine
engine = Engine(model_path="...")
outputs = engine.generate(prompt=["prompt 1", "prompt 2"], sampling_params={...})
```

**The macOS multiprocessing trap**  
This is the most important thing in this chapter. Both `LLM` and `Engine` spawn internal subprocesses to handle model execution. On macOS, Python's `multiprocessing` module uses the `spawn` start method by default (unlike Linux, which uses `fork`).

When a process spawns, Python starts a fresh interpreter and re-imports your script from scratch to reconstruct the environment. If your engine-creation code runs at module level (outside any function), the re-import tries to create *another* engine while the first one is starting up — deadlock.

The rule: **wrap all engine code in `if __name__ == '__main__':`**. This guard evaluates to `True` only in the original process, not in spawned children.

```python
# BREAKS on macOS — engine created at import time
from vllm import LLM, SamplingParams
llm = LLM(model="...")          # this runs when the file is imported
outputs = llm.generate(...)

# WORKS — engine created only when this file is run directly
from vllm import LLM, SamplingParams

def main():
    llm = LLM(model="...")
    outputs = llm.generate(...)

if __name__ == "__main__":
    main()
```

### What to do

**Step 1: Run the vLLM offline script**

Stop the vLLM server if it's running (same model can't load twice):
```bash
kill $(lsof -ti:8000) 2>/dev/null
```

Run the batch script:
```bash
venv-vllm-metal/bin/python vllm_offline.py
```

Look at the output. You'll see:
- Load time: ~25s (loading model + allocating KV cache)
- Generation time: ~2s for 5 prompts (true batch — all processed simultaneously)
- Throughput: ~357 tok/s

**Step 2: Understand the API**

Open `vllm_offline.py` and look at the key parts:

```python
llm = LLM(
    model="mlx-community/Qwen3-0.6B-4bit",
    max_model_len=2048,   # cap context to keep memory predictable
)
params = SamplingParams(
    temperature=0,        # greedy — deterministic output
    max_tokens=150,       # max tokens per response
)
outputs = llm.generate(PROMPTS, params)   # all 5 prompts submitted as one batch
for o in outputs:
    print(o.outputs[0].text)              # decoded string
    print(len(o.outputs[0].token_ids))    # token count
```

The `SamplingParams` controls how tokens are sampled:
- `temperature=0`: greedy — always pick the highest-probability token. Deterministic, faster.
- `temperature=1.0`: sample from the distribution — varied, sometimes creative.
- `top_p=0.9`: nucleus sampling — only sample from tokens that together cover 90% of probability mass.

**Step 3: Run the SGLang offline script**

```bash
SGLANG_USE_MLX=1 venv-sglang-mlx/bin/python sglang_offline.py
```

Note the API differences:
- SGLang uses `max_new_tokens` (not `max_tokens`)
- `sampling_params` is a plain dict (not a `SamplingParams` object)
- Results are dicts: `out["text"]` and `out["meta_info"]["completion_tokens"]`
- You must call `engine.shutdown()` at the end

```python
outputs = engine.generate(
    prompt=PROMPTS,
    sampling_params={"max_new_tokens": 150, "temperature": 0},
)
for out in outputs:
    print(out["text"])
    print(out["meta_info"]["completion_tokens"])
engine.shutdown()
```

**Results on this hardware:**

| Engine | Load time | Batch time (5 prompts) | Throughput |
|--------|-----------|----------------------|------------|
| vLLM | 25.8s | 2.10s | 357 tok/s |
| SGLang | 11.5s | 2.76s | 271 tok/s |

SGLang's shorter load time is because the MLX path skips PyTorch KV-cache allocation — the model runs through MLX directly. vLLM generates faster because its Metal compute kernels are more optimised.

### What you learned

Offline mode is the right tool for batch jobs. You avoid all the server lifecycle overhead, HTTP round-trips, and connection pooling. The model loads once, processes everything, and exits cleanly.

The macOS `spawn` trap is something every Python developer who writes multiprocessing code eventually hits. The `if __name__ == '__main__':` rule isn't optional on macOS — it's structurally required by how the OS launches child processes.

---

## Chapter 6: What If Your Engine Goes Down?

### The problem

You're now running vLLM as your primary engine. Occasionally it crashes (usually when Apple Silicon's memory pressure kills it). You have Ollama always running in the background as a fallback, but switching between them manually is annoying. You want your code to automatically route to whichever engine is healthy.

### The concept you need

**The router pattern**  
Since all engines speak the same API, you can put a thin proxy in front of them. The proxy appears to be a single engine. Internally it maintains a list of backends, health-checks them periodically, and distributes requests based on rules you define.

Two specific rules are useful:
- **Round-robin**: alternate between backends. Request 1 → vLLM, request 2 → Ollama, request 3 → vLLM, etc.
- **Fastest-wins (parallel fan-out)**: send the same request to all backends simultaneously. Return whichever responds first. Cancel the others. Minimises latency at the cost of doing redundant compute.

**asyncio and `as_completed`**  
The router needs to handle many concurrent HTTP connections efficiently. Python's `asyncio` event loop does this with a single thread — instead of blocking on each HTTP call, it suspends the coroutine and processes other work while waiting. `asyncio.as_completed(tasks)` returns a generator that yields tasks as they complete — the key primitive for fastest-wins routing.

### What to do

**Step 1: Install the async HTTP server library**

```bash
uv pip install --python venv-langchain/bin/python aiohttp==3.11.18
```

**Step 2: Start the router**

Start at least two engines first (e.g., vLLM on :8000 and Ollama on :11434), then:

```bash
venv-langchain/bin/python router.py
```

The startup output tells you what the router found:
```
Running initial health checks...
  vllm       UP
  sglang     DOWN
  ollama     UP
  lmstudio   DOWN
Router ready.
```

**Step 3: Check status and test round-robin**

```bash
# See what the router knows about each backend
curl -s http://localhost:9000/router/status | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('Healthy:', d['healthy_count'], 'backends')
for b in d['backends']:
    mark = 'UP  ' if b['healthy'] else 'DOWN'
    print(f'  {mark} {b[\"name\"]:10s}  handled={b[\"requests_handled\"]}')
"

# Send 4 requests — watch the router log to see them alternate
for i in 1 2 3 4; do
  curl -s http://localhost:9000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"any","messages":[{"role":"user","content":"ping"}],"max_tokens":5,"stream":false}' \
    > /dev/null
done
```

Check the router log — you'll see requests alternating between vllm and ollama.

**Step 4: Test fastest-wins**

```bash
curl -s http://localhost:9000/v1/fastest \
  -H "Content-Type: application/json" \
  -d '{"model":"any","messages":[{"role":"user","content":"ping"}],"max_tokens":5}' | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print('Winner:', d.get('_router_winner'))"
```

The `_router_winner` field is added by the router so you can see which backend answered. The response includes the original OpenAI-compatible payload.

**Step 5: Use the router from LangChain**

```python
from langchain_openai import ChatOpenAI

# Point LangChain at the router instead of a specific engine
llm = ChatOpenAI(
    base_url="http://localhost:9000/v1",
    api_key="no-key",
    model="any",   # router rewrites to the correct model name per backend
)
result = llm.invoke("What is paged attention?")
```

Your LangChain application doesn't know or care which engine answered.

### What you learned

The router pattern is the practical consequence of the OpenAI-compatible standard. Because every engine uses the same API, a proxy doesn't need to understand anything about LLMs — it just forwards HTTP requests and checks health endpoints. The engines are fully interchangeable from the proxy's perspective.

The round-robin and fastest-wins patterns represent two different optimization goals:
- Round-robin: even load distribution, avoid overloading one engine
- Fastest-wins: minimum latency, don't care about compute waste

In production (with real GPU servers), fastest-wins is sometimes used as a "warm cache" strategy — whichever server already has the prompt prefixes in its cache will respond faster.

---

## Chapter 7: Exploring Interactively vs. Running Reliably

### The problem

You've been writing scripts to test things, but iterating is slow — change the script, re-run it, wait for output, change again. You want to run one cell at a time, see the output immediately, and adjust your next step based on what you see. But you've also learned that certain things (the offline `LLM` class, the server processes) need to run as scripts, not interactively.

You need to understand when each form is the right tool.

### The concept you need

**Jupyter notebooks vs. Python scripts**

A Jupyter notebook is a document that mixes code cells, output, and markdown explanation. You run cells individually. Output appears inline. This is ideal for exploration — you can run a single request, see the response, decide whether to try a different prompt, and continue without re-running everything from the start.

The limitation: Jupyter runs all cells in a single Python kernel. That kernel is `__main__`. When `LLM()` spawns a subprocess, the subprocess re-imports `__main__` — but `__main__` in a Jupyter context is the kernel itself, not a clean script. The `if __name__ == '__main__':` guard doesn't help because it's always true in a kernel.

The practical rule:
- **Notebooks**: anything that talks to a running server (HTTP calls, LangChain), iterative experimentation, comparison, visualisation
- **Scripts**: anything that spawns processes (offline `LLM`, `Engine`), long-running servers, CI/CD

The workaround for running offline scripts *from* a notebook:

```python
import subprocess

# This runs in a separate OS process — Jupyter's kernel is not affected
result = subprocess.run(
    ["venv-vllm-metal/bin/python", "vllm_offline.py"],
    capture_output=True, text=True
)
print(result.stdout)
```

### What to do

**Step 1: Set up Jupyter**

```bash
uv pip install --python venv-langchain/bin/python jupyterlab ipykernel

# Register the venv as a named kernel so Jupyter can find it
venv-langchain/bin/python -m ipykernel install \
  --user \
  --name inference-lab \
  --display-name "Inference Lab (langchain)"
```

**Step 2: Open the notebook**

Start at least one engine (vLLM on :8000 or Ollama on :11434), then:

```bash
venv-langchain/bin/jupyter lab
```

Open `inference_lab.ipynb`. In the top right, select kernel → "Inference Lab (langchain)".

**Step 3: Work through the notebook sections**

The notebook has four sections:

1. **Raw HTTP** — `httpx` calls to `/v1/chat/completions`. Run the non-streaming cell first, read the output, then run the streaming cell and watch tokens arrive in real time.

2. **LangChain** — `invoke()`, `stream()`, LCEL chain. The cross-engine comparison cell loops over all running backends and shows their responses side by side. This is where notebooks shine — you'd never want to set up a script for this kind of interactive comparison.

3. **Router** — Only runs if `router.py` is already running. Start it in a terminal, then come back and run these cells to see round-robin and fastest-wins from the notebook.

4. **Offline batch** — This section explains why offline APIs can't run inside a Jupyter kernel, then shows the `subprocess.run()` workaround. Run it and you'll see `vllm_offline.py` execute as a child process with its output captured.

### What you learned

The notebook vs. script choice is not about preference — it's about structural constraints. Jupyter's single-kernel execution model and Python's `spawn` multiprocessing model are fundamentally incompatible with the offline batch APIs. Knowing this upfront saves you from debugging mysterious deadlocks.

The `subprocess.run()` workaround is genuinely useful — you get the exploration benefits of a notebook (run one thing at a time, see output inline) while the heavy work happens in a clean process that doesn't conflict with the kernel.

---

## Where You Are Now

You started with "Ollama feels slow sometimes" and you ended up here:

| What you can do now | What taught you this |
|---------------------|----------------------|
| Measure TTFT, throughput, and concurrency scaling for any engine | Ch. 1 — benchmarking |
| Explain why vLLM scales to C=8 and Ollama doesn't | Ch. 2 — PagedAttention |
| Set up SGLang on Apple Silicon despite its CUDA assumptions | Ch. 3 — platform patching |
| Connect any engine to LangChain with one URL change | Ch. 4 — OpenAI-compatible API |
| Process a batch of documents without running a server | Ch. 5 — offline batch + macOS spawn |
| Route traffic across engines with automatic failover | Ch. 6 — router pattern |
| Know when to use a notebook vs. a script, and why | Ch. 7 — execution models |

---

## Quick Command Reference

```bash
# Start vLLM
venv-vllm-metal/bin/python -m vllm.entrypoints.openai.api_server \
  --model mlx-community/Qwen3-0.6B-4bit --port 8000 --max-model-len 4096

# Start SGLang
SGLANG_USE_MLX=1 venv-sglang-mlx/bin/python -m sglang.launch_server \
  --model-path Qwen/Qwen3-0.6B --port 43440 \
  --trust-remote-code --disable-radix-cache --disable-cuda-graph --tp-size 1

# Start Ollama
ollama serve

# Check what's running
for port in 8000 43440 11434 1234; do
  curl -sf http://localhost:$port/v1/models >/dev/null 2>&1 \
    && echo "port $port UP" || echo "port $port down"
done

# Benchmark
venv-vllm-metal/bin/python benchmark.py all --concurrencies 1 4 8

# Offline batch
venv-vllm-metal/bin/python vllm_offline.py
SGLANG_USE_MLX=1 venv-sglang-mlx/bin/python sglang_offline.py

# LangChain demo
venv-langchain/bin/python langchain_demo.py --engine all

# Router
venv-langchain/bin/python router.py

# Notebook
venv-langchain/bin/jupyter lab     # then open inference_lab.ipynb

# Stop anything by port
kill $(lsof -ti:8000)   # vLLM
kill $(lsof -ti:43440)  # SGLang
kill $(lsof -ti:11434)  # Ollama
kill $(lsof -ti:9000)   # router
```
