# Module 0: Welcome, the loop, and the capstone

**Goal:** Understand the parts of a voice agent, and meet the client you'll build one for.

**You'll learn**

- What the Builder Essentials badge certifies, and how to earn it
- The three models every voice agent needs, and what each one does
- What the Voice Agent API orchestrates so you don't have to
- Why Flux changes where turn-taking happens, and what that removes from your code
- How to find the answer to any module, whenever you're stuck

No code in this module. Read it, then run Module 1.

## Two agents, one call

Picture the same call answered twice.

The caller says "I need to move my appointment from Tuesday to, " and the first agent cuts in with
"Great, I've moved it to Tuesday." Wrong day, and it interrupted her to get there.

The second agent waits for her to finish, reads back "Thursday the nineteenth at ten a.m., is that
right?", hears yes, and books it once.

Same speech model. Same language model. The difference is everything in between: and that is what
this course teaches you to build.

## Your client for the whole course

Every module adds one capability to one agent, for one client.

> **Northwind Clinic** runs a patient-access line, and forty percent of its calls are scheduling.
> They want an agent that verifies the caller by **date of birth** and a **confirmation code**,
> **checks availability**, **books or reschedules**, and **transfers to a human** when someone
> describes an emergency or gets frustrated.
>
> Constraints that shape the build: protected health information stays inside the clinic's
> environment, callers are on phones, and they have every accent you can imagine.

That is not a toy scenario. It is the shape of the project you'd actually be staffed on. The full
brief (the synthetic patient records, the canonical prompt, the function list) lives in
[the scenario brief](../../course/SCENARIO.md).

> **Demo only.** No real patient data appears in this course. Nothing here is a
> HIPAA-compliant design, and nothing here should be pointed at real patient data. The boundary
> techniques you'll build in Module 8 are real techniques; the compliance program around them is
> out of scope.

## A voice agent is three models in a loop

Audio comes in, audio goes out, and a model in the middle decides what to say. Each job belongs to a different kind of model.

**Speech-to-text (STT)** turns microphone audio into words. This course uses **Flux**, Deepgram's conversational speech-to-text model. Flux streams transcripts as you speak, so nothing waits for a complete utterance.

**A large language model (LLM)** is the brain. It takes the transcript, mixes it with the conversation history and the agent's standing instructions, and decides what to say back. We use OpenAI's `gpt-4o-mini` because it's fast and cheap, and speed matters more than raw capability when somebody is waiting to hear a reply. The same pattern works with Anthropic, Google, Groq, and AWS Bedrock. You swap a provider class, not your architecture.

**Text-to-speech (TTS)** turns the reply back into audio. We use **Flux TTS**, Deepgram's streaming voice engine built for conversation.

> **Those speech models don't have to run on Deepgram's infrastructure.** Flux, Nova-3, and Aura-2 are on AWS Marketplace and [deploy to Amazon SageMaker endpoints](https://developers.deepgram.com/docs/deploy-amazon-sagemaker) in your own AWS account and VPC, which is the answer when audio can't leave your infrastructure at all. Worth knowing about; it isn't what this course does. Everything here runs on the hosted Voice Agent API, and that's a different path, SageMaker's network isolation blocks the outbound LLM calls the orchestrator depends on, so the Agent API itself doesn't run there.

## The Voice Agent API does the orchestration

You could wire those three together yourself: call your own STT, pipe the transcript into your own LLM call, feed the response into your own TTS. You'd spend most of your time on plumbing and latency, and very little on what the agent actually does.

The Voice Agent API collapses all three into one WebSocket. You describe what you want:

- Which STT model
- Which LLM provider and model
- Which TTS voice
- The agent's personality and greeting

…and you get a socket. Audio bytes go in, audio bytes come out. Deepgram runs the pipeline server-side and manages the handoffs between providers.

Over the next nine modules you *configure that orchestrator* and react to what it sends you. You will never reimplement it.

That division is the mental model for the whole course. **You own** the prompt, the functions the
agent can call, and the evaluation that proves it works. **Deepgram owns** the seams between
listening, thinking, and speaking. When something goes wrong, the first diagnostic question is
always: which side of that line is it on?

## What Flux changes

This is the part worth slowing down for, because it's where voice agents differ most from what you'd expect.

In a traditional pipeline, your client decides when the user has stopped talking. You measure audio energy, you set a silence threshold, you write voice activity detection, and you get it slightly wrong forever. Turn-taking lives in your code.

Flux performs turn detection **inside the model**. It scores every turn for end-of-turn confidence as the audio streams in, and tells you what it concluded. You will not write a silence threshold anywhere in this course.

That removes a great deal of code and leaves you with exactly one obligation: when Flux says the user started talking, **stop your speaker immediately**. The agent stops sending audio the moment it knows, but whatever it already sent is sitting in your playback buffer, and it will keep talking over the user until you clear it.

That single responsibility gets its own module ([Module 5](../05-barge-in/LAB.md)), because it's the difference between a demo and something a person would willingly talk to.

## What you'll have built

By the end of Module 9, roughly 350 lines that:

- Open a WebSocket and negotiate an agent configuration
- Stream microphone audio from a browser without blocking the thread that plays the reply
- Play the agent's speech as it arrives
- Cut playback the instant you interrupt
- Verify a caller, check availability, and book an appointment exactly once
- Refuse to speak a value it was never handed
- Let you tune how patient the agent is, and measure what it costs

## How the course is laid out

Every module is a **complete, working program**. `steps/03-hear-the-agent/main.py` already does everything Modules 1 and 2 built. You open it, run it, and add the piece that module is about.

Work the `TODO (Step N.x)` blocks in `main.py`, in order. `LAB.md` explains why each one matters.

> The number in a marker is the module number, and so is the folder's: Module 8 lives in
> `steps/08-healthcare/` and carries `TODO (Step 8.x)`. Appendix A branches off Module 6, so its
> folder is `steps/06b-bring-your-own-llm/` and its markers are `TODO (Step 6b.x)`.

Inside a block, `#:` marks the instructions. Everything else is code, commented out at the indentation it belongs at. Select those lines and press `Cmd+/` (`Ctrl+/` on Windows and Linux) to uncomment them where they sit.

### When you get stuck, the next folder is the answer

This is the most useful rule in the course, so it gets its own heading.

**The next folder is the current module, finished.** Stuck halfway through Module 5? Open
`steps/06-make-it-yours/main.py`: that is Module 5 completed, and nothing beyond it. Compare it
to what you wrote, take what you need, and carry on.

You can also start anywhere. Each folder already contains everything the previous modules built,
so dropping in at Module 7 is a supported way to use this course, not a shortcut.

Each module ends with a **Checkpoint**: the observable thing that has to be true before you move
on, and what to look at when it isn't. Trust the checkpoint rather than your sense of whether it
felt right.

## The modules

| # | Module | Adds to the Northwind agent |
|---|---|---|
| 0 | Welcome, the loop, and the capstone | The mental model |
| 1 | [Set up and smoke-test](../01-setup/LAB.md) | A machine that can reach Deepgram and move audio |
| 2 | [Settings and the event lifecycle](../02-connect/LAB.md) | A configured agent, and the events it sends |
| 3 | [Hearing the agent](../03-hear-the-agent/LAB.md) | Its voice, out of your speaker |
| 4 | [The full loop](../04-talk-to-the-agent/LAB.md) | Your microphone, and a real conversation |
| 5 | [Interruption done right](../05-barge-in/LAB.md) | It stops the moment you speak |
| 6 | [Prompting for the ear](../06-make-it-yours/LAB.md) | The Northwind job, personality, and voice |
| 7 | [Function calling](../07-function-calling/LAB.md) | Checking availability and booking once |
| 8 | [Identity and the PII boundary](../08-healthcare/LAB.md) | Verification, vocabulary, and a human transfer |
| 9 | [Turn-taking and observability](../09-optimize/LAB.md) | Tuning, and knowing what it cost |
| 10 | [Reference agent and capstone](../10-final/README.md) | The submission |

Appendix A, [Bring your own LLM](../06b-bring-your-own-llm/LAB.md), is optional and sits off
Module 6. It moves the thinking to a model in your own AWS account.

## The badge

The badge is earned by shipping, not by watching. Two parts:

- **A knowledge check**: 30 questions drawn from the module quizzes, 80% to pass.
- **A practical**: you submit your Northwind agent with an evaluation scorecard and a short
  rationale, and it is scored against a published rubric. The brief and the rubric are in
  [Module 10](../10-final/README.md), and it is worth reading the rubric *now* rather than at the
  end, because every module contributes something the rubric asks for.

Each module has a five-question quiz. They exist to catch a misunderstanding while it's still
cheap, so answer them before moving on.

## Recap

- A voice agent is three models in a loop (STT, an LLM, and TTS) and **the LLM holds the conversation history**.
- The Voice Agent API runs all three behind one WebSocket and manages the seams. You configure it; you never rebuild it.
- Flux does turn detection **inside the model**, which deletes your voice activity detection and leaves you one job: clear your playback buffer when the caller interrupts.
- **The next folder is the answer key.** Every module is a complete program.
- You're building one agent for Northwind Clinic, and the capstone is that agent.

---

With the mental model in place, get your machine ready and confirm it can move audio.

**Next:** [Module 1: Set up and smoke-test](../01-setup/LAB.md)
