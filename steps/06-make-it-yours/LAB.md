# Module 6: Prompting for the ear

**Goal:** Give the agent the Northwind job, a voice, and prompt rules written for the ear.

**You'll learn**

- The two prompt instructions that separate a voice agent from a chatbot read aloud
- Where rejected settings go when they don't fail the handshake
- What swapping the LLM costs you in latency

## Start here

```bash
uv run steps/06-make-it-yours/main.py
```

Everything works: it hears you, answers you, and stops when you talk over it. It already greets you as Northwind, because the prompt is written for you this time. The voice is still the stock one, and it will stay that way until you change it.

This module has the least code in the course and the most to play with.

## How it works

Three settings define the agent's character, and they're independent of each other:

**`prompt`:** the standing instructions the model sees ahead of every user turn. Personality, job, boundaries.

**`speak.provider.model`:** the voice. Purely how it sounds; it changes nothing about what the agent says.

**`greeting`:** the opening line, and the only thing the agent says before it knows anything about the user. It's doing all the work of setting expectations.

The prompt deserves the most attention, because writing prompts for *speech* differs from writing them for chat in two specific ways.

**Tell it that it's speaking.** LLMs default to writing. Without an explicit instruction you get markdown, bullet points, and asterisks read aloud, and it's genuinely jarring the first time you hear a TTS engine pronounce "asterisk asterisk important asterisk asterisk."

**Tell it to be brief.** A four-sentence answer that scans fine in a chat window feels interminable when you have to sit through it. Voice punishes verbosity in a way text doesn't.

Keep the prompt short for a second reason: every turn re-sends every token, and long prompts slow the first reply.

### The rules worth writing down

Those two are the minimum. A prompt for a production voice agent earns its keep with five:

| Rule | Why it matters out loud |
|---|---|
| **No markup.** "Never use markdown, bullet points, or emoji." | Otherwise you hear "asterisk asterisk important asterisk asterisk." |
| **Short turns.** One or two sentences, one question at a time. | A caller cannot skim. Two questions in one breath gets one answer, and you won't know which. |
| **Data for the ear.** Dates with their weekday, times in words, digits read individually. | "Ten one" could be October 1st, 10:01, or the tenth and the first. A weekday removes the ambiguity for free. |
| **Confident phrasing.** Say what you know; say plainly when you don't. | Hedging sounds evasive in speech in a way it doesn't in text. And "never guess" is the instruction that stops an agent inventing an appointment. |
| **Named escalation triggers.** Spell out the exact situations where the agent hands off. | "Use judgement" is not a trigger. "If the caller describes a medical emergency" is. |

The Northwind prompt in `main.py` is those five rules applied to this client. Read it before you
change it.

## Do this

**TODO 6.1: Read the Northwind prompt, then test it.** The prompt is written for you this time,
because it is the one the rest of the course builds on. Your job is to find out whether it works.

Run the agent and try each of these out loud:

1. Ask something that would normally get a bulleted list: *"what do I need to bring?"* You should hear prose, not punctuation.
2. Ask for a fact it does not have: *"what time do you close on Saturday?"* There are no opening hours anywhere in this agent.
3. Ask it two questions at once. Does it answer one and ask about the other, or blur them together?

Then break it deliberately. Delete this line from the prompt:

```
- If you do not know something, say so plainly. Never guess.
```

…and ask about Saturday again. Here is the same question, with and without that one line:

```
with    [assistant] I'm not sure about our Saturday hours.
        [assistant] Would you like to book or move an appointment instead?

without [assistant] We close at one in the afternoon on Saturday.
        [assistant] Do you need to book an appointment for that day?
```

One in the afternoon is invented. There are no hours in this agent to be right or wrong about, and
it stated a specific time with complete confidence. Put the line back.

Note *why* the question matters: asking "when is my next appointment?" is a weaker test, because
the model's natural next move is to ask who you are, which hides the problem. Pick a question with
no identity path and no data behind it, and the gap shows immediately.

**TODO 6.2: Pick a voice.** Swap `flux-alexis-en` for another Flux voice. The full list lives in the [Deepgram TTS models documentation](https://developers.deepgram.com/docs/tts-models).

**TODO 6.2b: Try a different opening line.** The greeting is the only thing the agent says before it knows anything about the caller, so it is doing all the work of setting expectations. Compare "Thank you for calling Northwind Clinic, how can I help?" with the version in `main.py` that names what it can do. Listen to both. The second one stops the caller having to guess at the menu.

**TODO 6.3: Try a different brain.** `gpt-4o-mini` is fast and cheap, which matters more than raw capability when someone is waiting to hear a reply. Before you change anything, have a few short conversations and note the latency after each reply. It's the number in seconds on the right of the browser's activity line, just above the transcript, and it only shows the latest turn, so write each one down. Then switch to `gpt-5.5`, comment out the `temperature` line (`gpt-5.5` doesn't accept it), restart, and ask the same questions. Compare the two sets of numbers. You pay for that capability in latency, and your users feel every bit of it. Module 9 is where that number becomes the whole point.

`temperature` controls variability: `0.0` for an agent that must say the same thing every time, `1.0` and up for a chatty one. Other providers work here too (Anthropic, Google, Groq, AWS Bedrock) via the matching `ThinkSettingsV1Provider_*` class. Note that you're switching models without an OpenAI account: Deepgram brokers that call. It doesn't broker all of them, and [Appendix A](../06b-bring-your-own-llm/LAB.md) is the optional detour into what changes when the model runs in your account instead.

**TODO 6.4: Surface warnings.** Add a `Warning` branch mirroring the `Error` branch above it.

Warnings are where deferred failures go. A misspelled voice is not caught during the handshake: it
surfaces here, later, when the agent first tries to speak with it. Without this branch you get an
agent that connected successfully and then stopped, and nothing on screen telling you why.

## Verify

Your agent greets you as Northwind, in the voice you chose, and holds its rules when you push at
it. Ask it what you need to bring and you hear prose, not punctuation. Ask it about an appointment
it has no data for and it says so.

Now the misspelled voice, which is the more interesting half of this module. With TODO 6.4 done:

```
>> Settings applied
>> Agent warning: SPEAK_REQUEST_FAILED - Error making request to Deepgram speak provider (model: 'flux-alexei-en', voice: 'flux-alexei-en').
>> Agent warning: SPEAK_REQUEST_FAILED - Error making request to Deepgram speak provider (model: 'flux-alexei-en', voice: 'flux-alexei-en').
>> Agent warning: SPEAK_REQUEST_FAILED - Error making request to Deepgram speak provider (model: 'flux-alexei-en', voice: 'flux-alexei-en').
>> Agent error: FAILED_TO_SPEAK - Failed to speak. Please check your agent.speak settings.
```

Read that sequence carefully, because it is not what most people expect. **Your settings were
accepted**: `SettingsApplied` arrived. The voice name is not validated during the handshake. It
fails later, when the agent first tries to speak: three retries, each surfacing as a warning, and
then a fatal error. There is **no fallback to another voice**, and not one byte of audio is
produced.

That gap between "settings accepted" and "agent can actually speak" is the thing to remember. It
is also why TODO 6.4 matters: without a `Warning` branch, all you would see is an agent that
connected fine and then died, with no clue why.

## Checkpoint

Four things, and the third is the one people skip:

1. **The agent greets you as Northwind** in a voice you chose.
2. **It answers in prose**, with no markup read aloud.
3. **It refuses to invent a fact.** Ask what time it closes on Saturday. There are no hours in this agent. It must say it doesn't know rather than name a time. If it names one, your prompt is not doing its job: and Module 7 will hand it real data to be confidently wrong about.
4. **A misspelled voice produces warnings and then a fatal error**, and you saw both. If you saw the error with no warnings, TODO 6.4 isn't done.

## Stuck?

**It still reads markdown aloud.** The instruction has to be explicit. "Never use markdown, bullet points, or emoji" works; "be conversational" doesn't.

**It ignores the persona after a few turns.** Move the important constraints to the *end* of your prompt, and cut anything that isn't load-bearing.

**Answers got long again.** Larger models are more verbose by default. Re-state the brevity instruction, or go back to `gpt-4o-mini`.

**Voice didn't change and there's no warning.** Confirm you edited `speak`, not `listen`, and that TODO 6.4 is done.

**Noticeably slower after switching models.** Working as intended. Check the browser's latency readout and decide whether the quality is worth it.

`steps/07-function-calling/main.py` is this module, finished. Module 7 keeps this prompt and
**adds** to it rather than replacing it, so whatever you changed here carries forward, if you
want the canonical version back, take it from that folder.

## Recap

- **Three independent settings define the agent's character:** `prompt` (job and boundaries), `speak.provider.model` (purely how it sounds), and `greeting` (the only line spoken before the agent knows anything).
- **Prompts for speech differ from prompts for chat in five ways:** no markup, short turns, data shaped for the ear, confident phrasing, and named escalation triggers.
- **"Never guess" is load-bearing.** It is the line that stops an agent stating an appointment that does not exist.
- **Keep the prompt short**: every token is re-sent on every turn, so a long prompt slows the first reply.
- **A bad voice name is accepted at handshake and fails later**, as warnings then a fatal error, with no fallback. Surfacing `Warning` is what makes that visible.

## Going further

Give the agent a constraint it has to hold under pressure ("you only discuss coffee, and you politely redirect anything else"), then spend two minutes trying to talk it off-topic. Prompt injection resistance in a voice agent is the same problem as in a chat agent, except your attacker is talking out loud.

---

Your agent has a job and a voice. What it can't do yet is anything outside its own head.

**Next:** [Module 7: Function calling](../07-function-calling/LAB.md)
