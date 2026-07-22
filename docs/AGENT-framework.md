# The AGENT Framework

Source: "You're Not Behind (Yet): How to Build Your First AI Agent (Full Guide)"
(https://youtu.be/Bm84BAtOfQw) — distilled from the full transcript, saved 2026-07-21.

This is the design spec we're building our financial project against. Every decision in
this repo should trace back to one of the five letters below.

---

## 0. Chatbot vs. Agent

| | Chat | Agent |
|---|---|---|
| Analogy | A meeting | An employee |
| Direction | Pulls on you (waits for prompts) | Pushes on you (acts, then checks in) |
| Output | An answer you copy/paste | A completed workflow |
| Result | Buys back time | Lets you let go of a whole area |

An agent without a **loop** is just an automation — it does the job once and stops.

### The DATA loop (what makes it an agent)

- **D — Diagnose** — figure out what the actual problem is (consultant)
- **A — Assemble** — build a plan, pick/design tools (architect)
- **T — Take action** — execute (operator)
- **A — Assess** — check its own work, catch misses, improve (reviewer)

### Rule of 3 R's — is this worth agentifying?

1. **Repetitive** — do I do this weekly (or more)?
2. **Rules-based** — same input → same output, following a clear process?
3. **Return on time** — will building it cost less time than doing it manually forever?

If it's occasional, fuzzy, and cheap to just do — stick with chat. Don't build.

---

## A — Aim for a specific outcome

Define the **outcome**, not the steps. Climbing a mountain: taking a step is the task,
reaching the summit is the outcome. Aim at the summit; the AI often routes better than
you would. The #1 reason people fail at agents is trying to control every step.

Three moves:

1. **Why before how.** Give it the reason for the goal so it can make smart calls alone.
   - *Weak:* "Sort my emails by sender."
   - *Strong:* "I need to spend less time managing my inbox."
2. **Write a DoD (Definition of Done).** Specific, measurable, one sentence.
   - *Weak:* "Handle my emails."
   - *Strong:* "Done means every morning at 9am the inbox is empty, replies are drafted
     in my voice, anything needing me is flagged to the top, and nothing important slips."
   - If you can't picture it done, the agent can't hit it.
3. **Reverse prompting** (the advanced move). State the result you want, then tell the AI
   to *ask you the questions it needs* for full clarity — then let it build the plan.

> If you can't state the outcome in one sentence, you're not ready to build.

---

## G — Give it an identity

Out of the box an LLM knows a little about everything and nothing specifically well. An
identity focuses that power. **Tighter definition = better output.** (Cited example: an
airline support agent stripped of its rulebook dropped from 33% → 11% success. Same
model, same task, 3x dumber because it forgot who it was.)

Three plain-English files:

| File | Answers | Contains |
|---|---|---|
| **Soul file** | *How it behaves* | Personality, voice, quirks, values, tone, banned phrases, what it does when unsure |
| **Identity file** | *Who it is* | Name, role, job description, **lanes** (hard boundaries on what it may touch) |
| **User file** | *Who it works for* | Your role, goals, priorities, how you like things done, key context |

**Pro tip: don't write these yourself.** Prompt template:

> I want to build an AI agent that [AIM FROM STEP A]. Create its three identity files —
> a soul file, an identity file, and a user file — and ask me any questions you need to
> fill these in accurately. Then write all three.

(Note the reverse prompting baked in.)

---

## E — Equip it

**Context is the moat. Garbage context in, garbage context out.**

### The desk metaphor (the context window)

| Desk location | What it is |
|---|---|
| On the desk — playbooks | Processes & procedures for doing the work |
| On the desk — identity files | The agent's constitution |
| On the desk — tools | Connections to other systems (APIs, connectors) |
| Above the desk — loops | Schedules, the heartbeat |
| Under the desk — filing cabinets | Memory: available but not cluttering the desk |

**Context rot** = dumping everything on the desk. It answers, but without certainty,
because it can't find anything cleanly.

### Two ways to capture your process

1. **Camcorder method** (workable, not best) — record yourself doing the task while
   narrating, hand the recording to AI, have it write the playbook.
2. **Reverse-engineer from the source** (recommended) — connect the agent to the real
   data and have it learn the pattern from your own history.
   > Connect to my [SOURCE]. Read the last 50 [ITEMS]. Study how I actually work — my
   > tone, my structure, my judgment calls, the phrases and patterns I use most. Then
   > write a style guide / playbook that captures it.

   Then **test it**: have it produce output on live items, correct that output, and feed
   the corrections back to tighten the playbook.

### Solidify into system prompts

One system prompt **per sub-process**, not one giant prompt. (Inbox example: sort, reply,
forward, escalate, report.)

---

## N — Narrow the scope

One specialist per job. You wouldn't ask your admin assistant to also run marketing and
take sales calls.

- Never build a **mega-agent**. It creates context rot and confusion.
- Split work across **sub-agents**, each great at one thing. (Example: one agent writes
  code, a *separate* agent reviews it.)
- Add a **manager/orchestrator agent** whose only job is delegation — it does no work
  itself, routes tasks to sub-agents, monitors them, fixes them, and reports to you.
  You talk to one agent; it talks to the rest.

  > You're my manager agent. You never do any tasks yourself. When work comes in, you
  > only route it to sub-agents dedicated to that one specific job. If a job touches
  > multiple areas, split it into separate sub-agents, one per area. You coordinate and
  > report back to me.

### Model selection (match horsepower to task, it's a cost lever)

| Model | Use for |
|---|---|
| **Haiku** | Simple, high-volume: sorting, labeling, quick drafts. Cheapest. |
| **Sonnet** | Day-to-day: research, writing, most code. |
| **Opus** | Reasoning, complex builds, managing agents. |
| **Fable** | Orchestration/consulting; long-running, complex, low-information tasks. Most expensive. |

Pattern: **build with Opus/Fable, run on Sonnet/Haiku.** (Anecdote: a refactor that
would've cost ~$150 on Opus cost ~$1.50 on Haiku.)

---

## T — Trust in stages

Building is the easy part. Letting it act without you is the scary part. Don't hand over
the car keys on day one — but do eventually take your hand off the wheel, or you've just
hired a driver and steered for them.

The ladder:

1. **Set guardrails first** — encode capabilities and hard limits in the identity files
   (can it spend money? decide? draft only, never send?).
2. **Approve everything at first** — "show me what you would do." Never YOLO.
3. **Loosen the leash** — expand permissions as it earns them, area by area.
4. **Give it a heartbeat** — a recurring schedule so it runs without being asked.

Goal state: you leave the room and the work still gets done. If you're babysitting it,
you haven't bought back any time.

---

## Checklist for this project

- [ ] **A** — One-sentence outcome + measurable DoD written down
- [ ] **G** — Soul / identity / user files generated via reverse prompting
- [ ] **E** — Data sources connected; playbook reverse-engineered; system prompts per sub-process
- [ ] **N** — Scope narrowed; sub-agents split out; models assigned per task
- [ ] **T** — Guardrails encoded; approval mode first; schedule/heartbeat last
