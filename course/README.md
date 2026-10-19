# Deepgram Builder Essentials: Technical Track

A self-paced course. You build one voice agent for one client, one capability at a time, and
submit it for a badge.

- **[The scenario](SCENARIO.md)**: Northwind Clinic, and the canonical prompt, data, and functions every module shares.
- **[The capstone](capstone/BRIEF.md)**: what to submit, and [how it's scored](capstone/RUBRIC.md).
- **[What this course doesn't teach](DEFERRED.md)**: four capabilities, deliberately out of scope.
- **[Troubleshooting](TROUBLESHOOTING.md)**: the failures that actually happen, by symptom.
- **[Landing page copy](front-page.md)**: for catalogues and listings.

## The path

Start at [Module 0](../steps/00-overview/LAB.md) and work forward. Each folder is a complete,
working program, so you can also drop in anywhere: folder N+1 is folder N finished, which makes
it both the answer key and a valid starting point.

| Module | Folder | Typical time |
|---|---|---|
| 0, Welcome, the loop, and the capstone | `00-overview` | 15 min |
| 1: Set up and smoke-test | `01-setup` | 15 min |
| 2, Settings and the event lifecycle | `02-connect` | 20 min |
| 3, Hearing the agent | `03-hear-the-agent` | 25 min |
| 4: The full loop and turn-taking | `04-talk-to-the-agent` | 30 min |
| 5, Interruption done right | `05-barge-in` | 25 min |
| 6: Prompting for the ear | `06-make-it-yours` | 20 min |
| 7, Function calling | `07-function-calling` | 35 min |
| 8, Identity, vocabulary, and the PII boundary | `08-healthcare` | 25 min |
| 9: Turn-taking, latency, and observability | `09-optimize` | 25 min |
| 10, Reference agent and capstone | `10-final` | 20 min |
| Appendix A, Bring your own LLM *(optional)* | `06b-bring-your-own-llm` | 15 min |

Roughly four and a half hours of labs, plus the capstone. Folder numbers match module numbers,
and so do the `TODO (Step N.x)` markers; Appendix A's folder is `06b` because it branches off Module 6.

Each module ends with a five-question quiz; the badge adds a thirty-question knowledge check and a
practical submission.

## Links worth keeping

| What | Where |
|---|---|
| Sign up / API key | https://console.deepgram.com/signup?jump=keys |
| Voice Agent docs | https://developers.deepgram.com/docs/voice-agent |
| Flux docs | https://developers.deepgram.com/docs/flux |
| Voice catalogue | https://developers.deepgram.com/docs/tts-models |
| Playground | https://playground.deepgram.com/voice-agent |
| Bedrock model access *(Appendix A only)* | https://console.aws.amazon.com/bedrock/home#/modelaccess |
| Discord | https://discord.gg/xWRaCDBtW4 |
| GitHub Discussions | https://github.com/orgs/deepgram/discussions |

## Maintaining this course

```bash
uv run scripts/verify_steps.py
```

Checks the manifest against `steps/`, that every module compiles and lints, that no `TODO` marker
leaks into the next folder's answer key, that every module ships a lab, that labs carry the course
sections, that every relative link resolves, that no prose reads as instructor-led, that the
Northwind scenario is uniform across the cascade folders, that no module asserts a factual claim a
later module disproves, that every advertised function schema names parameters its handler accepts,
and that the capstone stays inside what the course teaches.

Run it after editing anything under `steps/`, `course/`, or `web/`.

Narration, the on-screen cards, and the badge knowledge check are not here: they live in the
private teaching repository, which reads this manifest and has a verifier of its own.
