# Module 2: Settings and the event lifecycle

**Goal:** Open a WebSocket to the Voice Agent API, describe the agent you want, and confirm the server accepted it.

**You'll learn**

- How one `AgentV1Settings` object configures listening, thinking, and speaking
- Why the settings handshake has to complete before you send a single byte of audio
- How to write a message handler that survives events Deepgram hasn't shipped yet

## Start here

This folder runs as-is, nothing from Module 1 carries forward; that was a diagnostic. The agent program starts here.

```bash
uv run steps/02-connect/main.py
```

A page opens with a **Connect** button. Press it and you get `>> Connection opened` in the terminal, a handshake is initiated but nothing happens. The settings go out and nothing catches the replies.

You'll continue by adding the orchestration that happens after the handshake is finished.

## How it works

A traditional voice pipeline means three services and the glue between them: speech-to-text, an LLM, text-to-speech. You own the orchestration, the buffering, and every millisecond of latency between the hops.

The Voice Agent API collapses that into one WebSocket. You describe all three components in a single settings message, and Deepgram runs the pipeline server-side. Read `SETTINGS` in `main.py`, because it's the most important thing in the file:

- **`listen`**: Flux, Deepgram's conversational speech-to-text model. Turn detection lives *inside* the model, which is why you'll never write voice activity detection in this course.
- **`think`**: the LLM. `gpt-4o-mini` here, which Deepgram brokers, so your Deepgram key covers it.
- **`speak`**: Flux TTS. The `flux-` prefix routes to Deepgram's v2 Speak backend automatically.
- **`greeting`**: what the agent says first, which Deepgram adds to the conversation history so the LLM knows it already said it.

Every module in this course either adds to that object or reacts to what it produces.

### Where the browser fits

The browser is used to make the microphone and speakers easy to access. Your `main.py` never touches a microphone, a speaker, or a socket. It hands two things to `bridge.run()`: the agent you want, and a function to call when the agent says something. The shared code in [`web/`](../../web/) does the rest.

The bridge hides plumbing, never concepts, and connecting to a voice agent is your main takeaway from this module. Opening the socket is not the same as being connected. A session is a handshake with a gate in the middle: you describe the agent you want, Deepgram confirms it accepted that description, and only after the confirmation does audio mean anything.

Open [`web/session.py`](../../web/session.py) and find `_run()`.

```
open the socket
  → register handlers         events fire on arrival, so a late handler misses the early ones
  → start the listener        the receive loop blocks until close, so it gets its own thread
  → start the sender          one thread owns every write, and nothing else touches the socket
  → send SETTINGS             the description of the agent you want
  → wait for SettingsApplied  Deepgram accepting it, ten seconds at most
  → the gate opens            the browser is cleared to capture
```

That last line is the one to carry forward. `SettingsApplied` flips a single flag, and everything that produces audio waits on it: the browser gets a `ready` frame telling it to start capturing, and any chunk that beats the flag is dropped before it reaches your `on_media`. The handshake is what turns an open socket into a running agent.

## Do this

Work through the TODO blocks in `main.py` in order.

**TODO 2.1: Handle inbound messages.** Write `on_message`. Three details in that handler matter more than they look:

The `isinstance(message, bytes)` check comes first because audio frames are not JSON events and have no `.type` attribute. Reach for one anyway and you get `"Unknown"` thousands of times a minute.

The final `else` prints instead of ignoring. Deepgram adds server events over time, and the fallthrough means new ones surface in your console rather than vanishing silently. You'll rely on that in Module 5.

The signature takes three arguments (`agent`, `player`, `message`) whether you use them or not. `player` starts earning its place in Module 3, `agent` in Module 7.

**TODO 2.2: Hand your agent to the bridge.** `bridge.run(settings=SETTINGS, on_message=on_message)`.

Note what you are *not* passing: `on_media`. Without it the bridge never opens the microphone at all, which is why this module sends no audio, and why the agent hangs up on you.

## Verify

```
>> Connection opened
>> Welcome
Sending agent settings...
>> Settings applied
[assistant] Thank you for calling Northwind Clinic. I can help you check, book, or move an appointment. How can I help?
>> History
>> AgentAudioDone
>> Agent error: CLIENT_MESSAGE_TIMEOUT - ...
>> Connection closed
```

The agent already spoke. That `[assistant]` line is `ConversationText`, and the audio for it streamed past your handler while you watched, and you just have nowhere to play it yet. It also appears in the transcript on the page, which is the bridge mirroring events for you, not your code.

Notice `>> Welcome` and `>> History` arriving through the fallthrough branch. Neither has an explicit `elif`, and both still showed up. That's the design working.

Expect the `CLIENT_MESSAGE_TIMEOUT` at the end. The agent wants a *continuous* media stream and hangs up after about fifteen seconds of receiving none. Nothing sends audio until Module 4. Worth seeing now so you recognize it later.

## Checkpoint

Two lines have to appear before you move on:

1. **`>> Settings applied`**: Deepgram accepted your description of the agent. Until this
   arrives you have an open socket, not a running agent.
2. **An `[assistant]` line** carrying the Northwind greeting. That proves the think and speak
   stages are configured too, not just the connection.

The `CLIENT_MESSAGE_TIMEOUT` and `>> Connection closed` that follow are **expected**: read them
as the end of a successful run, not a failure. A problem at this checkpoint is almost always the
API key, and the `Error` line just above the timeout will say so.

### The events of one turn

This is the lifecycle you'll be reading for the rest of the course, so it's worth a table. Two
kinds of frame travel on the socket: **JSON text frames** carry events, **binary frames** carry
audio, and both go in both directions.

| Event | What it means | What your code does about it |
|---|---|---|
| `Welcome` | The socket is open. Carries a `request_id`. | Log the `request_id`: it ties your logs to the Console. Module 9 uses it. |
| `SettingsApplied` | Your settings were accepted. | The gate opens; audio now means something. |
| `ConversationText` | A finished turn, with `role` and `content`. | Print it, or show it in a transcript. |
| `History` | Deepgram's running record of the conversation. | Nothing, usually. Arrives via the fallthrough. |
| `UserStartedSpeaking` | The caller began a turn. | **Stop playback immediately.** This is barge-in, and it is Module 5. |
| `AgentThinking` † | The language model is working. | A "thinking" indicator, if you have a UI. |
| `AgentStartedSpeaking` † | The first audio of the reply is on its way. | Usually nothing; useful for timing. |
| *(binary frames)* | The reply, as audio. | Play them as they arrive. Module 3. |
| `AgentAudioDone` | The agent finished **sending** audio. | Not the same as you finishing *hearing* it: there may still be a second queued in the browser. Module 5 depends on that difference. |
| `LatencyReport` | Timing data, streamed through the turn. | Module 9 turns it into something useful. It arrives whether you ask for it or not. |
| `Warning` | Something non-fatal. | Log it and carry on. |
| `Error` | Something fatal; the socket is closing. | Reconnect and resend settings. Treat every `Error` as a reconnect, not a retry. |

You will not see all of these in this module, because nothing is sending audio yet. You have
already seen four of them.

**† These two do not arrive by default.** `AgentStartedSpeaking` is emitted only when
`experimental` is set on `Settings`, and `AgentThinking` is emitted at the think provider's
discretion: `gpt-4o-mini` does not send it. This course leaves `experimental` off, so you will
not see either one. The handlers you write for them in Module 3 are there so the console is ready
when they do arrive, which is exactly what the fallthrough branch is for.

## Stuck?

**The page says the server timed out applying settings**. Either a rejected setting or a bad key. Check the terminal for an `Error` message just above it.

**Nothing after `>> Connection opened`**. You defined `on_message` but did not pass it to `bridge.run`.

**The Connect button is disabled**. Read the red box on the page. Almost always a page opened on a LAN address rather than `127.0.0.1`.

**`Address already in use`**. An earlier module is still running in another terminal. Stop it, or pass `--port 8001`.

`steps/03-hear-the-agent/main.py` is this module, finished.

## Recap

- **One `AgentV1Settings` object configures all three models** (`listen`, `think`, `speak`) plus the greeting. Every later module either adds to that object or reacts to what it produces.
- **An open socket is not a running agent.** `SettingsApplied` is the gate, and everything that produces audio waits on it.
- **JSON frames are events, binary frames are audio**, in both directions.
- **Handle unknown events by printing them.** Deepgram adds server events over time, and the fallthrough is what makes them visible instead of silent.
- `CLIENT_MESSAGE_TIMEOUT` with no `on_media` is **expected**, not a bug.

## Going further

Change `greeting` to something else and run again. Then delete it entirely: the agent connects and waits silently, which is what you want for an agent that answers rather than opens.

---

Your agent is live and already talking. Next you give the audio somewhere to go, and hear it.

**Next:** [Module 3: Hearing the agent](../03-hear-the-agent/LAB.md)
