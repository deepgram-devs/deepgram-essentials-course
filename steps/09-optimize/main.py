"""Module 9 - Turn-taking, latency, and observability.

Runs exactly as Module 8 left it: the Northwind agent, verifying callers,
refusing what it should not say, and handing off when it is out of its depth.

It works. What you cannot yet say is whether it is any *good* -- how long a
caller waits after they stop speaking, where that time goes, and whether the
change you just made helped or only felt like it did.

This module is about replacing impressions with numbers. You turn on the
latency report, learn to read its fields, move the two turn-taking dials and
measure what each one costs, and capture the identifiers that let you find one
specific call again tomorrow.

Look for the "TODO (Step 9.x)" blocks below. Inside them, "#:" marks the
instructions and everything else is code, commented out at the indentation it
belongs at: select those lines and press Cmd+/ (Ctrl+/ on Windows and Linux)
to uncomment them where they sit.

Run it with:  uv run steps/09-optimize/main.py
"""


import json
from datetime import date

from deepgram.agent.v1.types import (
    AgentV1SendFunctionCallResponse,
    AgentV1Settings,
    AgentV1SettingsAgent,
    AgentV1SettingsAgentContextListen,
    AgentV1SettingsAgentContextListenProvider_V2,
    AgentV1SettingsAudio,
    AgentV1SettingsAudioInput,
    AgentV1SettingsAudioOutput,
)
from deepgram.types.speak_settings_v1 import SpeakSettingsV1
from deepgram.types.speak_settings_v1provider import SpeakSettingsV1Provider_Deepgram
from deepgram.types.think_settings_v1 import ThinkSettingsV1
from deepgram.types.think_settings_v1functions_item import ThinkSettingsV1FunctionsItem
from deepgram.types.think_settings_v1provider import ThinkSettingsV1Provider_OpenAi
from dotenv import load_dotenv

from web import AgentHandle, Player, bridge

load_dotenv()

SAMPLE_RATE = 24000  # Deepgram's recommended sample rate for voice agents. For telephony, 8000 is recommended.
# The browser captures in 80 ms chunks -- the size Flux's turn detection is
# tuned for. That interacts with everything below: no threshold setting can
# detect a turn end sooner than the chunk carrying it arrives.

# Flux's turn detection knobs, at a balanced starting point. Every turn gets an
# end-of-turn confidence score; these decide how much confidence is enough and
# how long silence may run. This module is where you move them.
#: ---- TODO (Step 9.2): Move the dials -------------------------------------
#: Flux scores every turn for end-of-turn confidence as the audio streams in.
#: These two constants act on that score, and they trade against each other:
#: end a turn too early and you cut people off mid-thought, too late and every
#: exchange carries a dead pause. There is no setting that avoids both.
#:
#: Once TODO 9.1 is printing a number, run the four rows in the LAB's table --
#: 0.5/5000, 0.9/5000, 0.7/500, then back to 0.7/5000 -- holding the same short
#: conversation each time. Listen, and watch ">> Latency:" alongside.
#:
#: A value outside its valid range fails the handshake. Settings are never
#: applied, the Error branch from Module 2 prints INVALID_SETTINGS with the
#: range it wanted, and the connection closes. So if a change seems to do
#: nothing, the value was fine: check that you restarted after editing it.
#:
#: Also available: eager_eot_threshold (0.3-0.9, off by default, must be <=
#: EOT_THRESHOLD). It starts the LLM on a *probable* turn end and discards the
#: work if the caller keeps talking -- lower latency, more LLM calls. Add it in
#: the provider below once the two constants make sense on their own.
#: --------------------------------------------------------------------------
EOT_THRESHOLD = 0.7  # Valid 0.5-1.0. Raise it to stop the agent cutting people off mid-thought, lower it for snappier replies at the cost of false turn ends.
EOT_TIMEOUT_MS = 5000  # Valid 500-60000. Hard ceiling: end the turn after this much silence, whatever the score says.

# Words this agent hears all day. Flux biases recognition toward them, which is
# the cheapest accuracy fix available for a domain-specific agent. Module 8
# measures what it is actually worth -- see the exercise in
# steps/08-healthcare/LAB.md.
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

# Slots the agent may offer. In production this is the clinic's scheduling
# system; here it is a dict, so the lab runs with no extra credentials.
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

# Committed bookings, and reservations still waiting on a spoken yes. Both are
# in memory, which is fine for a lab and wrong for a phone line.
BOOKED: dict = {}
PENDING: dict = {}

_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
_ORDINAL = {1: "st", 2: "nd", 3: "rd", 21: "st", 22: "nd", 23: "rd", 31: "st"}
_HOURS = [
    "twelve", "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten", "eleven",
]
_MINUTES = {15: "fifteen", 30: "thirty", 45: "forty-five"}


def spoken_date(iso: str) -> str:
    """Format an ISO date the way a person says it, weekday included.

    The weekday is not decoration. It is the caller's free second chance to
    catch a date they misheard, and it costs one word.

    Args:
        iso: A date as YYYY-MM-DD.

    Returns:
        The date as, for example, "Thursday, October 8th".
    """
    day = date.fromisoformat(iso)
    return f"{day.strftime('%A')}, {_MONTHS[day.month - 1]} {day.day}{_ORDINAL.get(day.day, 'th')}"


def spoken_time(clock: str) -> str:
    """Format a clock time as words.

    Args:
        clock: A time as "9:30 AM".

    Returns:
        The time as, for example, "nine thirty in the morning".
    """
    hhmm, meridiem = clock.split()
    hour, minute = (int(part) for part in hhmm.split(":"))
    part_of_day = "in the morning" if meridiem.upper() == "AM" else "in the afternoon"
    if minute == 0:
        return f"{_HOURS[hour % 12]} o'clock {part_of_day}"
    return f"{_HOURS[hour % 12]} {_MINUTES.get(minute, str(minute))} {part_of_day}"


def check_availability(date_wanted: str, visit_type: str = "") -> dict:
    """List open slots on one date, formatted for speech.

    Read-only, so the agent may call it as often as it likes.

    Args:
        date_wanted: The date to check, as YYYY-MM-DD.
        visit_type: Optional kind of visit. Accepted and ignored here; a real
            scheduler would filter on it.

    Returns:
        The open slots with times already spoken-ready, or a graceful miss.
    """
    del visit_type
    slots = AVAILABILITY.get(date_wanted)
    if not slots:
        return {"found": False, "message": f"There is nothing open on {spoken_date(date_wanted)}."}

    return {
        "found": True,
        "date": spoken_date(date_wanted),
        "slots": [
            {"slot_id": slot["slot_id"], "time": spoken_time(slot["time"]), "provider": slot["provider"]}
            for slot in slots
            if slot["slot_id"] not in BOOKED
        ],
    }


def _find_slot(slot_id: str) -> tuple[str | None, dict | None]:
    """Locate a slot by its id.

    Args:
        slot_id: The slot to find.

    Returns:
        A (date, slot) pair, or (None, None) when there is no such slot.
    """
    for day, slots in AVAILABILITY.items():
        for slot in slots:
            if slot["slot_id"] == slot_id:
                return day, slot
    return None, None


def book_appointment(date_of_birth: str, code_last_four: str, slot_id: str) -> dict:
    """Reserve a slot pending the caller's spoken confirmation.

    This deliberately does not book anything. It validates, stashes the
    request under a token, and hands back a sentence for the agent to read
    aloud. Only confirm_booking writes, because the model -- not this code --
    decides when a function gets called, and a prompt is a request rather than
    a guarantee.

    Args:
        date_of_birth: The caller's date of birth, as YYYY-MM-DD.
        code_last_four: Last 4 digits of their confirmation code.
        slot_id: A slot_id returned by check_availability.

    Returns:
        A pending_token and a read_back to confirm, or a graceful miss.
    """
    patient = PATIENTS.get(f"{date_of_birth}:{str(code_last_four)[-4:]}")
    if patient is None:
        return {"found": False, "message": "I could not find a patient with that date of birth and code."}

    day, slot = _find_slot(slot_id)
    if day is None or slot is None:
        return {"found": False, "message": "That is not a slot I can offer."}
    if slot_id in BOOKED:
        return {"found": False, "message": "That slot has already been taken."}

    token = f"T-{slot_id}-{str(code_last_four)[-4:]}"
    read_back = f"{spoken_date(day)} at {spoken_time(slot['time'])} with {slot['provider']}"
    PENDING[token] = {
        "slot_id": slot_id,
        "patient_key": f"{date_of_birth}:{str(code_last_four)[-4:]}",
        "read_back": read_back,
    }
    return {"confirmed": False, "pending_token": token, "read_back": read_back}


def confirm_booking(pending_token: str) -> dict:
    """Commit a reservation the caller has agreed to out loud.

    Popping the token is what makes this idempotent: the caller says yes
    twice, or the model calls twice, and the appointment is still booked once.

    Args:
        pending_token: The token returned by book_appointment.

    Returns:
        The committed booking, or a graceful refusal.
    """
    pending = PENDING.pop(pending_token, None)
    if pending is None:
        return {"booked": False, "message": "I do not have a booking waiting on confirmation."}

    BOOKED[pending["slot_id"]] = pending["patient_key"]
    return {"booked": True, "slot_id": pending["slot_id"], "read_back": pending["read_back"]}


def find_appointment(date_of_birth: str, code_last_four: str) -> dict:
    """Return only the three fields the agent is allowed to say out loud.

    The record this reads from carries a full date of birth, a full
    confirmation code, a phone number, and a visit type that names a medical
    condition. None of those are returned. The prompt also forbids speaking
    them, but the prompt is backup: this is the layer that makes it
    impossible.

    Args:
        date_of_birth: The caller's date of birth, as YYYY-MM-DD.
        code_last_four: Last 4 digits of their confirmation code.

    Returns:
        The caller's first name and their next appointment's date, time, and
        provider -- or a graceful failure to verify.
    """
    patient = PATIENTS.get(f"{date_of_birth}:{str(code_last_four)[-4:]}")
    if patient is None:
        return {"verified": False, "message": "I could not verify a patient with that date of birth and code."}

    appointment = patient["next_appointment"]
    return {
        "verified": True,
        "first_name": patient["first_name"],
        "next_appointment": {
            "date": spoken_date(appointment["date"]),
            "time": spoken_time(appointment["time"]),
            "provider": appointment["provider"],
        },
    }


def transfer_to_human(reason: str) -> dict:
    """Hand the call to clinic staff.

    In production this bridges the call. Here it reports what it would do, so
    you can assert on the action rather than on the agent claiming to take it.

    Args:
        reason: Why the call is being transferred.

    Returns:
        A confirmation for the agent to read out.
    """
    print(f">> TRANSFER TO STAFF: {reason}")
    return {"transferred": True, "message": "Connecting you to a member of our staff now."}


# Maps the function names advertised in FUNCTIONS to the Python that runs
# them. The name string is the only thing joining the two.
FUNCTION_HANDLERS = {
    "check_availability": check_availability,
    "book_appointment": book_appointment,
    "confirm_booking": confirm_booking,
    "find_appointment": find_appointment,
    "transfer_to_human": transfer_to_human,
}

# What the agent is told it can call. Advertising only: the LLM decides
# *whether* to call, this file decides *what happens* when it does. These
# declarations and FUNCTION_HANDLERS never reference each other -- the name
# string is the only thing joining them.
FUNCTIONS = [
    ThinkSettingsV1FunctionsItem(
        name="check_availability",
        description=(
            "List open appointment slots on a given date. Use this whenever "
            "the caller asks what is available, or wants to book or move an "
            "appointment. Dates are ISO format, e.g. 2026-10-08."
        ),
        parameters={  # plain JSON Schema, as the LLM's tool API expects
            "type": "object",
            "properties": {
                "date_wanted": {
                    "type": "string",
                    "description": "The date to check, as YYYY-MM-DD.",
                },
                "visit_type": {
                    "type": "string",
                    "description": "Optional kind of visit, e.g. 'follow-up'.",
                },
            },
            "required": ["date_wanted"],
        },
    ),
    ThinkSettingsV1FunctionsItem(
        name="book_appointment",
        description=(
            "Reserve a slot for a caller, pending their spoken confirmation. "
            "This does NOT book the appointment -- it returns a read_back "
            "string and a pending_token. Say the read_back to the caller, "
            "wait for a clear yes, then call confirm_booking with the token."
        ),
        parameters={
            "type": "object",
            "properties": {
                "date_of_birth": {
                    "type": "string",
                    "description": "The caller's date of birth, as YYYY-MM-DD.",
                },
                "code_last_four": {
                    "type": "string",
                    "description": "The last 4 digits of their confirmation code.",
                },
                "slot_id": {
                    "type": "string",
                    "description": "The slot_id returned by check_availability.",
                },
            },
            "required": ["date_of_birth", "code_last_four", "slot_id"],
        },
    ),
    ThinkSettingsV1FunctionsItem(
        name="confirm_booking",
        description=(
            "Commit a pending appointment after the caller has said yes to "
            "the read_back. Call this ONLY after an explicit spoken "
            "confirmation. Never call it in the same turn as "
            "book_appointment."
        ),
        parameters={
            "type": "object",
            "properties": {
                "pending_token": {
                    "type": "string",
                    "description": "The pending_token from book_appointment.",
                },
            },
            "required": ["pending_token"],
        },
    ),
    ThinkSettingsV1FunctionsItem(
        name="find_appointment",
        description=(
            "Look up the caller's existing appointment. Requires their date "
            "of birth and the last four digits of their confirmation code. "
            "Use this when the caller asks about an appointment they already "
            "have."
        ),
        parameters={
            "type": "object",
            "properties": {
                "date_of_birth": {
                    "type": "string",
                    "description": "The caller's date of birth, as YYYY-MM-DD.",
                },
                "code_last_four": {
                    "type": "string",
                    "description": "The last 4 digits of their confirmation code.",
                },
            },
            "required": ["date_of_birth", "code_last_four"],
        },
    ),

    ThinkSettingsV1FunctionsItem(
        name="transfer_to_human",
        description=(
            "Call this to transfer the caller to a member of clinic staff. "
            "You MUST call this function -- saying you will transfer is "
            "not transferring. "
            "Call it whenever the caller asks for a person, becomes "
            "distressed, or asks anything clinical, including questions "
            "about medication. Call it before you say anything about a "
            "transfer, then say the message it returns. Do not answer "
            "clinical questions yourself. A medical emergency is the "
            "exception: tell the caller to hang up and dial 911 rather "
            "than transferring them."
        ),
        parameters={
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why the call is being transferred.",
                },
            },
            "required": ["reason"],
        },
    ),
]


def todays_date() -> str:
    """Return today's date in this scenario, the way the agent should say it.

    Fixed on purpose, not date.today(). The appointments and open slots in
    this file are fixed to October 2026, so a real date would eventually put
    every one of them in the past. Leaving the date out is worse: the model
    has no calendar, and guesses the year itself when it fills in a date --
    which is how "October the eighth" becomes a lookup in 2023.

    Returns:
        A date a few days before the clinic's first appointment.
    """
    return "Monday, September 28th, 2026"


SETTINGS = AgentV1Settings(
    #: ---- TODO (Step 9.3b): Uncomment -- tag the session.
    #: A list of strings you choose, attached to the request, so you can
    #: separate one deployment's traffic from another's later. They travel
    #: with the session, alongside the request_id you print in TODO 9.3a.
    # tags=["northwind", "module-9"],
    audio=AgentV1SettingsAudio(
        input=AgentV1SettingsAudioInput(encoding="linear16", sample_rate=SAMPLE_RATE),
        output=AgentV1SettingsAudioOutput(encoding="linear16", sample_rate=SAMPLE_RATE),
    ),
    agent=AgentV1SettingsAgent(
        # Flux is Deepgram's conversational speech-to-text model, built for
        # voice agents. The "v2" provider version routes the agent to the v2
        # Listen backend (wss://api.deepgram.com/v2/listen), where the flux
        # models live. Turn detection is part of the model, so the thresholds
        # are configured here.
        listen=AgentV1SettingsAgentContextListen(
            provider=AgentV1SettingsAgentContextListenProvider_V2(
                type="deepgram",
                model="flux-general-en",  # Deepgram's general-purpose English voice agent model. Use flux-general-multi for auto-detection. See: https://developers.deepgram.com/docs/flux/language-prompting
                eot_threshold=EOT_THRESHOLD,  # Valid 0.5-1.0. Raise it to stop the agent cutting people off mid-thought, lower it for snappier replies at the cost of false turn ends.
                eot_timeout_ms=EOT_TIMEOUT_MS,  # Valid 500-60000. Hard ceiling: end the turn after this much silence no matter what the score says.
                keyterms=KEYTERMS,  # Bias recognition toward the words this clinic repeats all day.
            ),
        ),
        think=ThinkSettingsV1(
            provider=ThinkSettingsV1Provider_OpenAi(
                type="open_ai",
                model="gpt-4o-mini",
                temperature=0.3,  # An agent reading back a date of birth should read it back the same way twice.
            ),
            # The prompt is prepended to every user turn before it reaches the
            # LLM. It is the agent's standing instructions -- personality, job,
            # and boundaries. Keep it short: every token here is re-sent on
            # every turn, and long prompts slow the first reply.
            functions=FUNCTIONS,
            prompt=(
                "You are the patient-access agent for Northwind Clinic. You help "
                "callers check, book, and move appointments.\n"
                f"Today is {todays_date()}.\n"
                "\n"
                "HOW TO SPEAK:\n"
                "- You are being heard, not read. Never use markdown, bullet "
                "points, or emoji.\n"
                "- Keep replies to one or two sentences, and ask one question at "
                "a time.\n"
                "- Say a date with its weekday ('Thursday, October 8th') and a "
                "time in words ('nine thirty in the morning').\n"
                "- If you do not know something, say so plainly. Never guess.\n"
                "\n"
                "If the caller describes a medical emergency, tell them to hang "
                "up and call 911 immediately.\n"
                "\n"
                "NUMERIC DISCIPLINE:\n"
                "- When the caller gives you a date of birth or confirmation "
                "code digits, read them back one digit at a time and wait for "
                "a yes before acting.\n"
                "- NEVER invent an appointment, a time, or a confirmation "
                "code. If you do not have it, call a function or say you "
                "cannot find it.\n"
                "\n"
                "Use check_availability to find open slots. To book, call "
                "book_appointment, say the read_back it returns, and call "
                "confirm_booking only after the caller says yes. Ask for the "
                "date of birth and the last four digits of the confirmation "
                "code first."
                "\n"
                "\n"
                "PRIVACY:\n"
                "- Never read a full confirmation code, a full date of birth, "
                "or a phone number aloud. Refer to the code by its last four "
                "digits only.\n"
                "- Never state a diagnosis, a medication, or a reason for a "
                "visit. You may say the appointment type only if the caller "
                "says it first.\n"
                "- If the caller asks anything clinical, or asks for a person, "
                "call transfer_to_human instead of answering."
            ),
        ),
        # Flux TTS is Deepgram's streaming, turn-based voice engine built for
        # voice agents. The "flux-" model prefix routes the agent to the v2
        # Speak backend (wss://api.deepgram.com/v2/speak) automatically.
        speak=SpeakSettingsV1(
            provider=SpeakSettingsV1Provider_Deepgram(
                type="deepgram",
                model="flux-alexis-en",
            ),
        ),
        # The agent's first utterance, spoken as soon as settings are applied.
        # It is added to the conversation history, so the LLM knows it already
        # said this and will not repeat itself on the first real turn.
        greeting=(
            "Thank you for calling Northwind Clinic. To look up an appointment "
            "I'll need your date of birth and the last four digits of your "
            "confirmation code. How can I help?"
        ),
    ),
)


def handle_function_call(agent: AgentHandle, message: object) -> None:
    """Run every function the agent asked for and return the results.

    The agent is mid-turn and blocked on these responses, so failures are
    reported back as the function's result rather than raised. A raised
    exception would escape into the SDK's receive loop, surface as
    EventType.ERROR, and drop the call.

    This also runs on the receive loop -- the same thread delivering audio --
    so a slow handler stalls playback for the whole conversation.

    Args:
        agent: The connected agent, used to send each response.
        message: The FunctionCallRequest, carrying a list of calls.
    """
    for call in getattr(message, "functions", []) or []:
        name = getattr(call, "name", "")
        arguments = getattr(call, "arguments", "") or "{}"
        print(f">> Function call: {name}({arguments})")

        handler = FUNCTION_HANDLERS.get(name)
        if handler is None:
            result = {"error": f"No function named '{name}' is available."}
        else:
            try:
                result = handler(**json.loads(arguments))
            except Exception as error:  # noqa: BLE001 -- never let this reach the receive loop
                result = {"error": f"{name} failed: {error}"}

        print(f">> Function result: {json.dumps(result)}")
        agent.send_function_call_response(
            AgentV1SendFunctionCallResponse(
                id=getattr(call, "id", ""),
                name=name,
                # content is a string on the wire; the handlers return dicts.
                content=json.dumps(result),
            ),
        )


def on_message(agent: AgentHandle, player: Player, message: object) -> None:
    """Handle one inbound frame from the agent.

    Unrecognized message types fall through to a plain print so that new server
    events stay visible rather than being silently dropped.

    Args:
        agent: The connected agent, used to reply to function calls.
        player: Where audio is played. send() queues a chunk; clear() throws
            away whatever is queued but not yet heard.
        message: Either raw bytes of Flux TTS audio, or a decoded model whose
            "type" attribute names the event.
    """
    if isinstance(message, bytes):
        player.send(message)
        return

    message_type = getattr(message, "type", "Unknown")

    if message_type == "SettingsApplied":
        print(">> Settings applied")
    #: ---- TODO (Step 9.3a): Uncomment -- capture the identifier ----------
    #: Welcome is the first frame the server sends, and it carries a
    #: request_id. Uncomment the branch that prints it:
    #:
    # elif message_type == "Welcome":
    #     request_id = getattr(message, "request_id", None)
    #     print(f">> request_id: {request_id}")
    #:
    #: That string is how you find this exact call again -- in your own logs,
    #: and when you ask Deepgram about it. Log it on every session, alongside
    #: whatever your system calls the caller. A latency complaint you cannot
    #: tie to a specific request is a complaint you cannot investigate.
    #:
    #: The companion to it is `tags` on Settings, which is TODO 9.3b at the
    #: top of SETTINGS.
    #: ----------------------------------------------------------------------
    elif message_type == "ConversationText":
        role = getattr(message, "role", "unknown")
        content = getattr(message, "content", "")
        print(f"[{role}] {content}")
    elif message_type == "UserStartedSpeaking":
        # Flux detected start-of-turn, so the agent has stopped sending audio --
        # but whatever it already sent is still queued, on this side of the
        # network and in the browser, and would keep talking over the user.
        player.clear()
        print(">> User started speaking (barge-in: playback cleared)")
    elif message_type == "AgentThinking":
        print(">> Agent thinking...")
    elif message_type == "AgentStartedSpeaking":
        print(">> Agent started speaking")
    elif message_type == "AgentAudioDone":
        print(">> Agent finished speaking")
    elif message_type == "FunctionCallRequest":
        handle_function_call(agent, message)
    elif message_type == "LatencyReport":
        #: ---- TODO (Step 9.1): Uncomment -- measure before you tune.
        #: total_latency is end-of-utterance to first audio byte -- the exact
        #: number the dials in TODO 9.2 move, and the only honest way to tell
        #: whether a change helped. Everything else is impression. Uncomment
        #: these three lines, then delete the `pass` right below them: it only
        #: held the branch open while it was empty.
        # total = getattr(message, "total_latency", None)
        # if total is not None:
        #     print(f">> Latency: {total:.2f}s")
        pass
        #:
        #: These reports arrive in a STREAM, not once per turn. A single
        #: exchange produced 36 of them in testing, and exactly one carried
        #: total_latency; the rest were empty or held only a deprecated
        #: stt_latency of 0.0. That is why the None check above is not
        #: decoration -- it is the thing that turns 36 messages into the one
        #: line you actually want.
        #:
        #: The report also defines ttt_token_latency, ttt_text_latency,
        #: ttt_tool_latency, ttt_thinking_latency, and tts_latency. Every
        #: field is optional and absent -- not zero -- when it does not
        #: apply. In testing, total_latency, tts_latency, ttt_text_latency
        #: and ttt_token_latency were populated on every turn; ttt_tool_latency
        #: only on turns that called a function; ttt_thinking_latency never.
        #: Read whatever you get, and do not build a dashboard that assumes a
        #: field will be there.
        #:
        #: Note you never asked for this report. It arrives whether you handle
        #: it or not -- you have been discarding it since Module 3.
        #: ------------------------------------------------------------------
    elif message_type == "Error":
        code = getattr(message, "code", "unknown")
        description = getattr(message, "description", "unknown error")
        print(f">> Agent error: {code} - {description}")
    elif message_type == "Warning":
        # Non-fatal, and the place a deferred failure shows up -- a bad voice
        # name passes the handshake and warns here when the agent first tries
        # to speak with it. A threshold outside its valid range is different:
        # it fails the handshake, through the Error branch above.
        code = getattr(message, "code", "unknown")
        description = getattr(message, "description", "unknown warning")
        print(f">> Agent warning: {code} - {description}")
    else:
        print(f">> {message_type}")


def on_media(agent: AgentHandle, audio: bytes) -> None:
    """Forward one captured chunk of microphone audio to the agent.

    Nothing here inspects the audio -- Flux decides where turns begin and end
    server-side, so there is no client-side voice activity detection to run.

    Args:
        agent: The connected agent.
        audio: One 80 ms chunk of linear16 PCM from the microphone.
    """
    agent.send_media(audio)


def main() -> None:
    """Serve the page and run the agent until interrupted."""
    bridge.run(settings=SETTINGS, on_message=on_message, on_media=on_media)


if __name__ == "__main__":
    main()
