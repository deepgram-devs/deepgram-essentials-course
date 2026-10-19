# Deferred: what this course does not teach

The Builder Essentials outline describes four capabilities this course does not cover hands-on.
They are listed here so the omission is deliberate and visible, rather than something a learner
discovers when a client asks for it.

Nothing below appears in the capstone or the knowledge check. `scripts/verify_steps.py` enforces
that: `check_capstone_scope` fails the build if the brief or the rubric names any of it.

| Capability | Would attach to | Why it is deferred |
|---|---|---|
| **Standalone Flux (`/v2/listen`)** (`TurnInfo` events, the turn state machine, `EagerEndOfTurn` / `TurnResumed` / `ForceEndTurn`) | Module 4 | This course reaches Flux only through the Voice Agent API, which handles the turn state machine for you. Module 4 teaches the *model*: how end-of-turn confidence works, and Module 9 tunes the two thresholds the Agent API exposes. The raw event stream needs a second, non-agent codebase. |
| **Mid-call context control**: `UpdatePrompt`, `UpdateThink`, `UpdateSpeak`, `UpdateListen`, `InjectAgentMessage`, `InjectUserMessage` | Module 9 | The reference agent documents these as next steps but never exercises them. They are the basis of multi-phase agents (change behaviour after identity is verified), which is a genuinely useful pattern and a module in its own right. |
| **Telephony channels**: mulaw at 8 kHz, media-stream bridges, inbound and outbound patterns, CCaaS integrations | a new module | The repo ships a browser bridge. Putting the agent on a phone line is an encoding change plus a bridge service, and the bridge is the part that takes real work. The capstone therefore asks for a browser channel. |
| **Automated evaluation**: a scripted-caller harness, regression runs, fallback chains, session-limit handling | Module 9 | Module 9 teaches measurement by hand, and the capstone's caller set is run manually. A harness that drives synthesized callers and diffs the results is the natural next build, and it is what turns the scorecard into CI. |

## If you want them anyway

The course is a foundation, not a ceiling. Each of these is a reasonable next project on top of
the finished agent in `steps/10-final/`, and the [Voice Agent
docs](https://developers.deepgram.com/docs/voice-agent) cover all four.

A note on the evaluation harness in particular: everything the capstone asks you to do by hand is
automatable, and automating it is the single highest-value thing you can build after this course.
The discipline (same callers, one change at a time, numbers written down) matters more than
whether a human or a script runs it.
