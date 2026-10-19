# Deepgram Builder Essentials: Technical Track

A self-paced course. Build a real-time voice agent in Python, one runnable module at a time. You speak, it listens on Flux, thinks with an LLM, answers in a natural voice, stops when you interrupt it, and calls your code when it needs something it can't know.

Every step is a complete, working program that opens a browser tab and talks to you. The agent is entirely Python: the browser is only the microphone and the speaker.

You build one agent for one client (**Northwind Clinic**, a patient-access line) and every module
adds one capability to it. At the end you submit that agent for the **Builder Essentials** badge.

Start at Module 0 or drop in at Module 5; each folder already contains everything the previous
modules built, so the next folder is both the answer key and a valid starting point.

## Prerequisites

| You need | Why you need it |
|---|---|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | The only thing to install. It fetches Python 3.13 and every dependency itself, so you don't need Python already. |
| A free [Deepgram API key](https://console.deepgram.com/signup?jump=keys) | Signup takes a minute, and the free credit covers this course with room to spare. |
| A current browser | Chrome, Firefox, or Safari. The browser is the microphone and the speaker: it needs `getUserMedia` and `AudioWorklet`. |
| Wired headphones | Your browser cancels most of the echo from your speakers, but not all of it on every browser, and Step 5 is where the difference shows. |
| A terminal | macOS, Linux, Windows, and WSL all work: under WSL the audio is Windows' problem, not yours. |

Being comfortable with Python helps. An audio or machine-learning background doesn't.

**Don't want to install anything?** [.devcontainer/README.md](.devcontainer/README.md) runs the whole workshop in a container: GitHub Codespaces needs nothing local at all, and VS Code Dev Containers needs only Docker. Both arrive with `uv sync` already run and `.env` already created, so you paste your key and start at Step 1. Your microphone and browser stay on your machine either way; the only thing a container takes away is the `--local` flag below.

## Setup

Once you have uv and a key:

```bash
uv sync
cp .env.example .env      # then paste your key into .env
uv run steps/01-setup/main.py
```

One virtual environment serves every step. You run `uv sync` once.

That last command checks your key in the terminal, then opens a browser page that checks the rest: microphone permission, the audio APIs, input level, and output. Better here than mid-conversation later.

Every step from Step 2 on serves a page at `http://127.0.0.1:8000` and opens it for you. **It has to be `127.0.0.1`**: browsers only grant microphone access on a secure context, and a LAN address is not one.

### Running in another region

Deepgram serves the same APIs from more than one place. Global is the default; the EU and AU endpoints process audio inside those geographies. Pick one in `.env`:

```bash
DEEPGRAM_REGION=eu        # global (default), eu, au, or in
```

That is the whole change. Your key works in every region, no step's code names one, and every step reads the same `.env`, so one line moves all of them together.

Step 1 then starts the agent against whichever endpoint you picked and reports whether that endpoint serves all three models. Model availability differs by region and moves over time, so that (not the key, and not whether the host answers) is the question worth asking before a room of people hits Step 2.

[web/region.py](web/region.py) has the details, and the same mechanism points the workshop at a Deepgram Dedicated or self-hosted deployment.

### Prefer the terminal?

Add `--local` to any step and it uses your system microphone and speaker through PortAudio instead, with no browser involved:

```bash
uv run steps/10-final/main.py --local
```

Same agent code either way: see [web/README.md](web/README.md) for what changes underneath.

## The modules

Each folder holds the finished state of the module before it. Open `LAB.md` for instructions (Module 10 ships a `README.md` instead), work the `TODO (Step N.x)` blocks in `main.py`, and check the next folder if you get stuck: it's the answer key.

Inside a TODO block, `#:` marks the instructions. Everything else is code, commented out at the indentation it belongs at, select those lines and press `Cmd+/` (`Ctrl+/` on Windows and Linux) to uncomment them where they sit.

| Module | You build | Run it | Time |
|---|---|---|---|
| [0. Welcome, the loop, and the capstone](steps/00-overview/LAB.md) | *(read only)* The parts of a voice agent, and the client | — | 15 min |
| [1. Set up and smoke-test](steps/01-setup/LAB.md) | Verify key, browser, and microphone | `uv run steps/01-setup/main.py` | 15 min |
| [2. Settings and the event lifecycle](steps/02-connect/LAB.md) | The WebSocket and settings handshake | `uv run steps/02-connect/main.py` | 20 min |
| [3. Hearing the agent](steps/03-hear-the-agent/LAB.md) | Playback: the greeting plays | `uv run steps/03-hear-the-agent/main.py` | 25 min |
| [4. The full loop and turn-taking](steps/04-talk-to-the-agent/LAB.md) | Microphone input: a real conversation | `uv run steps/04-talk-to-the-agent/main.py` | 30 min |
| [5. Interruption done right](steps/05-barge-in/LAB.md) | Stopping the agent mid-sentence | `uv run steps/05-barge-in/main.py` | 25 min |
| [6. Prompting for the ear](steps/06-make-it-yours/LAB.md) | The Northwind job, voice, and prompt rules | `uv run steps/06-make-it-yours/main.py` | 20 min |
| [7. Function calling](steps/07-function-calling/LAB.md) | Checking availability, and booking exactly once | `uv run steps/07-function-calling/main.py` | 35 min |
| [8. Identity and the PII boundary](steps/08-healthcare/LAB.md) | Verification, vocabulary, and a human handoff | `uv run steps/08-healthcare/main.py` | 25 min |
| [9. Turn-taking, latency, observability](steps/09-optimize/LAB.md) | Thresholds, latency, and finding a call again | `uv run steps/09-optimize/main.py` | 25 min |
| [10. Reference agent and capstone](steps/10-final/README.md) | The complete implementation, and the submission | `uv run steps/10-final/main.py` | 20 min |
| [Appendix A, Bring your own LLM](steps/06b-bring-your-own-llm/LAB.md) *(optional)* | The brain on Amazon Bedrock, in your AWS account | `uv run steps/06b-bring-your-own-llm/main.py` | 15 min |

Folder numbers match module numbers, and so do the `TODO (Step N.x)` markers: Module 8 lives in
`steps/08-healthcare/` and carries `TODO (Step 8.x)`. Appendix A is the one exception: it branches
off Module 6, so `steps/06b-bring-your-own-llm/` carries `TODO (Step 6b.x)`.

Short on time? Modules 1 to 5 are the core: finish those and you have a working voice agent. Module 9
is dials rather than code and makes a natural second sitting. And because every folder is
complete, skipping ahead costs you the typing, not the course.

Appendix A is a detour off Module 6, not a link in the chain, and it is the only part needing a
credential beyond your Deepgram key, AWS access with Bedrock model access granted, which usually
takes longer to obtain than the appendix takes to do.

Each module ends with a **Checkpoint** (the observable thing that must be true before you move on)
and a five-question quiz.

## The badge

Two parts, both described in [`course/capstone/`](course/capstone/):

- **A knowledge check**: 30 questions drawn from the module quizzes, 80% to pass. Neither is
  published here: both are taken in the course's learning platform, and the module quizzes are
  what you revise from.
- **A practical**: submit your agent with an [evaluation scorecard](course/capstone/SCORECARD.md) and a one-page rationale, scored against a [published rubric](course/capstone/RUBRIC.md).

Read the rubric before you start rather than at the end: every module contributes something it
asks for. [`course/DEFERRED.md`](course/DEFERRED.md) lists what this course deliberately does not
cover, so you know the edges.

## What you'll learn

- Configuring speech-to-text, an LLM, and text-to-speech through a single WebSocket
- Why Flux does turn detection server-side, and what that removes from your client
- Streaming microphone audio without blocking the thread that plays the reply
- Clearing queued playback the instant a user interrupts, the difference between a demo and something people will use
- Wiring client-side function calls into a live conversation, so the agent answers from your data rather than its own imagination
- Gating an irreversible action behind a spoken confirmation, in code rather than in a prompt
- Turning a general agent into a domain specialist: keyterms, guardrail prompts, and payloads that carry only what the agent may say aloud
- Trading turn-detection latency against accuracy, and measuring it honestly

The audio plumbing itself lives in [web/](web/), a small FastAPI bridge and two AudioWorklets that every step shares and you read rather than write. [web/README.md](web/README.md) explains what it does and the three things about it that are easy to get wrong.

## Getting help

- [Deepgram Voice Agent docs](https://developers.deepgram.com/docs/voice-agent)
- [Flux docs](https://developers.deepgram.com/docs/flux)
- [GitHub Discussions](https://github.com/orgs/deepgram/discussions)
- [Discord](https://discord.gg/xWRaCDBtW4)

## Maintaining this course

```bash
uv run scripts/verify_steps.py
```

Checks the manifest in [`course/modules.yml`](course/modules.yml) against `steps/`, that every
module compiles and lints, that no `TODO` marker leaks into the next folder's answer key, that every
module ships a lab, that labs carry the course sections, that every relative link resolves, that no
prose reads as though a facilitator were present, that the Northwind scenario is uniform across the
cascade folders, that no module asserts a factual claim a later module disproves, that every
advertised function schema names parameters its handler accepts, and that the capstone stays inside
what the course teaches.

Run it after editing anything under `steps/`, `course/`, or `web/`: ruff covers all three. Ten
near-identical copies of `main.py` drift quietly, and drift between a module and its answer key is
the failure mode that surfaces in front of a learner.

This repository holds the course itself. The material for *teaching* it, video narration, the
on-screen cards, and the badge knowledge check, lives in a separate private repository, which
reads `course/modules.yml` from here so module numbering cannot drift between the two. Changing a
module's identity, ordering, or `exempt_from` means running the verifier in both.

> Looking for the instructor-led version? This course was adapted from a three-hour facilitated
> workshop, which lives on in its own repository with its run of show, projection deck, and
> facilitator notes intact.
