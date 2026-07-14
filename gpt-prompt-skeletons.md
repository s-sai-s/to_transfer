# GPT Prompt Skeletons, by Model

We kept running into the same problem: every GPT model family wants its prompts shaped a little differently, and we'd re-learn that the hard way each time we switched models. So we went through OpenAI's cookbooks and prompting guides (the GPT-4.1 guide, the GPT-4.5 release notes, the GPT-5 / 5.2 / 5.4 guides and model guidance page, the o-series reasoning best practices, and the general Chat Completions docs) and pulled out the skeleton each one actually recommends.

To make these easy to compare and swap between, every template below uses the same variable names: `{role}`, `{task}`, `{context}`, `{rules}`, `{examples}`, `{format}`, `{reasoning}`, `{tools}`. Same prompt content, different shape per model.

---

## GPT-4.1 / GPT-4o

These models are literal. They follow instructions closely but won't infer what you meant if you didn't say it — so be explicit, use clear delimiters (Markdown headers or XML tags both work fine), and put your most important instructions at both the top *and* bottom of the prompt. Repeating the task at the end genuinely helps on longer prompts — think of it as a sandwich.

```markdown
# Role
{role}

# Task
{task}

# Context
{context}

# Rules
{rules}

# Examples
{examples}

# Output Format
{format}

# Reminder
{task}
```

A couple of things worth calling out:
- That closing `{task}` repeat isn't filler — it measurably improves adherence once the prompt gets long.
- If this is an agentic/tool-use prompt, add three reminder lines near the top of `{rules}`: keep going until the task is actually resolved (persistence), use tools to gather info instead of guessing, and plan/reflect between tool calls.

---

## GPT-4.5

GPT-4.5 is the odd one out here — a large, non-reasoning model built for world knowledge, writing quality, and EQ rather than STEM/agentic work. It infers intent more liberally than 4.1, so you don't need the same rigid scaffolding. Plain, conversational instructions work about as well as strict sections, and honestly read better. We kept the same variables but wrote them more like prose than a spec.

```markdown
{role}

{task}

Context: {context}

Keep in mind: {rules}

For reference, here's what good output looks like:
{examples}

Format your response as: {format}
```

A couple of things worth calling out:
- Skip the GPT-4.1-style task repeat at the end — GPT-4.5 holds onto earlier instructions fine within a turn, and over-structuring just makes it sound stiffer, which works against its actual strength.
- There's no `{reasoning}` or `{tools}` knob here — it's not a reasoning model and didn't get the same agentic tool-calling training as 4.1/GPT-5, so if you need reliable tool use, spell it out explicitly in `{rules}`.

---

## GPT-5 / GPT-5.1

GPT-5 wants a stricter, more sectioned prompt than 4.1, plus a couple of new control knobs: `reasoning_effort` and verbosity. For agentic prompts it also wants an explicit "when do I stop" block — without one it tends to either give up too early or keep grinding past the point of usefulness.

```markdown
# Role and Objective
{role}
{task}

# Instructions
{rules}

## Sub-categories for more detailed instructions
- Context gathering: {context}
- Tool usage: {tools}
- Stop conditions: (define when the model should stop and answer vs. keep working)

# Reasoning Effort
{reasoning}

# Output Format
{format}

# Examples
{examples}

# Final Instructions
{task}
```

A couple of things worth calling out:
- `{reasoning}` maps directly to the `reasoning_effort` API param (minimal/low/medium/high) — if you can't set it via the param for whatever reason, state it in the prompt text too.
- Keep `{rules}` short and numbered. GPT-5 is noticeably sensitive to conflicting instructions and will just latch onto whichever one it read most recently.

---

## GPT-5.4 / GPT-5.4-mini

GPT-5.4 (and the mini variant — pitched as the strongest small model for coding, computer use, and subagent workloads) is the same GPT-5 family, stretched further: a 400K-token context window, a new `xhigh` reasoning tier, and much more emphasis on keeping the model in scope and re-grounded across long documents. OpenAI's own guidance here leans toward modular, reusable rule blocks rather than one fixed template, but we kept the section layout consistent with the rest of the GPT-5 line so it's easy to diff against.

```markdown
# Role and Objective
{role}
{task}

# Instructions
{rules}

## Sub-categories for more detailed instructions
- Context gathering / long-context handling: {context}
- Scope constraints: (explicitly forbid extra features / scope creep beyond {task})
- Tool usage: {tools} (state parallelization and verification requirements)
- Uncertainty handling: (when to ask a clarifying question vs. state assumptions)
- High-risk self-check: (pre-finalization verification for legal/financial/irreversible actions)
- Stop conditions: (define when the model should stop and answer vs. keep working)

# Reasoning Effort
{reasoning}

# Verbosity
(separate from {format} — a short length/detail constraint, e.g. "terse for simple asks, detailed for multi-step tasks")

# Output Format
{format}

# Examples
{examples}

# Final Instructions
{task}
```

A couple of things worth calling out:
- `{reasoning}` now spans `none` (default) / `low` / `medium` / `high` / `xhigh`. `xhigh` is new to the 5.4 line — save it for genuinely hard multi-step or agentic work, not everyday requests.
- With a 400K context window, don't assume everything stays equally salient. Have `{context}` include instructions to re-ground on specific sections or citations once a document passes ~10K tokens.
- If you're migrating a prompt over from GPT-5/5.1/5.2, keep your existing `{reasoning}` level as the baseline and only dial it down if you're confident you don't need the extra rigor — don't assume 5.4 needs *more* effort than earlier versions by default.

---

## o1 / o3 / o4-mini

These are reasoning models — they already do internal chain-of-thought before answering, so asking them to "think step by step" or reason out loud is redundant at best and actively wastes reasoning tokens at worst. Keep the prompt minimal, say everything you need once, and be precise about the goal and constraints. Skip the heavy delimiters and roleplay scaffolding you'd use for GPT-4.x — plain, direct language works better here.

```markdown
Goal: {task}

Context: {context}

Constraints: {rules}

Output format: {format}
```

A couple of things worth calling out:
- We left `{examples}` out of the default skeleton on purpose — few-shot examples are usually unnecessary for these models and can actually anchor them to the example's reasoning path instead of the real problem. Only add zero-shot input/output pairs if your output *format* is ambiguous, not to demonstrate how to think.
- Don't bolt on "let's think step by step" or anything like it — it's redundant with what the model already does internally, and it burns hidden reasoning tokens for nothing.

### Variant: xhigh reasoning effort (deep research / long agentic runs)

Some of the newer o-series and reasoning-line models expose an extended effort scale — `none` / `minimal` / `low` / `medium` / `high` / `xhigh` — though support varies by model, so check the specific model page before relying on a value. `xhigh` is aimed at deep research, async work, and long agentic runs, not day-to-day requests.

```markdown
Goal: {task}

Context: {context}

Constraints: {rules}

Reasoning effort: {reasoning}

Output format: {format}
```

A couple of things worth calling out:
- Save `xhigh` for work you expect to run long or async — multi-step research, large-codebase agentic tasks. It trades latency for depth, so it's not something you want as a blanket default.
- For long-running, tool-heavy flows, some models add a `phase` control (`commentary` vs. `final_answer`) so they don't stop early mid-task. That's an API/tool-config setting, not something you need to spell out in `{rules}` prose.

### Variant: tool / function calling (o3, o4-mini and successors)

These models call tools natively as part of their internal reasoning, not as a bolt-on step. The structure that works best is three tiers: a developer message for role and boundaries, tool descriptions that actually carry the usage rules, then the user request.

```markdown
# Developer Message
{role}
{tools} — for each tool: when to call it, when NOT to call it, how its arguments should be constructed (put these rules in the tool/function description itself, not just in prose)

# User Message
{task}

Context: {context}

Constraints: {rules}

Output format: {format}
```

A couple of things worth calling out:
- Don't add "think step by step before calling a tool" or anything similar — these models already reason internally before each call, and asking for more can actually hurt performance.
- Put invocation criteria and argument-construction rules inside each tool's `description` field (that's part of `{tools}`), not in the surrounding prompt text. Treat the description as the actual contract between the model and the tool.
- In multi-turn tool use, pass back the reasoning items from the previous function call along with your function's output, not just the raw result — that's what keeps the reasoning continuous across calls.

---

## GPT-3.5 / legacy chat-completions

The older, less literal models actually do better with short, direct, imperative prompts — and unlike the newer models, few-shot examples pull real weight here. Skip the long structured documents; a simple format cue at the end is enough.

```markdown
{role}

Instructions: {rules}

Task: {task}

Context: {context}

Examples:
{examples}

Respond in this format: {format}
```

---

## Variable cheat sheet

Same meaning across every template above:

| Variable | What goes here |
|---|---|
| `{role}` | Who the model should act as / its persona |
| `{task}` | The one explicit objective |
| `{context}` | Background, documents, retrieved data it needs |
| `{rules}` | Constraints, do's and don'ts |
| `{examples}` | Few-shot input/output pairs (use sparingly for o-series) |
| `{format}` | The exact output shape — JSON schema, markdown structure, length limits |
| `{reasoning}` | Reasoning depth: none/low/medium/high (GPT-5/5.1), plus xhigh (GPT-5.4/5.4-mini and newer o-series); skip for GPT-4.x/4.5 (not a real knob there) and for o-series where it's implicit |
| `{tools}` | Tool-calling rules — only needed for agentic prompts |
