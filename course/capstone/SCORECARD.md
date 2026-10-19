# Capstone scorecard

Copy this into your submission and fill it in. Two runs of the [caller set](CALLERS.md), one
configuration change between them.

## Configurations

| | Baseline | Tuned |
|---|---|---|
| `eot_threshold` | | |
| `eot_timeout_ms` | | |
| think model | | |
| **what changed, and why** | — | |

State the *one* thing you changed. If you changed more than one, you cannot attribute the
difference, and criterion 6 caps at 2.

## Results

For each caller: did it pass, and what was `total_latency` on that turn?

| # | Caller | Baseline | `total_latency` | Tuned | `total_latency` | Notes |
|---|---|---|---|---|---|---|
| 1 | Opens correctly | ☐ | | ☐ | | |
| 2 | Digits read back | ☐ | | ☐ | | |
| 3 | Mid-sentence pause | ☐ | | ☐ | | |
| 4 | Availability + proper noun | ☐ | | ☐ | | |
| 5 | **The gate**: nothing booked | ☐ | | ☐ | | |
| 6 | Refuses visit type | ☐ | | ☐ | | |
| 7 | Refuses code and phone | ☐ | | ☐ | | |
| 8 | **Transfer actually called** | ☐ | | ☐ | | |

`request_id` for one representative call from each run:

- baseline: `____`
- tuned: `____`

## What got worse

The most important box on this page. Name at least one thing the tuned configuration made worse,
or state plainly that you looked and found none: and say how you looked.

> 

## Rationale

One page, no more. Four questions:

1. **What did you tune, and why that?**
2. **What do the numbers show?** Cite a specific stage, not just the total.
3. **What regressed, and why was the trade worth it?**
4. **What would you watch in production**, and which `request_id` or tag would you filter on to watch it?
