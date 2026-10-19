# Northwind Clinic: the scenario bible

Every module in this course builds one agent for one client. This file is the **single source of
truth** for that client: the canonical prompt text, keyterms, synthetic data, function schemas,
and greeting.

Because each step folder contains the finished state of the step before it, these strings appear
**byte-identical** in `steps/07-function-calling/`, `steps/08-healthcare/`, `steps/09-optimize/`,
and `steps/10-final/`. `check_scenario_consistency` in `scripts/verify_steps.py` enforces that.
**Change a string here, and it changes in four places.**

> **Demo only.** None of the records below belong to real patients. Nothing here is a HIPAA-compliant design, and
> nothing here should be pointed at real patient data. The boundary techniques in Module 8 are
> real techniques; the compliance work around them is out of scope for this course.

## The client

**Northwind Clinic** runs a patient-access line. Forty percent of its calls are scheduling. The
agent must:

- verify the caller by **date of birth** and the **last four digits of a confirmation code**
- **check appointment availability**
- **book or reschedule**
- **transfer to a human** on an emergency or a frustrated caller

Constraints that shape the build:

- Protected health information stays inside the clinic's environment.
- Callers are on phones, with every accent you can imagine.
- The clinic's vocabulary (drug names, procedures, provider names) is not vocabulary the
  internet at large uses.

## Why a clinic teaches the same lesson banking did

The workshop used a bank because **banking punishes vagueness**: an agent that paraphrases a
number is a defect, not a rough edge. A clinic carries the identical lesson and raises the bar,
because dates and times are harder for the ear than dollars are:

| The discipline | Where it shows up |
|---|---|
| Read a number back before acting on it | DOB and confirmation code, digit by digit |
| Never invent a value | Never invent a slot, a date, or a code |
| Pre-format values for the ear, in the handler | `spoken_date()` / `spoken_time()` |
| An irreversible action needs a confirmation gate | `book_appointment` commits only after a yes |

## Canonical strings

### Greeting

```
Thank you for calling Northwind Clinic. I can help you check, book, or move an
appointment. How can I help?
```

### Keyterms (identical in 07, 08, 09, 10)

```python
KEYTERMS = [
    "Northwind Clinic",
    "confirmation code",
    "reschedule",
    "semaglutide",
    "metformin",
    "lisinopril",
    "colonoscopy",
    "echocardiogram",
    "A1C",
    "Dr. Nwosu",
    "Dr. Bergstrom",
]
```

Module 7 introduces this list and wires it into `SETTINGS`. Module 8 teaches it by **measuring
it**: the learner says "I'm calling about my semaglutide prescription with Doctor Bergstrom, and
my A1C results," once with `KEYTERMS` as shipped and once with `KEYTERMS: list = []`, then
compares the two transcripts.

### Synthetic data

Keyed by **date of birth + last four of the confirmation code**. The digits `4821` and `9007`
are kept from the banking version deliberately: the "last four digits" recognition lesson is
identical, and the existing prose and verify narratives already reference them.

```python
PATIENTS = {
    "1979-04-12:4821": {
        "first_name": "Dana",
        "date_of_birth": "1979-04-12",
        "confirmation_code": "NWC-000-4821",
        "phone": "555-0147",
        "next_appointment": {
            "date": "2026-10-01",
            "time": "9:30 AM",
            "provider": "Dr. Nwosu",
            "type": "A1C follow-up",
            "location": "Northwind Clinic, Suite 200",
        },
    },
    "1965-11-20:9007": {
        "first_name": "James",
        "date_of_birth": "1965-11-20",
        "confirmation_code": "NWC-000-9007",
        "phone": "555-0192",
        "next_appointment": {
            "date": "2026-10-03",
            "time": "2:00 PM",
            "provider": "Dr. Bergstrom",
            "type": "Echocardiogram",
            "location": "Northwind Cardiology, 3rd floor",
        },
    },
}

# Open slots the agent may offer, keyed by date. Pre-formatted for the ear.
AVAILABILITY = {
    "2026-10-08": [
        {"slot_id": "S-1041", "time": "9:00 AM", "provider": "Dr. Nwosu"},
        {"slot_id": "S-1042", "time": "11:30 AM", "provider": "Dr. Nwosu"},
        {"slot_id": "S-1043", "time": "3:15 PM", "provider": "Dr. Bergstrom"},
    ],
    "2026-10-09": [
        {"slot_id": "S-1055", "time": "8:45 AM", "provider": "Dr. Bergstrom"},
        {"slot_id": "S-1056", "time": "1:00 PM", "provider": "Dr. Nwosu"},
    ],
}
```

### Functions

Module 7 introduces two, which is exactly the capstone's requirement: one read-only, one
irreversible:

| Function | Module | Kind | Replaces |
|---|---|---|---|
| `check_availability(date_wanted, visit_type)` | M7 | read-only | `lookup_balance` |
| `book_appointment(date_of_birth, code_last_four, slot_id)` | M7 | **irreversible**, two-phase | `transfer_funds` stretch |
| `confirm_booking(pending_token)` | M7 | commits the above | `confirm_transfer` stretch |
| `find_appointment(date_of_birth, code_last_four)` | M8 | read-only, **payload-filtered** | `find_appointment` (08-healthcare) |
| `transfer_to_human(reason)` | M8 | escalation | new to M8, from draft B9 |

`list_recent_transactions` has no clinic equivalent and is **retired**. Its lesson, return
pre-formatted values so the model cannot paraphrase them, moves into `check_availability`,
which returns a list of slots with `time` already spoken-ready.

### Formatting helpers

Replacing `usd()`. Same lesson: format in the handler, not in the prompt.

```python
def spoken_date(iso: str) -> str:
    """"2026-10-08" -> "Thursday, October 8th". Never a date without a weekday."""

def spoken_time(clock: str) -> str:
    """"9:30 AM" -> "nine thirty in the morning"."""
```

### The prompt

Built **additively**, because folder N+1 is folder N finished. Module 6 writes the voice rules;
Module 7 appends `NUMERIC DISCIPLINE` and function routing; Module 8 appends the privacy block and
the escalation rule. Nothing is ever replaced, which is what keeps the cascade diffs clean.

**Module 6, the voice rules** (the base every later module extends):

```
You are the patient-access agent for Northwind Clinic. You help callers check,
book, and move appointments.

HOW TO SPEAK:
- You are being heard, not read. Never use markdown, bullet points, or emoji.
- Keep replies to one or two sentences, and ask one question at a time.
- Say a date with its weekday ('Thursday, October 8th') and a time in words
  ('nine thirty in the morning').
- If you do not know something, say so plainly. Never guess.

If the caller describes a medical emergency, tell them to hang up and call 911
immediately.
```

**Module 7 appends**: `NUMERIC DISCIPLINE` keeps its header verbatim; it is the anchor learners
remember from the banking version:

```
NUMERIC DISCIPLINE:
- When the caller gives you a date of birth or confirmation code digits, read
  them back one digit at a time and wait for a yes before acting.
- NEVER invent an appointment, a time, or a confirmation code. If you do not
  have it, call a function or say you cannot find it.

Use check_availability to find open slots. To book, call book_appointment and
then confirm_booking only after the caller says yes. Ask for the date of birth
and the last four digits of the confirmation code first.
```

**Module 8 appends** the privacy block and the named escalation path. Written in that module's lab.

## What each module contributes

| Module | Adds to the agent |
|---|---|
| M2 to M6 | Greeting and base prompt only, no functions yet |
| M7 | `check_availability`, `book_appointment` + `confirm_booking`, `KEYTERMS`, the prompt above |
| M8 | Payload filtering, `find_appointment`, `transfer_to_human`, privacy prompt block, the `KEYTERMS` A/B |
| M9 | `eot_threshold` / `eot_timeout_ms` tuning, `LatencyReport` reading |
| A1 | Same agent, Bedrock as the think provider |
