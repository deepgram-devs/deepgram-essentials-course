# Module 7: Function calling

**Goal:** Turn the agent into a specialist that answers from your data instead of from its imagination, and books an appointment exactly once.

**You'll learn**

- What makes a function client-side, and why that's a single omitted field
- Why the function description *is* a prompt
- How to gate an irreversible action behind a spoken confirmation
- The threading trap that turns a slow function into stuttering audio

## Start here

```bash
uv run steps/07-function-calling/main.py
```

You have a complete voice agent, and Module 6 made it honest: ask when your next appointment is and
it tells you it can't see your records. True, and no help at all. A caller does not want an
agent that is candid about being useless.

This module closes that gap. By the end you'll have an agent that reads real availability out of the
clinic's data, and books an appointment, once, and only after the caller has said yes to hearing
it back.

Northwind is a clinic rather than a shop for a reason: **it punishes vagueness.** A support bot that
paraphrases is annoying. An agent that paraphrases a date of birth, or books Thursday when the
caller said Friday, is a different category of problem. Every rule you write here transfers to
whatever domain you actually work in.

## How it works

Function calling connects the agent to things the model can't know: your database, your API, the current time, the caller's records. The flow has four hops.

1. You advertise a function in `SETTINGS`: name, description, and a JSON Schema for its parameters.
2. The LLM decides a user turn warrants calling it, and Deepgram sends you a `FunctionCallRequest`.
3. Your code runs the function and sends back a `FunctionCallResponse`.
4. The LLM works your result into its reply, and the agent speaks it.

The single most important detail: **leaving `endpoint` unset marks a function client-side.** That one omission makes Deepgram send the call down the socket to you, instead of calling an HTTP endpoint itself. Set `endpoint` and Deepgram handles the call server-side and you never see it. Both are valid; client-side is what you want when the function touches local state, local credentials, or anything you'd rather not expose over HTTP. It also means you need no public URL and no tunnel to finish this module.

The second most important detail: **the description is a prompt.** It's the only thing the LLM reads when deciding whether to call your function. Write it to say *when* to use the function, not just what it does. "Check the calendar" is worse than "List open appointment slots on a given date. Use this whenever the caller asks what is available, or wants to book or move an appointment."

### The two halves of a function

Every function you write lives in two places that never reference each other. The name string is the only thing joining them.

**The declaration** goes in `FUNCTIONS`, carrying a name, a description, and a JSON Schema for the arguments. This is what the LLM sees, and it's *all* the LLM sees. It never sees your implementation.

**The implementation** goes in `FUNCTION_HANDLERS`, registered under exactly that name. It receives whatever arguments the LLM chose and returns a value the agent will read aloud.

Keep that split in mind, because it explains the most common failure in this module: rename one and not the other, and you get an agent that decides to call something, waits, and then apologizes for a problem it can't describe.

### Two kinds of function, and only one of them is safe

You're writing three functions, and they are not equally dangerous.

| Function | Kind | If the model calls it wrongly |
|---|---|---|
| `check_availability` | **read-only** | The caller hears the wrong day and says so. Recoverable in one sentence. |
| `book_appointment` | **reserves, does not commit** | Nothing happens yet, by design. |
| `confirm_booking` | **writes** | A double booking, or a slot taken from someone else. Not recoverable by talking. |

A read-only function can be called speculatively and often. An irreversible one cannot, and the
uncomfortable part is that **the LLM decides when to call it.** You cannot rely on a prompt to
prevent a write, because a prompt is a request.

So the write is split in two. `book_appointment` validates everything, stashes the request under a
token, and returns a sentence for the agent to read back. Nothing is booked. Only
`confirm_booking`, with that token, actually writes, and it pops the token as it goes, so calling
it twice books once.

That is the pattern to carry with you: **an irreversible action gets a two-phase gate, in code, not
in prose.** The prompt asks nicely. The token is what makes it true.

### Guard it in prose first, anyway

The prompt you extend in this module gains a NUMERIC DISCIPLINE block, and one line in it does more work than the rest:

```
NEVER invent an appointment, a time, or a confirmation code.
```

That rule closes the fabrication gap before a single line of function-calling code exists: it's the
line you tested in Module 6. Write the guardrail in prose, then give it the function that makes
obeying the guardrail possible.

### Before you write any of it

Worth two minutes of thinking, not typing. Sketch one function for your *own* work: something your
agent would need to look up that a model cannot know. Then ask the harder question about it: is it
read-only, or does it change something? If it changes something, what does the read-back sound like,
and what is the token?

## Do this

**TODO 7.1: Uncomment the imports.** Four of them, each already written where it belongs: two at the top of the file, and two in the Deepgram imports below them.

**TODO 7.2: Uncomment the functions.** The `PATIENTS` and `AVAILABILITY` data, the `spoken_date()` and `spoken_time()` helpers, then the three handlers. Each piece has a note above it saying what it does.

Three habits to copy from these handlers, because they're what separates a handler that demos from one that ships.

**Format for the ear.** `spoken_date()` returns `"Thursday, October 8th"`, not `"2026-10-08"`. Hand the LLM a shape it can read aloud and you spend fewer prompt tokens on formatting rules, with fewer chances for it to say something strange. A date always carries its weekday: that's the caller's free second chance to catch a mistake.

**Return a graceful miss, don't raise.** An unrecognized caller returns `{"found": False, "message": "I could not find a patient with that date of birth and code."}`. The agent turns that into a sentence. An exception leaves the caller listening to silence, and it escapes into the SDK's receive loop and drops the call, exactly as you saw in Module 3.

**Make the write idempotent.** `confirm_booking` pops its token. The caller says "yes" twice, or the model calls it twice, and the appointment is still booked once. You get this for free from `dict.pop`, and it is the difference between a demo and something you'd put on a phone line.

**TODO 7.3: Advertise them.** Build the `FUNCTIONS` list. The `parameters` field is plain JSON Schema, exactly as the LLM's tool-calling API expects. Read `book_appointment`'s description twice: most of it is a *sequencing rule*, not a definition.

**TODO 7.4: Wire it into `SETTINGS`.** Five small edits: `keyterms`, temperature, the prompt, `functions=FUNCTIONS`, and the greeting.

The prompt edit is an **append**, not a replacement: Module 6's voice rules still hold, and you're adding NUMERIC DISCIPLINE and the function sequencing on the end.

`keyterms` biases Flux toward the words this domain repeats all day. It's the highest-leverage accuracy fix for a domain agent and it costs one line. Note that Flux has no `numerals` or `smart_format` parameter; those belong to the v1 Listen API. On Flux, spoken-number accuracy comes from `keyterms` plus the prompt rule that makes the agent read digits back before acting on them, which is a better habit anyway. Module 8 takes `keyterms` apart properly.

The greeting edit matters more than it looks: it names what the agent will ask for *before* the caller volunteers a full confirmation code, or a diagnosis, out loud. A greeting is the cheapest privacy control you have.

**TODO 7.5: Handle the call.** Uncomment `handle_function_call`. Three things in it are worth understanding, because they will bite you in your own code:

**`content` is a string.** Your handlers return dicts, so `json.dumps` the result on the way out.

**Catch exceptions and return the error text as `content`.** The agent is mid-turn and blocked waiting on your response. A raised exception escapes into the SDK's receive loop, surfaces as `EventType.ERROR`, and drops the call. Returning `"book_appointment failed: ..."` lets the LLM apologize gracefully and move on.

**This runs on the SDK's receive loop, the same thread delivering audio.** A slow function stalls playback for the whole conversation. Keep handlers fast, or hand the work to a thread and reply when it finishes. This is a real production failure mode, not a course artifact, and it's the reason a real scheduling lookup belongs behind a timeout.

Print both the call and the result. You want to see what the LLM actually passed you.

**TODO 7.6: Dispatch it.** Add the `FunctionCallRequest` branch.

Run it *before* you add this branch, once. You'll see `>> FunctionCallRequest` from the fallthrough and then nothing. The agent waits forever for a reply that never comes. Worth seeing on purpose, because it's what a broken handler looks like from the outside.

## Verify

Connect and work down this script out loud. It takes five turns, and the fifth one is the point of the module.

1. *"Hi, I'd like to book an appointment for October the eighth."*
2. *"My date of birth is April twelfth, nineteen seventy nine, and my code ends four eight two one."*
3. *"Nine o'clock with Doctor Nwosu, please."*
4. *"Yes, that's right."*
5. *"Yes, please book it."*

Here is a real run, trimmed to the interesting lines:

```
[user] My date of birth is April twelfth nineteen seventy nine, and my code ends four eight two one.
[assistant] Let me read that back to you.
[assistant] Your date of birth is April twelfth, nineteen seventy-nine, and the last four digits of
            your confirmation code are four, eight, two, one.
[assistant] Is that correct?

[user] Nine o'clock with Doctor. Nawazu, please.
>> Function call: check_availability({"date_wanted":"2026-10-08"})
>> Function result: {"found": true, "date": "Thursday, October 8th", "slots": [...]}
[assistant] I found an appointment available with Dr. Nwosu on Thursday, October eighth at nine
            o'clock in the morning.
[assistant] Would you like to book that?

[user] Yes. That's right.
>> Function call: book_appointment({"code_last_four":"4821","date_of_birth":"1979-04-12","slot_id":"S-1041"})
>> Function result: {"confirmed": false, "pending_token": "T-S-1041-4821", "read_back": "..."}
[assistant] I've reserved the appointment for you. It is Thursday, October eighth at nine o'clock
            in the morning with Dr. Nwosu.
[assistant] Please confirm if this is correct.

[user] Yes. Please book it.
>> Function call: confirm_booking({"pending_token":"T-S-1041-4821"})
>> Function result: {"booked": true, "slot_id": "S-1041", "read_back": "..."}
[assistant] Your appointment is successfully booked for Thursday, October eighth at nine o'clock
            in the morning with Dr. Nwosu.
```

Four things in that transcript are worth stopping on.

**It read the code back one digit at a time**: "four, eight, two, one." That's the prompt, not the code.

**It turned "October the eighth" into `2026-10-08`** without being told the year. Models are good at this and you should still validate it, because they are not *reliably* good at it.

**`book_appointment` returned `"confirmed": false`.** The agent then asked again. Nothing was written. This is the gate working, and it is the single most important line in the transcript.

**Flux heard "Doctor Nawazu."** `Dr. Nwosu` is in `keyterms` and it *still* came through wrong. Keyterms bias recognition; they don't guarantee it. The agent recovered because the name was in the availability data it had just read: which is a good argument for letting your data, not the transcript, be the source of truth for proper nouns. Module 8 is where you measure what keyterms are actually worth.

Then ask it something that shouldn't trigger a call (*"what's the weather like?"*) and confirm no function fires. An agent that calls functions it doesn't need is as broken as one that never calls them.

### Test data

| Say | Result |
|---|---|
| date of birth `April 12 1979` + code ending `4821` | Dana, A1C follow-up with Dr. Nwosu |
| date of birth `November 20 1965` + code ending `9007` | James, echocardiogram with Dr. Bergstrom |
| any other pair | the graceful not-found path |
| `October 8th` | three open slots |
| `October 9th` | two open slots |
| any other date | nothing open, spoken gracefully |

## Checkpoint

Four things, and the fourth is the one that matters:

1. **`check_availability` fires** when you ask about a date, and the agent reads back real times with weekdays.
2. **The agent reads your digits back** before acting on them.
3. **A bad date of birth produces a spoken apology**, not silence and not a dropped call.
4. **Nothing is booked until you say yes twice.** After turn 4 the console shows `"confirmed": false`. Only after turn 5 do you see `confirm_booking` and `"booked": true`.

Test the gate deliberately: get to the read-back, then say *"no, make it eleven thirty instead."* No booking should exist. If an appointment got made before you agreed to it, the two-phase gate isn't wired up: and that is exactly the bug that matters most in this module.

## Stuck?

**The function never gets called.** Nine times out of ten it's the description. Make it explicit about *when* to use the function. Confirm `functions=FUNCTIONS` actually reached `ThinkSettingsV1`.

**The agent apologizes vaguely and the console shows the call.** The name in `FUNCTIONS` doesn't match the key in `FUNCTION_HANDLERS`. The two halves only meet through that string.

**`>> FunctionCallRequest` prints and the agent goes silent.** TODO 7.6 isn't done, or your handler raised before sending a response. The agent is still waiting.

**`TypeError: got an unexpected keyword argument`.** The LLM passed a parameter your Python doesn't accept. Your schema and your signature have drifted apart.

**It books without waiting for confirmation.** Check that `book_appointment` really returns without writing, and that `confirm_booking` is the only thing that touches `BOOKED`. If both are right, strengthen the sequencing sentence in `book_appointment`'s *description*: that's where the model reads the ordering rule.

**It calls `confirm_booking` with a token it invented.** Your `confirm_booking` should refuse an unknown token and say so. If it does, this is working as designed: the caller hears an apology instead of getting a booking they never agreed to.

**The agent interrogates the caller for things it could infer.** Too many properties marked `required`. Require only what you can't proceed without.

**Audio stutters when a function runs.** The threading trap. Your handler is too slow for the receive loop.

**Agent gets the answer but says something different.** The LLM paraphrases your result. Return clear, pre-formatted values and it stays close to them: which is what `spoken_date` and `spoken_time` are for.

**"Nothing open" on a date that should have slots.** Check the year in `date_wanted` on the `>> Function call:` line. The model has no calendar and fills in the year itself, which is why the prompt tells it today's date, from `todays_date()`. If you changed the prompt, keep that line.

**The date of birth or the code comes through wrong.** Check `keyterms` reached the listen provider, and confirm the prompt still tells the agent to read digits back. That read-back is your last line of defence against a misheard four.

`steps/08-healthcare/main.py` is this module, finished.

## Recap

- **Omitting `endpoint` is what makes a function client-side.** One absent field decides whether Deepgram calls your code or an HTTP URL.
- **The description is a prompt.** It's all the LLM sees when deciding to call, so it should say *when*, not just what.
- **A function lives in two places joined only by its name**: the declaration the model reads, and the handler that runs.
- **Format for the ear in the handler.** Return "Thursday, October 8th", never "2026-10-08".
- **Return graceful misses; never raise.** An exception escapes the receive loop and drops the call.
- **Irreversible actions need a two-phase gate in code.** The prompt asks; the token guarantees. And popping the token makes a repeat call harmless.

## The recipe for any function

The clinic is scaffolding. This is the part that transfers:

1. **Name it after the action.** `check_availability` beats `get_data`. The name steers the model nearly as much as the description does.
2. **Declare it** with no `endpoint`, so your code runs it.
3. **Describe when to call it**, not just what it does, and for anything irreversible, describe what must happen first.
4. **Implement it** under exactly that name. Validate inputs, return graceful misses instead of throwing, and return only what the agent may say out loud.
5. **Split anything irreversible** into a reserve step that returns a read-back and a token, and a commit step that consumes the token.
6. **Reference the sequence in the prompt** as well as the description. Belt and braces: the model should hear the ordering from both directions.

Then test by voice, including the paths where it fails.

## Going further

**Break the gate on purpose.** Ask to book, and when the agent reads the appointment back, change your mind: *"actually, make it Friday."* Then check `BOOKED`. Then try the rude version: interrupt the read-back with *"yes yes yes book it."* You are looking for the case where the agent commits something the caller never actually heard.

**Make the token expire.** Right now a `pending_token` lives until the process dies. Give it a timestamp and refuse it after sixty seconds. A caller who goes quiet mid-booking and comes back five minutes later should not find a live reservation waiting.

**Move `BOOKED` out of memory.** It's a module-level dict, which means two callers on two connections share nothing and a restart forgets everything. That's fine for a lab and wrong for a phone line. Writing it to SQLite is twenty lines, and it makes the idempotency question real: what happens if `confirm_booking` runs twice on two different processes?

**Add `reschedule_appointment`.** It's a read, a write, and a delete in one action, and it needs the same two-phase treatment. Decide what the read-back has to say for a caller to genuinely understand what they're agreeing to, "moving your Thursday appointment to Friday at one o'clock" tells them more than "confirmed."

---

Your agent answers from real data and books safely. What it does not yet do is refuse to say things
it should never say out loud: and in a clinic, that is the requirement with teeth.

**Next:** [Module 8: Identity, vocabulary, and the PII boundary](../08-healthcare/LAB.md)
