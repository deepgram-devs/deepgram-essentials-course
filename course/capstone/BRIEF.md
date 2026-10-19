# Capstone brief

Submit a working Northwind Clinic agent, an evaluation, and a page explaining your choices.

Scored against [the rubric](RUBRIC.md): **read it before you start.** Every module contributes
something it asks for.

## What to submit

**1. The agent.** A repo or archive containing your `main.py` and anything it needs. It must run
with `uv run`, in the browser, against a Deepgram API key the reviewer supplies. Do not include
your key.

It must have, at minimum:

- A `Settings` message with `eot_threshold` and `eot_timeout_ms` set deliberately
- A prompt written for the ear, with at least one named escalation trigger
- **At least two functions: one read-only, and one that changes state behind a spoken confirmation**
- Clean barge-in
- `request_id` captured, `tags` set, and `total_latency` reported per turn

**2. The scorecard.** [SCORECARD.md](SCORECARD.md), filled in: the [eight callers](CALLERS.md) run
twice, against a baseline and a tuned configuration, with one change between them.

**3. The rationale.** One page. What you tuned, what the numbers showed, what regressed, and what
you would watch in production.

## What "changes state behind a spoken confirmation" means

The reference agent splits booking into `book_appointment`, which reserves and returns a read-back,
and `confirm_booking`, which commits and consumes its token. You do not have to copy that shape,
but whatever you build has to survive caller 5, who changes their mind at the read-back. If an
appointment exists afterwards, the criterion fails regardless of how the rest reads.

## Scope

The channel is **the browser**. The functions run **client-side**, in your own process. That is what
this course builds and what the rubric scores. Capabilities outside that scope are listed in
[`course/DEFERRED.md`](../DEFERRED.md) and are not assessed: do not add them expecting credit.

You may submit the reference agent from `steps/10-final/` essentially unchanged and still pass, or
still fail. The code is the smaller half. The rubric asks what *you* changed, what you measured, and
what you learned when something got worse.

## The knowledge check

Thirty questions, drawn from the module quizzes and rewritten. **80% to pass.** Sit it after the
practical, not before: several questions assume you have run the caller set.

## How it is reviewed

A Deepgram engineer scores the six criteria, 1 to 4 each. **Pass at 18 of 24, with nothing below 2.**
You get written feedback either way. If you miss, you may resubmit once; a second attempt uses a
different scenario.

## A note on honesty

The fastest way to fail criterion 6 is a scorecard where everything passed and nothing regressed.
Tuning a voice agent trades one failure mode for another. A submission that names its regression and
argues the trade is stronger than one that claims there wasn't one.
