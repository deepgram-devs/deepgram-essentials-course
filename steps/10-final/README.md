# Module 10: The reference agent, the capstone, and what's next

**Goal:** Read the finished agent as one piece, then submit your own.

```bash
uv run steps/10-final/main.py
```

Everything the course builds, with nothing left to fill in. Roughly 350 lines of your own code on
top of the shared browser bridge: and it is the answer key for Module 9 as well as the reference
for your submission.

## What's in here

| Concern | Where it lives |
|---|---|
| Audio format contract | `SAMPLE_RATE`; the browser reads the rest back from `SETTINGS` |
| Turn detection | `EOT_THRESHOLD`, `EOT_TIMEOUT_MS`, wired into the listen provider |
| Domain vocabulary | `KEYTERMS`, passed to the listen provider |
| Agent definition | `SETTINGS`: listen, think, speak, greeting, `tags` |
| Clinic data | `PATIENTS`, `AVAILABILITY`, `BOOKED`, `PENDING` |
| Formatting for the ear | `spoken_date`, `spoken_time` |
| Read-only functions | `check_availability`, `find_appointment` |
| The two-phase write | `book_appointment` → `confirm_booking` |
| Escalation | `transfer_to_human` |
| The PII boundary | what `find_appointment` returns, and what it doesn't |
| Client-side plumbing | `FUNCTIONS`, `FUNCTION_HANDLERS`, `handle_function_call` |
| Inbound events | `on_message` |
| Barge-in | `player.clear()` in the `UserStartedSpeaking` branch |
| Observability | the `Welcome` branch, and the `LatencyReport` branch |
| Outbound audio | `on_media` |

Two things are worth re-reading with fresh eyes, because they are the ones that transfer to
whatever you build next.

**`find_appointment` returns three keys.** Not because the prompt asks it to, but so that the
values it omits cannot be spoken by a model that never received them.

**`book_appointment` writes nothing.** Only `confirm_booking` does, and it pops its token on the
way through. The prompt asks for a confirmation; the token is what guarantees one.

## The capstone

The badge has two parts, and both are described in [`course/capstone/`](../../course/capstone/):

- **[The brief](../../course/capstone/BRIEF.md)**: what to submit.
- **[The rubric](../../course/capstone/RUBRIC.md)**: how it is scored. Read this *before* you start, not after.
- **[The caller set](../../course/capstone/CALLERS.md)** and **[scorecard](../../course/capstone/SCORECARD.md)**: the evaluation you run and hand in.
- **The knowledge check**: 30 questions drawn from the module quizzes. Sat at submission, not
  published here.

You can submit this agent as-is and score poorly, because the rubric asks what *you* changed and
why. The work is the evaluation and the rationale, not the code you already have.

## Recap

- The whole agent is one settings object, one message handler, one media callback, and a handful of functions.
- **Read-only functions are safe to call; irreversible ones need a gate in code.**
- **The payload is the enforcement layer** for anything that must never be said.
- **Measure before you tune**, and keep the identifier that lets you find the call again.

## Where to go from here

**Telephony.** The browser is one channel. A phone line means mulaw at 8 kHz instead of linear16 at
24 kHz, a `SAMPLE_RATE` and encoding change plus a media bridge. Not built here; see
[`course/DEFERRED.md`](../../course/DEFERRED.md).

**Multilingual.** `flux-general-multi` detects the language instead of assuming English.

**Eager end-of-turn.** `eager_eot_threshold` starts the LLM on a *probable* turn end and discards
the work if the caller keeps talking. Lower latency, more model calls.

**Server-side functions.** Set `endpoint` on a declaration and Deepgram calls your HTTP service
instead of sending the request down the socket. Worth doing when the function needs credentials
your client shouldn't hold.

**Mid-conversation updates.** The API can change the prompt or inject a message mid-call, which is
how multi-phase agents hand off between modes. Also deferred: see `DEFERRED.md`.

**Your own vertical.** Swap `PATIENTS` and `AVAILABILITY` for your domain and keep the shape: read
functions, a gated write, a filtered payload, a named escalation.

## Reference

- [Voice Agent docs](https://developers.deepgram.com/docs/voice-agent)
- [Flux docs](https://developers.deepgram.com/docs/flux)
- [Voice catalogue](https://developers.deepgram.com/docs/tts-models)
- [Discord](https://discord.gg/xWRaCDBtW4) · [GitHub Discussions](https://github.com/orgs/deepgram/discussions)
