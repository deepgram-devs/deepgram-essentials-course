# Troubleshooting

The failures that actually happen, by symptom. Each module's `Stuck?` section covers its own
specifics; this is the cross-cutting list.

## Setup and audio

**Microphone permission.** The prompt appears during Module 1 and is easy to click past. Fix: the
icon at the left of the address bar, allow, press the button again. On macOS also check **System
Settings → Privacy & Security → Microphone** and confirm the *browser* is enabled: it is the
browser that needs permission now, not the terminal.

**The page is on the wrong address.** `getUserMedia` and `AudioWorklet` need a secure context,
which browsers grant to `localhost` and nothing else. A LAN address makes the audio API silently
vanish. Symptom: the Connect button stays disabled with a red box above it. Fix: use the
`http://127.0.0.1:8000` the terminal printed.

**Bluetooth headsets.** Activating the microphone flips many headsets into a low-quality mono
profile, and some then fail to open at all. Reconnect, or switch to wired.

**The agent talks to itself.** Laptop speakers feeding the laptop microphone, past the echo
canceller. Headphones, or turn the volume down. Module 1's check reports whether the browser
actually granted echo cancellation, which is worth reading when this happens.

**A truncated API key.** Copy-paste drops characters or adds a space. Module 1 makes a real
authenticated call rather than checking the string is non-empty, so this surfaces immediately as
`Deepgram rejected the key`.

**The microphone row says `OK` with a peak near zero.** The failure that looks like success. A
device opened and heard nothing: you are muted, or the browser picked the wrong input. Fix it
before Module 4, or you will debug an agent that never answers because it never heard you.

## Connection and configuration

**`The agent refused these settings`.** Nothing is wrong with your machine: Deepgram does not
serve one of the three models where you are connecting. The error names which one. Blank
`DEEPGRAM_REGION` resolves almost every case.

**`CLIENT_MESSAGE_TIMEOUT` after about fifteen seconds.** Expected in Modules 2 and 3, which send
no audio. From Module 4 onward it means `on_media` was defined but never passed.

**A setting appears to do nothing.** Restart `main.py`: settings are read once, at startup. A
misspelled voice name is the exception that really is accepted and fails later, as warnings (below).

**`INVALID_SETTINGS` and the connection closes.** A value outside its valid range, such as an
`eot_threshold` below 0.5 or an `eot_timeout_ms` above 60000, fails the handshake. The `Error`
description names the setting and the range it wanted.

**A misspelled voice.** `SettingsApplied` arrives normally, then three `SPEAK_REQUEST_FAILED`
warnings and a fatal `FAILED_TO_SPEAK`. No audio, and no fallback to a default voice.

## Behaviour

**Events that never arrive.** `AgentStartedSpeaking` is only sent when `experimental` is set on
`Settings`, and `AgentThinking` is emitted at the think provider's discretion: `gpt-4o-mini` does
not send it. Handlers for both are worth keeping; their absence is not a fault.

**The agent invents facts.** The prompt is missing an instruction to admit ignorance. "Never guess"
is the load-bearing line.

**A function never fires.** Nine times out of ten it is the description, which must say *when* to
call, not just what the function does.

**The agent says it did something and didn't.** Most common with transfers: it announces a handoff
and never calls the function. Assert on the console line, not the sentence.

**Audio stutters during a function call.** Your handler runs on the SDK's receive loop, the same
thread delivering audio. Keep handlers fast, or move the work to a thread.

**An exception in a handler drops the call.** Anything escaping into the receive loop surfaces as
`EventType.ERROR` and closes the connection. Return failures as values.
