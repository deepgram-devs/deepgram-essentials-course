# Module 3: Hearing the agent

**Goal:** Route the agent's Flux TTS audio to your speaker and hear the greeting out loud.

**You'll learn**

- Why streaming audio always needs a queue, and who owns it
- The difference between "the agent stopped sending" and "you stopped hearing"
- Why an exception in a message handler ends the entire call

## Start here

```bash
uv run steps/03-hear-the-agent/main.py
```

Press **Connect**. Everything from Module 2 works: the agent connects, applies settings, and announces itself in the console. Audio for that greeting is arriving on the socket right now, and the `if isinstance(message, bytes):` block at the top of the message handler is throwing every frame away.

This module gives those audio frames somewhere to go.

## How it works

Deepgram sends TTS audio as raw PCM frames matching the `output` format you declared in `SETTINGS`: 24 kHz, mono, signed 16-bit. No container, no header, no decoding; the bytes off the socket are already playable samples.

Your handler's second argument, `player`, is where they go. One call:

```python
player.send(message)
```

One line, because a queue is already sitting behind it. You rarely write that queue yourself: this bridge ships one, [Deepgram's starter apps](https://github.com/deepgram-starters) ship one, and [Pipecat](https://pipecat.ai) abstracts it completely. Knowing where it lives is what lets you debug it when audio stutters or a reply seems to end early.

Audio arrives from the network in **bursts**: several hundred milliseconds at a time, whenever Flux finishes synthesizing a chunk. Your sound hardware consumes it at a **constant** rate, asking for exactly 128 samples every 5.3 ms and refusing to wait. Something has to absorb that difference, and if it ever runs dry you hear a click.

Open [`web/static/worklets.js`](../../web/static/worklets.js) and read `PlaybackProcessor`. Forty lines, and the whole story:

- `this.queue` holds the chunks waiting to be heard.
- `process()` hands the hardware exactly as many samples as it asked for, then fills any shortfall with **silence** rather than stale audio.
- `return true` at the end, unconditionally. Return `false` and the browser garbage-collects the node after one idle quantum, and the next reply has nowhere to go.

That queue is why `AgentAudioDone` does not mean "the agent stopped talking." It means the agent stopped *sending*. A second of speech may still sit in the queue ahead of you. Module 5 is entirely about that gap.

### Why the voice holds together across a long call

Worth knowing, though you configure none of it here. Flux TTS is built for a conversation rather
than a one-shot read: the connection lives for the whole call, and the model's own prior audio is
its state. That is why the voice at minute ten sounds like the voice at minute one, the tone and
pacing carry across turns instead of each reply being synthesized cold.

It also means the agent can be interrupted and still report exactly how much of its sentence the
caller actually heard. The Voice Agent API reconciles that for you: when you barge in, what was
genuinely spoken is what goes into the conversation history, so the language model does not
believe it finished a sentence the caller never heard. Module 5 is where you feel the
consequences; you never write the reconciliation yourself.

## Do this

**TODO 3.1: Play the audio.** The `bytes` block currently drops every audio frame. Hand them to the player instead: `player.send(message)`.

Notice what you are *not* writing: no error handling, no buffering, no device setup. A chunk the speaker cannot play is the bridge's problem. Look at `LocalPlayer.send` in [`web/audio.py`](../../web/audio.py) to see the version that does have to care. It catches `PortAudioError` and drops the chunk rather than letting it fly, because that handler runs inside the SDK's receive loop, and that loop wraps everything in a single `try`/`except`. The SDK reports any exception escaping it as `EventType.ERROR` and closes the connection. Dropping one 80 ms chunk beats ending the call.

**TODO 3.2: Narrate the turn.** Give `AgentThinking`, `AgentStartedSpeaking`, and `AgentAudioDone` their own `elif` branches so the console reads like a transcript of what the agent is doing.

**Only one of those three will actually print today**, and it is worth knowing which before you
wonder what you did wrong. `AgentAudioDone` arrives on every turn. `AgentStartedSpeaking` is sent
only when `experimental` is set on `Settings`, which this course leaves off.
`AgentThinking` is sent at the think provider's discretion, and `gpt-4o-mini` does not send it.

Write all three anyway. A handler for an event you have not seen yet costs one line and means the
console is ready when the event shows up: which is the same argument as the fallthrough `else`,
and the reason you could read `Welcome` and `History` in Module 2 without planning for them.

`LatencyReport` gets an explicit `pass`. These arrive as a stream through the turn, whether you ask
for them or not, and left to the fallthrough they bury the transcript. Module 9 is where you turn
that stream into one line worth reading.

## Verify

You hear the greeting spoken aloud, the transcript appears on the page, and the console shows:

```
>> Settings applied

[assistant] Thank you for calling Northwind Clinic. I can help you check, book, or move an appointment. How can I help?
>> Agent finished speaking
>> Agent error: CLIENT_MESSAGE_TIMEOUT - ...
>> Connection closed
```

`>> AgentAudioDone` now reads `>> Agent finished speaking`. Watch when it prints: **before** the audio finishes playing. That is the queue.

You will **not** see `>> Agent started speaking` or `>> Agent thinking...`, even though you just
wrote branches for them. That is not a mistake in your code: see the note in `Do this` above.

Expect the `CLIENT_MESSAGE_TIMEOUT` at the end, and this is the last time you will see it. The agent wants a continuous media stream and this module sends none, so it hangs up after about fifteen seconds. Module 4 fixes that by giving it something to listen to.

## Checkpoint

**You have to actually hear the greeting.** Not "the transcript appeared", hear it, through your
speaker or headphones.

Then check one detail, because it is the whole point of the module: `>> Agent finished speaking`
prints **before** the voice stops. If you watch the console while you listen, the line lands and
the agent keeps talking for a moment afterwards. That gap is your playback queue, and Module 5 is
about nothing else.

Do not continue on a silent machine. Module 4 gives the agent your microphone, and debugging a
conversation you cannot hear is far harder than fixing silence now.

## Stuck?

**Silence, but no errors.** Check the browser console (F12). Then re-run `uv run steps/01-setup/main.py` and press "Run the audio checks"; the tone test tells you whether the problem is this module or your output device.

**Nothing happens when you press Connect.** Look for a red box on the page. The most common cause is opening the page on a LAN address rather than `127.0.0.1`; browsers only grant microphone and AudioWorklet access on a secure context.

**Audio plays too fast, too slow, or chipmunk-pitched.** The page and `SETTINGS` disagree about the sample rate. Both read it from `SAMPLE_RATE`, so this should be impossible; if you see it, check the browser console for a warning about the rate the browser actually gave you.

**Stuttering or crackling.** You added something slow inside the `bytes` block. It runs on the SDK's receive loop; keep it to the one call.

`steps/04-talk-to-the-agent/main.py` is this module, finished.

## Recap

- Flux TTS audio arrives as **raw PCM** matching the `output` format you declared, no container, no decoding, already playable.
- **Streaming audio always needs a queue**, because the network delivers bursts and sound hardware consumes at a constant rate. Run dry and you hear a click.
- **`AgentAudioDone` means the agent stopped sending, not that you stopped hearing.** Module 5 lives in that gap.
- **An exception in your message handler ends the call.** It runs inside the SDK's receive loop, which reports anything escaping as `EventType.ERROR` and closes the connection. Dropping one chunk beats hanging up.
- Flux TTS keeps one connection per conversation, so the voice stays consistent across a long call, and the Voice Agent API reconciles what was actually heard when you interrupt.

## Going further

In `PlaybackProcessor.process`, make the underrun fill audible: replay the last buffer of speech instead of writing silence. Just above the underrun loop, save each full buffer that has sound in it, then fill from it:

```js
if (written === output.length && output.some((s) => Math.abs(s) > 0.05)) {
  this.last = output.slice();
}

while (written < output.length) {
  output[written] = this.last ? this.last[written] : 0;
  written += 1;
}
```

The check for sound matters, because every reply ends in a moment of trailing silence, and replaying silence is silent. Run it and listen to a reply. When the queue runs dry at the end, the speaker doesn't stop: it buzzes, looping the same 5.3 ms of speech until the next reply arrives. That is what a naive playback queue sounds like when it runs dry, and it is why the real one writes silence. Undo the change before you move on.

---

You can hear the agent. Now close the loop and let it hear you.

**Next:** [Module 4: The full loop](../04-talk-to-the-agent/LAB.md)
