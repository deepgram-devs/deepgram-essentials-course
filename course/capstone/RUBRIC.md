# Capstone rubric

Six criteria, scored 1 to 4. **Pass at 18 out of 24, with nothing below 2.**

A score of 2 is a competent submission. 3 is what a reviewer would be happy to see on a client
project. 4 is unusual and means you showed the reviewer something they had not thought of.

Reviewed by a Deepgram engineer. If you miss, you get written feedback and one resubmission; a
second attempt uses a different scenario.

---

### 1. Settings and turn-taking fit the scenario

| | |
|---|---|
| **1** | Defaults left untouched, or values changed with no stated reason. |
| **2** | `eot_threshold` and `eot_timeout_ms` set deliberately, with a one-line justification. |
| **3** | Values chosen from measured evidence across at least three configurations, and the trade-off named. |
| **4** | The choice is defended against a specific caller in the set who is badly served by it, and that cost is accepted explicitly. |

### 2. The prompt is written for the ear

| | |
|---|---|
| **1** | A chat prompt. Markup appears in speech, or replies run long. |
| **2** | No-markup and brevity rules present and working. |
| **3** | Also shapes data for the ear (dates with weekdays, digits read back) and instructs the agent to admit ignorance rather than guess. |
| **4** | Carries at least one named escalation trigger that a scripted caller actually exercises, and the prompt has visibly been iterated against failures rather than written once. |

### 3. Functions are correct and safe

| | |
|---|---|
| **1** | One function, or functions that raise on bad input. |
| **2** | At least two functions: one read-only, one that changes state. Misses return a message rather than raising. |
| **3** | The state-changing function is gated: it reserves, reads back, and commits only on explicit confirmation. The commit is idempotent. |
| **4** | The gate is shown to survive an adversarial caller (someone who changes their mind at the read-back, or tries to rush past it) with evidence in the scorecard. |

### 4. The channel works end to end

| | |
|---|---|
| **1** | Does not run, or runs only with manual intervention. |
| **2** | Runs in the browser and holds a conversation. |
| **3** | Barge-in is clean: the agent stops mid-word, with no trailing audio. |
| **4** | Failure paths are handled audibly: a handler error, a function that finds nothing, or an unrecognized caller all produce a spoken response rather than silence or a dropped call. |

### 5. Observability is in place and used

| | |
|---|---|
| **1** | Nothing captured. |
| **2** | `request_id` logged, and `total_latency` printed per turn. |
| **3** | `tags` set meaningfully, and the latency numbers appear in the scorecard rather than only the console. |
| **4** | The rationale uses the numbers to locate a *stage*, not just "it got faster" but which part of the turn moved, and what that implies. |

### 6. The evaluation is fair and honestly reported

| | |
|---|---|
| **1** | No evaluation, or impressions only. |
| **2** | The caller set run against one configuration, with results recorded. |
| **3** | The same callers run against a baseline and a tuned configuration, changing one thing at a time. |
| **4** | A regression is reported. Something got worse, it is named, and the submission argues why the trade was still worth making. |

---

## What reviewers weight most

Criterion 6 at level 4 is the one that distinguishes submissions. **A scorecard with no regression
in it is usually an incomplete evaluation, not a perfect agent.** Tuning a voice agent trades one
failure mode for another; if nothing got worse, you probably did not measure the thing that did.
