# Module 4: The full loop and turn-taking

**Goal:** Stream microphone audio to the agent and hold a conversation.

**You'll learn**

- How Flux decides where your turns begin and end without any client-side help
- Why 80 ms is the chunk size, and what moving it costs in both directions
- Why sending audio gets its own thread, and what freezes when it doesn't

## Start here

```bash
uv run steps/04-talk-to-the-agent/main.py
```

Press **Connect**. The greeting plays, the level meter moves when you talk (the microphone really is open), and then, about fifteen seconds later, the agent hangs up. It is waiting to hear from you and nothing is sending it anything.

This is the module where it becomes a voice agent.

## How it works

The microphone lives in the browser and has been open since you pressed Connect. It just has no instruction to do anything with what it captures.

That instruction is `on_media`, and it is one line:

```python
def on_media(agent, audio):
    agent.send_media(audio)
```

Here is the part that surprises people coming from traditional speech pipelines: this file contains no voice activity detection at all. No silence trimming, no energy threshold, no "has the user stopped talking" logic. Flux performs turn detection **inside the model**, server-side. Your entire job on the outbound side is keeping the pipe full and letting Flux decide the rest.

Two things happen before the audio reaches you, both in `CaptureProcessor` in [`web/static/worklets.js`](../../web/static/worklets.js), and both are work you would otherwise do yourself:

**Chunking.** Audio hardware delivers 128 frames at a time, about 5 ms. Flux wants 80 ms, which is 1920 frames at 24 kHz, exactly fifteen of those blocks. The worklet accumulates and ships a chunk when it is full.

**Resampling.** Most microphones run at 48 kHz. `SETTINGS` asked for 24 kHz. The page creates its `AudioContext` at 24 kHz so the browser's own resampler handles it, and carries a fallback for the browsers that ignore the request, which is why `CaptureProcessor` has a `ratio` at all.

### How Flux decides your turn is over

You configure this in Module 9 and never implement it, but the mental model matters now, because
everything the agent does is downstream of it.

Traditional streaming recognition ends a turn on silence: wait *N* milliseconds of quiet, declare
the caller finished. Set *N* short and you cut off anyone who pauses to think, "I'd like to book
for… Thursday" becomes two turns, and the agent answers the first half. Set *N* long and every
turn ends with a dead second that makes the whole thing feel robotic.

Flux decides from the speech itself. As audio streams in it continuously scores **end-of-turn
confidence**, a number between 0 and 1 for "has this person finished?", using the words, the
intonation, and the pace. Turn detection becomes a threshold on a probability instead of a
stopwatch. So:

- "I'd like to book for… Thursday, actually no, Friday" stays **one turn**, and the agent books Friday.
- A caller who trails off mid-sentence still gets their turn closed, by a timeout that acts as the safety net.

Two consequences you can see today. `UserStartedSpeaking` is Flux telling you a turn *began*,
that is your barge-in signal, and it is Module 5. And the transcript you get in
`ConversationText` is the **confirmed** turn: once it arrives, it will not change.

Module 9 is where you tune the thresholds that decide how patient this is.

## Do this

**TODO 4.1: Write `on_media`.** One call: `agent.send_media(audio)`.

That call returns immediately, and it is worth knowing why. The `agent` handed to `on_media` is not the SDK connection itself. It is an `AgentHandle` ([`web/session.py`](../../web/session.py)), a wrapper that drops the chunk on a queue for a dedicated sender thread to write, so `send_media` never waits on the socket.

That thread matters most when the connection closes. The underlying `websockets` library joins its receive thread as a close begins, waiting up to ten seconds by default for that thread to finish. A send issued during that window inherits the wait, so the moment Deepgram hangs up, the *next* `send_media` can sit for ten seconds before it returns. On a realtime audio thread, that is ten seconds of dropped frames. On the web server's event loop, it would freeze everything: the playback pump, the page, the lot. Giving the sends their own thread puts that stall somewhere it costs you nothing.

**TODO 4.2: Pass it to the bridge.** Add `on_media=on_media` to the `bridge.run(...)` call.

Passing it tells the page to start capturing, and *when* it starts matters: only after `SettingsApplied` arrives. The agent discards media received before the handshake completes, so starting any earlier throws away your first words. The bridge enforces that, which is why the page waits for a `ready` message instead of sending audio as soon as the socket opens.

## Verify

Run it and talk. You should hear the greeting, ask a question, and get a spoken answer:

```
>> Settings applied

[assistant] Thank you for calling Northwind Clinic. I can help you check, book, or move an appointment. How can I help?
>> Agent finished speaking
>> UserStartedSpeaking
[user] Hi. I need to move my appointment to next week.
[assistant] I can help with that.
[assistant] Can you please provide me with your current appointment date and time?
>> Agent finished speaking
```

Your wording will differ: that is a language model, not a script. One detail surprises people:
the agent's reply can arrive as **more than one** `ConversationText`, since it is streamed as it
is generated. Don't assume one reply is one message.

And as in Module 3, neither `>> Agent thinking...` nor `>> Agent started speaking` appears. Those
branches are waiting for events this configuration does not send.

The agent will also cheerfully invent things at this stage: it has no appointment data and no
instructions about honesty. That is not a bug to fix here. Module 6 gives it rules and Module 7
gives it real data.

The transcript builds up on the page too. Ctrl+C in the terminal exits cleanly.

Two things to notice. First, `>> UserStartedSpeaking` appears with no branch handling it. That's the Module 2 fallthrough earning its place, and it becomes the whole point of Module 5. Second, the `CLIENT_MESSAGE_TIMEOUT` from earlier modules is gone. Once you're streaming audio continuously, the agent has no reason to hang up.

## Checkpoint

**You have held a real, spoken, two-way conversation with the agent.** You asked something out
loud and heard an answer. That is the milestone this whole course is built on, so it is worth
spending a few minutes here rather than moving straight on, ask it something silly, interrupt it,
ask it about an appointment it cannot possibly know about.

Two specific things should be true:

1. **`>> UserStartedSpeaking` appears** when you begin talking, with no branch in your code handling it.
2. **`CLIENT_MESSAGE_TIMEOUT` is gone.** A continuously streamed microphone gives the agent no reason to hang up. If you still see it, `on_media` was defined but never passed.

While you are here, try talking over the agent mid-sentence. It stops, but about a second late.
Deepgram stopped sending as soon as Flux heard you, and what you hear is the audio already queued
in your browser, still playing. Nothing you have written is wrong: throwing that queued audio away
is the next module, and hearing the problem first is how it is meant to land.

## Stuck?

**The agent never responds to you.** Does the level meter move when you talk? If it does not, the microphone is muted or the browser picked the wrong input. If it does, check that you passed `on_media=on_media` and not just defined the function.

**"connected, not sending audio" stays on the page.** TODO 4.2 is not done. That message is the bridge telling you `on_media` was never passed.

**The agent hears itself and answers its own questions.** Your speaker is feeding your microphone. The browser's echo cancellation handles most of this, but not all of it on every browser. Use headphones. This gets much more noticeable in Module 5.

**Long pause before the agent replies.** Normal at this stage. Module 9 shows you how to measure it and what moves it.

`steps/05-barge-in/main.py` is this module, finished.

## Recap

- **`on_media` is one line**, and there is no voice activity detection anywhere in it. Flux does turn detection inside the model, server-side.
- **Flux scores end-of-turn confidence from the speech itself** (words, intonation, pace) not from a silence timer. That is why a mid-sentence pause doesn't end your turn.
- **80 ms is the chunk size.** Shorter pays WebSocket overhead for nothing; longer makes turn detection sluggish, because Flux cannot score an end-of-turn until the chunk containing it arrives.
- **Sends get their own thread.** A send issued while the connection is closing can inherit a ten-second join; on an audio thread or an event loop that would be catastrophic.
- **Capture starts only after `SettingsApplied`**, because the agent discards media that arrives before the handshake finishes.

## Going further

In `CaptureProcessor`, change `chunkFrames` to a quarter of what the bridge sends it (around 20 ms) and hold a conversation. Then try five times it, half a second. The short chunks pay WebSocket overhead for no benefit; the long ones make turn detection visibly sluggish, because Flux cannot score an end-of-turn until the chunk containing it arrives. 80 ms sits where it does for a reason.

---

You have a working two-way conversation. Now try interrupting it, and find out what's still missing.

**Next:** [Module 5: Interruption done right](../05-barge-in/LAB.md)
