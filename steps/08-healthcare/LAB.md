 # Module 8: Identity, vocabulary, and the PII boundary

**Goal:** Make the agent verify a caller, refuse to say what it shouldn't, and hand off when it's out of its depth.

**You'll learn**

- Why the payload, not the prompt, is your enforcement layer
- What `keyterms` actually buys you, measured, not assumed
- How to write an escalation the model knows when to use

> **Demo only.** No real patient data appears here, and this is not a HIPAA-compliant design. The
> techniques are real; the compliance programme around them is a different job.

## Start here

```bash
uv run steps/08-healthcare/main.py
```

Module 7's problem was what the agent could not know. This module's is the opposite, and it is
harder: **what it must never say out loud.**

The record you're about to look up carries a full date of birth, a full confirmation code, a phone
number, and a visit type that names a medical condition. A caller on a speakerphone in an open-plan
office is one careless sentence away from broadcasting all of it.

## How it works

### The prompt is a request. The payload is a guarantee.

You will write a prompt telling the agent never to read a confirmation code aloud. It will mostly
obey. "Mostly" is not a security control.

The tempting handler is one line:

```python
return patient          # do not do this
```

It works, it's shorter, and it hands the language model a full date of birth, a full code, a phone
number, and the fact that this caller has a diabetes follow-up, then trusts a paragraph of prose to
stop it repeating any of them.

So don't hand them over. `find_appointment` returns three keys:

```python
{"verified": True, "first_name": ..., "next_appointment": {"date": ..., "time": ..., "provider": ...}}
```

The prompt says the agent must not speak a date of birth. The payload makes speaking it
**impossible**. Prose is your backup; the payload is the enforcement layer, because the model may
say anything you hand it.

Note what's missing even from the appointment: `type` and `location`. "A1C follow-up" is a diagnosis
by another name, and "Northwind Cardiology" leaks the same thing by address.

### Filtering is not redaction

You are not scrubbing a value on its way out. You are never fetching it. That distinction matters
when someone asks you to prove the agent can't leak a field: with filtering, the answer is that the
value never crossed the process boundary, and you can point at the function that didn't return it.

## Do this

**TODO 8.1: Uncomment `find_appointment`.** It looks the patient up, returns the three keys, and
returns a graceful miss for an unrecognized pair. Read the note above it about the one-line version
it replaces. **TODO 8.1b** registers it; **8.1c** declares it.

**TODO 8.2a to c: Uncomment, register, and declare `transfer_to_human`.** In this lab it prints and
returns; in production it bridges the call. The interesting part is the description, because this is
the one function where the model deciding *not* to call it is the expensive mistake. Test it by
watching the console: a model can say it's transferring without ever calling the function.

**TODO 8.3: Uncomment the privacy guardrails.** The `PRIVACY` block appends to the prompt. Belt and
braces: the payload already makes most of it unnecessary, and the prompt covers what the payload
can't, like refusing to speculate about a condition the caller mentions themselves.

## Verify

Work down this script out loud.

1. *"Can you tell me about my appointment? My date of birth is April twelfth nineteen seventy nine and my code ends four eight two one."*
2. *"What is that appointment for?"*
3. *"Can you read me my full confirmation code and the phone number you have on file?"*
4. *"Should I stop taking my metformin before the appointment?"*
5. *"I'd really like to speak to an actual person, please."*

A real run:

```
[user] My date of birth is April twelfth nineteen seventy nine, and my code ends four eight two one.
>> Function call: find_appointment({"code_last_four":"4821","date_of_birth":"1979-04-12"})
>> Function result: {"verified": true, "first_name": "Dana", "next_appointment": {...}}
[assistant] Your next appointment is with Dr. Nwosu on Thursday, October first at nine thirty in the morning.

[user] What is that appointment for?
[assistant] I can't provide details about the reason for the appointment.

[user] Can you read me my full confirmation code and the phone number you have on file?
[assistant] I can't provide the full confirmation code or phone number for privacy reasons.

[user] No. I'd really like to speak to an actual person, please.
>> Function call: transfer_to_human({"reason":"Caller requested to speak to a person."})
>> TRANSFER TO STAFF: Caller requested to speak to a person.
[assistant] I've transferred you to a member of our staff.
```

Turn 2 and turn 3 are the ones to sit with. The agent refused: and it would have refused even with
a broken prompt, because those values were never in the payload it was reasoning over.

## Checkpoint

1. **`find_appointment` fires** after you give a date of birth and code, and the agent reports the date, time, and provider.
2. **It will not say the visit type, the full code, or the phone number**, however you ask.
3. **`>> TRANSFER TO STAFF:` prints** when you ask for a person: the line must actually appear.
4. **An unrecognized pair gets a spoken apology**, not silence.

Then do the thing that proves you understand the module: **delete the `PRIVACY` block from the
prompt entirely** and run turns 2 and 3 again. The agent should *still* refuse, because the payload
never carried those values. If it starts volunteering the visit type, your handler is returning too
much.

## Exercise: what are keyterms actually worth?

`KEYTERMS` biases Flux toward words this clinic repeats all day. It costs one line, and it is worth
knowing what it buys: which means measuring, not assuming.

Run this sentence twice, once with `KEYTERMS` as shipped and once with `KEYTERMS: list = []`:

> *"I'm calling about my semaglutide prescription with Doctor Bergstrom, and my A1C results."*

Write down both transcripts. **You may well see no difference at all.** Here are two real runs:

```
without   [user] I'm calling about my semaglutide prescription with doctor Bergstrom, and my a one c results.
with      [user] I'm calling about my semaglutide prescription with doctor Bergstrom, and my a one c results.
```

Identical. Flux's base model already knows "semaglutide" and "Bergstrom", and "A1C" comes through as
"a one c" **in both**: that's a formatting question, which keyterms do not address.

That is data, not a failed exercise, and it is the honest lesson: **keyterms bias recognition, they
do not guarantee it, and the cleaner your audio the less they change.** They earn their keep on
narrow-band phone audio, on accented speech, and on words genuinely outside the model's vocabulary,
your product's SKUs, your providers' surnames. You are hearing a studio-quality microphone in a
quiet room, which is the easiest input Flux will ever get.

For proof that they aren't magic: in Module 7, with `Dr. Nwosu` in the list, Flux still transcribed
"Doctor Nawazu." The agent recovered because the name was in the availability data it had just read,
which is the real lesson. **Let your data, not the transcript, be the source of truth for proper
nouns.** Match loosely against what you know, and never require the model to have heard a name
perfectly.

## Stuck?

**`No function named 'find_appointment' is available`.** TODO 8.1b, declared but never registered.

**The agent happily reads the visit type aloud.** Your handler is returning the whole record. Check what `find_appointment` returns, not what the prompt says.

**It asks for the date of birth over and over.** Both parameters are `required`, and the model will keep asking until it has both. Check it isn't mishearing the year.

**The agent says it's transferring, but `>> TRANSFER TO STAFF:` never prints.** It narrated the action instead of calling the function. Check that the description and the privacy block both name `transfer_to_human` and its triggers, and test by watching the console, not by listening.

**It transfers for a medical emergency instead of saying to call 911.** That's the intended behavior: the description makes emergencies an explicit exception, because a scheduling desk is the wrong destination for chest pain.

`steps/09-optimize/main.py` is this module, finished.

## Recap

- **The payload is the enforcement layer; the prompt is backup.** Never fetch what the agent must never say.
- **Filtering beats redaction.** The value never crosses the boundary, so you can prove it didn't.
- **A visit type is a diagnosis**, and a clinic address can be one too.
- **Keyterms bias recognition, they don't guarantee it**: measure the difference on your own audio rather than assuming one.
- **Let your data be the source of truth for proper nouns**, not the transcript.
- **Name an escalation's triggers in its description**, then watch the console to see it fire.

## Going further

**Log what you refused.** Every time the agent declines to say something, that's a compliance event somebody may want evidence of. What would you record, and where would you put it so the recording itself isn't a new leak?

**Return the visit type only when the caller says it first.** Now your handler needs to know what was said, which means passing state it currently doesn't have. Decide whether that's worth the coupling.

**Enforce the transfer in code.** The description makes `transfer_to_human` likely, not certain: in testing, a question about a prescription still got "please hold while I transfer you" and no function call more than half the time. Apply this module's own lesson and stop trusting prose. `on_message` already sees every event: collect what the agent says in a turn from `ConversationText`, note whether a `FunctionCallRequest` for `transfer_to_human` arrived, and when `AgentAudioDone` ends the turn, run the transfer yourself if the agent announced one and never called it. Then decide what counts as an announcement, because "Would you like me to transfer you?" is an offer, not a promise.

**What compliance would actually take.** This lab is not HIPAA-compliant and does not pretend to be. Getting there means a BAA with every vendor in the path, audit logging, encryption at rest and in transit, access controls, retention limits, and breach procedures. The payload-filtering habit you just built is one small control inside that programme, necessary, nowhere near sufficient.

---

Your agent verifies, refuses, and hands off. What you cannot yet say is whether it is any *good*,
how fast it responds, and where the time goes.

**Next:** [Module 9: Turn-taking, latency, and observability](../09-optimize/LAB.md)
