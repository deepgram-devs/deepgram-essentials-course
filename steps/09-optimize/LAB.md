# Module 9: Turn-taking, latency, and observability

**Goal:** Make the agent you just built feel fast, and know what it cost you.

**You'll learn**

- How to read `LatencyReport` and which number actually matters
- What `eot_threshold` and `eot_timeout_ms` trade against each other
- Why `eager_eot_threshold` buys latency with LLM calls

## Start here

```bash
uv run steps/09-optimize/main.py
```

Your agent is finished. It listens, thinks, speaks, yields the floor when you interrupt, and calls your Python when it needs something it can't know. Everything from here is how it *feels*.

This step is dials rather than code, and it's the step that decides whether people enjoy talking to what you built.

## How it works

Two constants have been sitting in every `main.py` since Module 2:

```python
EOT_THRESHOLD = 0.7
EOT_TIMEOUT_MS = 5000
```

They're the reason turn-taking has felt reasonable all course. Reasonable is not the same as right for what *you're* building, and this is where you find out what they've been doing.

Turn detection is the hardest problem in voice, and it's an unwinnable trade. End the turn too early and you cut people off mid-thought. End it too late and every exchange has a dead pause in it. No setting avoids both. The only question is which one fits your use case.

Flux scores every turn for end-of-turn confidence as the audio streams in. Both constants act on that score:

**`eot_threshold`** (0.5 to 1.0) is how much confidence Flux needs before calling the turn over. Raise it and the agent stops interrupting people who pause to think. Lower it and replies come faster, at the cost of the agent jumping in during those pauses.

**`eot_timeout_ms`** (500 to 60000) is the hard ceiling. End the turn after this much silence regardless of what the score says. It catches the case where someone trails off without a clean ending.

Both are optional. Omit them and you get Deepgram's server defaults, which is fine right up to the first time someone tells you the agent talks over them.

### The report is a stream, not an event

`LatencyReport` does not arrive once per turn. In testing, a single exchange produced **36** of
them, and exactly one carried `total_latency`. The rest were empty, or held only a deprecated
`stt_latency` of `0.0`.

That is why the `None` check in the TODO is not decoration. It is the thing that turns 36 messages
into the one line you want:

```
fields ever populated:
   stt_latency              n= 32  max=0.000      <- deprecated, ignore
   total_latency            n=  1  max=0.899
   ttt_text_latency         n=  1  max=0.762
   ttt_token_latency        n=  1  max=0.761
   tts_latency              n=  1  max=0.111
fields never populated: ttt_thinking_latency, ttt_tool_latency
```

Read that table as a warning about your future dashboard: **every field is optional, and absent is
not zero.** That exchange called no function, so `ttt_tool_latency` never arrived. On a turn that
does call one, it does. `ttt_thinking_latency` never appeared in any of our testing. Build something
that assumes `ttt_tool_latency` is always present and it will break on the first turn without a
function call.

### Finding one call again

Numbers are only useful if you can attach them to a specific conversation. Two things do that.

**`request_id`** arrives on the very first frame, `Welcome`, as a UUID like
`01a0c486-ee78-78a0-a47d-063270953fbd`. It is how you find this exact call later, in your logs,
and when you ask Deepgram about it. A latency complaint you cannot tie to a request is a complaint
you cannot investigate.

**`tags`** is a list of strings you put on `Settings`, and they travel with the session. Tag by
deployment, by environment, by experiment: anything you'll later want to filter on.

## Do this

Optimization goes in one order: measure, change one thing, measure again. The TODOs follow it.

**TODO 9.1: Turn on the latency report.** Uncomment the three lines in the `LatencyReport` branch, and delete the `pass` below them.

`total_latency` measures end-of-utterance to first audio byte. It's the exact number your threshold changes move, and the only honest way to tell whether a change helped. Everything else is impression.

The report also carries `ttt_token_latency`, `ttt_text_latency`, `ttt_tool_latency`, `ttt_thinking_latency`, and `tts_latency`. Every field is optional: **absent, not zero**, when it doesn't apply. That's why the `None` check isn't decoration.

**TODO 9.2: Move the dials.** Change `EOT_THRESHOLD` and `EOT_TIMEOUT_MS`, one at a time, and listen.

**TODO 9.3: Capture the identifier.** Uncomment the `Welcome` branch that logs `request_id` (9.3a), and the `tags` line at the top of `SETTINGS` (9.3b).

Values outside the valid ranges fail the handshake. Settings are never applied, and the `Error` branch you wrote in Module 2 prints `INVALID_SETTINGS` with the range the value had to fall in. Try `EOT_THRESHOLD = 0.3` once to see it, then put it back.

## Exercise: find your setting

Run the agent four times and hold the same short conversation each time. Write down what you notice.

Use this script. The `…` marks are deliberate pauses of a second or two, and they're the whole
point: read smoothly, and all four settings sound alike. Pausing mid-sentence is what separates them.

1. "I need to move my appointment… to… um… October the eighth."
2. "My date of birth is April twelfth, nineteen seventy-nine… and my code ends in… four eight two one."
3. "I think the… eleven thirty works."
4. "Yes, go ahead and confirm it."

Line 1 is the real test: a sentence that stops on "to" is plainly unfinished, so it shows you
whether a setting waits for you or jumps in. When comparing `>> Latency:` across runs, use a turn that follows a
`>> Function call:` line. Those turns cost more, so compare like with like.

| `EOT_THRESHOLD` | `EOT_TIMEOUT_MS` | What to listen for |
|---|---|---|
| `0.5` | `5000` | Snappy, and it interrupts you when you pause |
| `0.9` | `5000` | Patient to the point of feeling slow |
| `0.7` | `500` | Cuts you off on any real pause |
| `0.7` | `5000` | Where you started, the balance you've been using all course |

Watch `>> Latency:` alongside. The number moves, and it moves in the direction the setting predicts.

No correct answer exists here. It depends entirely on what you're building. A drive-through order taker wants low thresholds and fast turns. A therapy intake bot wants high thresholds and long silences. Pick the one that matches the agent you actually want.

## Verify

The agent asks for your date of birth and code before it checks availability, so give them first.
Trimmed to the lines that matter:

```
>> request_id: 01a14534-e3f2-7a20-88ca-e95564f24794
>> Settings applied
[assistant] Thank you for calling Northwind Clinic. To look up an appointment I'll need your date
            of birth and the last four digits of your confirmation code. How can I help?
[user] My date of birth is April twelfth nineteen seventy nine, and my code ends four eight two one.
[assistant] Let me read that back to you.
>> Latency: 0.54s
[user] what is open on October the eighth
>> Function call: check_availability({"date_wanted":"2026-10-08"})
>> Function result: {"found": true, "date": "Thursday, October 8th", "slots": [...]}
>> FunctionCallResponse
[assistant] On Thursday, October 8th, we have openings at nine o'clock in the morning, eleven
            thirty in the morning, and three fifteen in the afternoon...
>> Latency: 1.58s
```

One `>> Latency:` line per turn, even though dozens of reports arrived: that's the `None` check
doing its job. The turn with a function call costs more, and it's the one where
`ttt_tool_latency` shows up. And the two extreme settings in the table sound obviously different
from each other.

Your absolute numbers will differ from these; what matters is the *direction* they move when you
change a dial, measured against your own baseline rather than against this page.

## Checkpoint

1. **`>> request_id:` prints** on connect, and you could paste that string into a support request.
2. **Exactly one `>> Latency:` line per turn**, not dozens. If you're getting a flood, the `None` check is missing.
3. **You have run all four rows** of the table and written the numbers down, not just listened.
4. **The 0.5 and 0.9 rows sound clearly different**, and the number moved in the direction the setting predicts.

The fourth one is the real gate. If changing a threshold produced no audible difference *and* no
change in the latency figure, check that you restarted `main.py` after the edit. A value outside
its valid range doesn't quietly do nothing: it fails the handshake with `INVALID_SETTINGS`, and the
agent never connects.

## Stuck?

**No `>> Latency:` line.** Either the lines are still commented out, or `total_latency` is absent on your turns. Print `message` directly in that branch to see what actually arrived.

**Changing the values does nothing.** Restart `main.py` after every edit: the values are read once, when it starts. An out-of-range value isn't the cause, because that fails the handshake outright.

**The agent never connects after you change a dial.** Look for `>> Agent error: INVALID_SETTINGS` in the console. The description names the setting and its valid range.

**Latency is high across the board.** `total_latency` includes the LLM. `gpt-4o-mini` is the fast option; if you switched to `gpt-5.5` back in Module 6, this is the bill for it. Switch back and watch the number drop.

**Function calls make a turn slow.** Also in the number. Your handlers run on the receive loop, as Module 7 warned. `ttt_tool_latency` arrives on a turn that calls a function and isolates that part of the cost; time your handler directly too, so you know how much of it is your own code.

`steps/10-final/main.py` is this module, finished.

## Recap

- **Measure, change one thing, measure again.** Everything else is impression.
- **`total_latency` is end-of-utterance to first audio byte**: the number the dials actually move.
- **`LatencyReport` is a stream, not an event.** Dozens arrive per turn and most are empty; the `None` check is what makes them useful.
- **Every field is optional, and absent is not zero.** `ttt_tool_latency` appears only on turns that call a function, and `ttt_thinking_latency` never appeared in our testing.
- **`eot_threshold` and `eot_timeout_ms` trade against each other**, and no setting avoids both failure modes. Pick the one that fits the agent you're building.
- **An out-of-range value fails the handshake**, and the `Error` branch tells you the range it wanted.
- **`request_id` and `tags` are how you find one call again.** A complaint you can't tie to a request is a complaint you can't investigate.

## Going further

Add `eager_eot_threshold=0.5` to the listen provider. Flux starts the LLM on a *probable* turn end and discards the work if you keep talking. Latency drops noticeably; your LLM call volume goes up, because Flux throws some of those calls away. Keep it less than or equal to `eot_threshold`.

That trade (spend compute to buy responsiveness) is one of the more interesting levers in production voice, and worth knowing before you need it.

---

You've built a complete voice agent and tuned it to feel the way you want: it listens on Flux, thinks with an LLM, speaks with Flux TTS, yields the floor when interrupted, calls your code when it needs something it can't know, and takes its turns on your terms.

**Next:** [Where to go from here](../10-final/README.md)
