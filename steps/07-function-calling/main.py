"""Module 7 - Function calling.

Runs exactly as Module 6 left it: the Northwind agent, with its voice rules and
its refusal to invent things.

Your job here is to give it something real to know. Right now it is honest and
useless -- it will tell a caller it cannot see their appointment, which is true
and no help at all. You will advertise three functions in the agent's settings,
handle the FunctionCallRequest the agent sends when the LLM decides to use one,
and send the result back.

Two of those functions are read-only. The third books an appointment, which
cannot be undone, so it does not act until the caller has said yes to a
read-back. That split -- safe to call, versus safe only after confirmation --
is the part worth carrying to your own projects.

Look for the "TODO (Step 7.x)" blocks below and work through them in order.
Inside them, "#:" marks the instructions and everything else is code, commented
out at the indentation it belongs at: select those lines and press Cmd+/
(Ctrl+/ on Windows and Linux) to uncomment them where they sit.

Run it with:  uv run steps/07-function-calling/main.py
"""

#: ---- TODO (Step 7.1a): Uncomment -- json parses the LLM's arguments and
#: serializes your results; date lets spoken_date work out the weekday.
# import json
# from datetime import date

from deepgram.agent.v1.types import (
    #: ---- TODO (Step 7.1b): Uncomment -- the reply you send after a function runs.
    # AgentV1SendFunctionCallResponse,
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

#: ---- TODO (Step 7.1c): Uncomment -- the type each advertised function is built from.
# from deepgram.types.think_settings_v1functions_item import ThinkSettingsV1FunctionsItem
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
# how long silence may run. Module 9 is where you move them.
EOT_THRESHOLD = 0.7  # Valid 0.5-1.0. Raise it to stop the agent cutting people off mid-thought, lower it for snappier replies at the cost of false turn ends.
EOT_TIMEOUT_MS = 5000  # Valid 500-60000. Hard ceiling: end the turn after this much silence, whatever the score says.

# Words this agent hears all day. Flux biases recognition toward them, which is
# the cheapest accuracy fix available for a domain-specific agent. Module 8
# takes this list apart and shows you what it is actually worth.
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

#: ---- TODO (Step 7.2): Uncomment the functions ----------------------------
#: First, the data the agent answers from. SYNTHETIC -- in production these
#: bodies call the clinic's scheduling system, server-side, behind its own
#: auth. Two patients, keyed by date of birth and the last four digits of a
#: confirmation code, because that is the pair the caller can say out loud:
#:
# PATIENTS = {
#     "1979-04-12:4821": {
#         "first_name": "Dana",
#         "date_of_birth": "1979-04-12",
#         "confirmation_code": "NWC-000-4821",
#         "phone": "555-0147",
#         "next_appointment": {
#             "date": "2026-10-01",
#             "time": "9:30 AM",
#             "provider": "Dr. Nwosu",
#             "type": "A1C follow-up",
#             "location": "Northwind Clinic, Suite 200",
#         },
#     },
#     "1965-11-20:9007": {
#         "first_name": "James",
#         "date_of_birth": "1965-11-20",
#         "confirmation_code": "NWC-000-9007",
#         "phone": "555-0192",
#         "next_appointment": {
#             "date": "2026-10-03",
#             "time": "2:00 PM",
#             "provider": "Dr. Bergstrom",
#             "type": "Echocardiogram",
#             "location": "Northwind Cardiology, 3rd floor",
#         },
#     },
# }
#:
#: And the slots it is allowed to offer:
#:
# AVAILABILITY = {
#     "2026-10-08": [
#         {"slot_id": "S-1041", "time": "9:00 AM", "provider": "Dr. Nwosu"},
#         {"slot_id": "S-1042", "time": "11:30 AM", "provider": "Dr. Nwosu"},
#         {"slot_id": "S-1043", "time": "3:15 PM", "provider": "Dr. Bergstrom"},
#     ],
#     "2026-10-09": [
#         {"slot_id": "S-1055", "time": "8:45 AM", "provider": "Dr. Bergstrom"},
#         {"slot_id": "S-1056", "time": "1:00 PM", "provider": "Dr. Nwosu"},
#     ],
# }
#:
#: Bookings the caller has agreed to, and bookings still waiting on a yes. Both
#: live in memory, which is fine for a lab and wrong for production -- see
#: "Going further" in LAB.md.
#:
# BOOKED: dict = {}
# PENDING: dict = {}
#:
#:
#: Then two formatting helpers. Format for the ear HERE, not in the prompt:
#: hand the LLM "Thursday, October 8th" and it reads it back correctly; hand it
#: "2026-10-08" and you spend prompt tokens teaching it to say dates.
#:
#: A date is never spoken without its weekday -- that is the caller's free
#: second chance to catch a mistake. "9:30 AM" becomes "nine thirty in the
#: morning", because a caller hears "nine thirty A M" as three separate things.
#:
# _MONTHS = [
#     "January", "February", "March", "April", "May", "June",
#     "July", "August", "September", "October", "November", "December",
# ]
# _ORDINAL = {1: "st", 2: "nd", 3: "rd", 21: "st", 22: "nd", 23: "rd", 31: "st"}
# _HOURS = [
#     "twelve", "one", "two", "three", "four", "five",
#     "six", "seven", "eight", "nine", "ten", "eleven",
# ]
# _MINUTES = {15: "fifteen", 30: "thirty", 45: "forty-five"}
#
#
# def spoken_date(iso: str) -> str:
#     """Format an ISO date the way a person says it, weekday included.
#
#     The weekday is not decoration. It is the caller's free second chance to
#     catch a date they misheard, and it costs one word.
#
#     Args:
#         iso: A date as YYYY-MM-DD.
#
#     Returns:
#         The date as, for example, "Thursday, October 8th".
#     """
#     day = date.fromisoformat(iso)
#     return f"{day.strftime('%A')}, {_MONTHS[day.month - 1]} {day.day}{_ORDINAL.get(day.day, 'th')}"
#
#
# def spoken_time(clock: str) -> str:
#     """Format a clock time as words.
#
#     Args:
#         clock: A time as "9:30 AM".
#
#     Returns:
#         The time as, for example, "nine thirty in the morning".
#     """
#     hhmm, meridiem = clock.split()
#     hour, minute = (int(part) for part in hhmm.split(":"))
#     part_of_day = "in the morning" if meridiem.upper() == "AM" else "in the afternoon"
#     if minute == 0:
#         return f"{_HOURS[hour % 12]} o'clock {part_of_day}"
#     return f"{_HOURS[hour % 12]} {_MINUTES.get(minute, str(minute))} {part_of_day}"
#:
#: Then the three handlers. Every miss RETURNS, it never raises:
#:
#:     {"found": False, "message": "I could not find a patient with that date of birth and code."}
#:
#: The agent turns that into a sentence. An exception leaves the caller
#: listening to silence -- and worse, it escapes into the SDK's receive loop
#: and drops the call, exactly as you saw in Module 3.
#:
#: check_availability is read-only. It returns the slots with their times
#: ALREADY formatted, so the model has nothing left to paraphrase. _find_slot
#: below it is a small lookup book_appointment uses.
#:
# def check_availability(date_wanted: str, visit_type: str = "") -> dict:
#     """List open slots on one date, formatted for speech.
#
#     Read-only, so the agent may call it as often as it likes.
#
#     Args:
#         date_wanted: The date to check, as YYYY-MM-DD.
#         visit_type: Optional kind of visit. Accepted and ignored here; a real
#             scheduler would filter on it.
#
#     Returns:
#         The open slots with times already spoken-ready, or a graceful miss.
#     """
#     del visit_type
#     slots = AVAILABILITY.get(date_wanted)
#     if not slots:
#         return {"found": False, "message": f"There is nothing open on {spoken_date(date_wanted)}."}
#
#     return {
#         "found": True,
#         "date": spoken_date(date_wanted),
#         "slots": [
#             {"slot_id": slot["slot_id"], "time": spoken_time(slot["time"]), "provider": slot["provider"]}
#             for slot in slots
#             if slot["slot_id"] not in BOOKED
#         ],
#     }
#
#
# def _find_slot(slot_id: str) -> tuple[str | None, dict | None]:
#     """Locate a slot by its id.
#
#     Args:
#         slot_id: The slot to find.
#
#     Returns:
#         A (date, slot) pair, or (None, None) when there is no such slot.
#     """
#     for day, slots in AVAILABILITY.items():
#         for slot in slots:
#             if slot["slot_id"] == slot_id:
#                 return day, slot
#     return None, None
#:
#: book_appointment is the interesting one, because booking twice is worse than
#: not booking at all. It does NOT book. It validates, stashes the request in
#: PENDING under a token, and returns a read-back for the agent to say.
#:
# def book_appointment(date_of_birth: str, code_last_four: str, slot_id: str) -> dict:
#     """Reserve a slot pending the caller's spoken confirmation.
#
#     This deliberately does not book anything. It validates, stashes the
#     request under a token, and hands back a sentence for the agent to read
#     aloud. Only confirm_booking writes, because the model -- not this code --
#     decides when a function gets called, and a prompt is a request rather than
#     a guarantee.
#
#     Args:
#         date_of_birth: The caller's date of birth, as YYYY-MM-DD.
#         code_last_four: Last 4 digits of their confirmation code.
#         slot_id: A slot_id returned by check_availability.
#
#     Returns:
#         A pending_token and a read_back to confirm, or a graceful miss.
#     """
#     patient = PATIENTS.get(f"{date_of_birth}:{str(code_last_four)[-4:]}")
#     if patient is None:
#         return {"found": False, "message": "I could not find a patient with that date of birth and code."}
#
#     day, slot = _find_slot(slot_id)
#     if day is None or slot is None:
#         return {"found": False, "message": "That is not a slot I can offer."}
#     if slot_id in BOOKED:
#         return {"found": False, "message": "That slot has already been taken."}
#
#     token = f"T-{slot_id}-{str(code_last_four)[-4:]}"
#     read_back = f"{spoken_date(day)} at {spoken_time(slot['time'])} with {slot['provider']}"
#     PENDING[token] = {
#         "slot_id": slot_id,
#         "patient_key": f"{date_of_birth}:{str(code_last_four)[-4:]}",
#         "read_back": read_back,
#     }
#     return {"confirmed": False, "pending_token": token, "read_back": read_back}
#:
#: confirm_booking is the only thing that writes. It pops the token out of
#: PENDING and refuses an unknown or already-used one. Popping is what makes
#: it idempotent: the caller says "yes" twice, or the model calls it twice, and
#: the appointment is still booked once.
#:
# def confirm_booking(pending_token: str) -> dict:
#     """Commit a reservation the caller has agreed to out loud.
#
#     Popping the token is what makes this idempotent: the caller says yes
#     twice, or the model calls twice, and the appointment is still booked once.
#
#     Args:
#         pending_token: The token returned by book_appointment.
#
#     Returns:
#         The committed booking, or a graceful refusal.
#     """
#     pending = PENDING.pop(pending_token, None)
#     if pending is None:
#         return {"booked": False, "message": "I do not have a booking waiting on confirmation."}
#
#     BOOKED[pending["slot_id"]] = pending["patient_key"]
#     return {"booked": True, "slot_id": pending["slot_id"], "read_back": pending["read_back"]}
#:
#: Then map the advertised names to the callables:
#:
# FUNCTION_HANDLERS = {
#     "check_availability": check_availability,
#     "book_appointment": book_appointment,
#     "confirm_booking": confirm_booking,
# }
#: --------------------------------------------------------------------------

#: ---- TODO (Step 7.3): Advertise the functions ----------------------------
#: Build the list the agent is told about. This is advertising only: the LLM
#: decides *whether* to call, your code decides *what happens* when it does.
#:
#: These declarations and the handlers above never reference each other. The
#: name string is the only thing joining them, which is worth remembering the
#: first time you rename one and not the other.
#:
# FUNCTIONS = [
#     ThinkSettingsV1FunctionsItem(
#         name="check_availability",
#         description=(
#             "List open appointment slots on a given date. Use this whenever "
#             "the caller asks what is available, or wants to book or move an "
#             "appointment. Dates are ISO format, e.g. 2026-10-08."
#         ),
#         parameters={  # plain JSON Schema, as the LLM's tool API expects
#             "type": "object",
#             "properties": {
#                 "date_wanted": {
#                     "type": "string",
#                     "description": "The date to check, as YYYY-MM-DD.",
#                 },
#                 "visit_type": {
#                     "type": "string",
#                     "description": "Optional kind of visit, e.g. 'follow-up'.",
#                 },
#             },
#             "required": ["date_wanted"],
#         },
#     ),
#     ThinkSettingsV1FunctionsItem(
#         name="book_appointment",
#         description=(
#             "Reserve a slot for a caller, pending their spoken confirmation. "
#             "This does NOT book the appointment -- it returns a read_back "
#             "string and a pending_token. Say the read_back to the caller, "
#             "wait for a clear yes, then call confirm_booking with the token."
#         ),
#         parameters={
#             "type": "object",
#             "properties": {
#                 "date_of_birth": {
#                     "type": "string",
#                     "description": "The caller's date of birth, as YYYY-MM-DD.",
#                 },
#                 "code_last_four": {
#                     "type": "string",
#                     "description": "The last 4 digits of their confirmation code.",
#                 },
#                 "slot_id": {
#                     "type": "string",
#                     "description": "The slot_id returned by check_availability.",
#                 },
#             },
#             "required": ["date_of_birth", "code_last_four", "slot_id"],
#         },
#     ),
#     ThinkSettingsV1FunctionsItem(
#         name="confirm_booking",
#         description=(
#             "Commit a pending appointment after the caller has said yes to "
#             "the read_back. Call this ONLY after an explicit spoken "
#             "confirmation. Never call it in the same turn as "
#             "book_appointment."
#         ),
#         parameters={
#             "type": "object",
#             "properties": {
#                 "pending_token": {
#                     "type": "string",
#                     "description": "The pending_token from book_appointment.",
#                 },
#             },
#             "required": ["pending_token"],
#         },
#     ),
# ]
#:
#: The description IS the prompt. It is the only thing the LLM reads when
#: deciding to call, so spell out *when* to use it, not just what it does --
#: and for anything irreversible, spell out what must happen first. Read
#: book_appointment's description again: most of it is a sequencing rule.
#:
#: Note what is missing from all three: "endpoint". Leaving it unset is what
#: marks a function client-side -- that is why Deepgram sends the call down the
#: socket to you instead of calling an HTTP endpoint itself.
#: --------------------------------------------------------------------------


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
                #: ---- TODO (Step 7.4a): Uncomment -- bias Flux toward the words this clinic says all day.
                # keyterms=KEYTERMS,
            ),
        ),
        think=ThinkSettingsV1(
            provider=ThinkSettingsV1Provider_OpenAi(
                type="open_ai",
                model="gpt-4o-mini",
                #: ---- TODO (Step 7.4b): Comment out 0.7, and uncomment 0.3 below it.
                #: An agent reading back a date of birth should read it back the
                #: same way twice.
                temperature=0.7,
                # temperature=0.3,
            ),
            # The prompt is prepended to every user turn before it reaches the
            # LLM. It is the agent's standing instructions -- personality, job,
            # and boundaries. Keep it short: every token here is re-sent on
            # every turn, and long prompts slow the first reply.
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
                "up and call 911 immediately."
                #: ---- TODO (Step 7.4c): Uncomment -- the rules that protect a number.
                #: This APPENDS to Module 6's prompt rather than replacing it: the
                #: voice rules above still hold. The NUMERIC DISCIPLINE header is
                #: worth keeping verbatim; it is the thing you will remember about
                #: this module in a year.
                # "\n"
                # "\n"
                # "NUMERIC DISCIPLINE:\n"
                # "- When the caller gives you a date of birth or confirmation "
                # "code digits, read them back one digit at a time and wait for "
                # "a yes before acting.\n"
                # "- NEVER invent an appointment, a time, or a confirmation "
                # "code. If you do not have it, call a function or say you "
                # "cannot find it.\n"
                # "\n"
                # "Use check_availability to find open slots. To book, call "
                # "book_appointment, say the read_back it returns, and call "
                # "confirm_booking only after the caller says yes. Ask for the "
                # "date of birth and the last four digits of the confirmation "
                # "code first."
                #:
                #: That last paragraph is a sequencing rule in prose, and the
                #: function descriptions say the same thing again. Belt and braces
                #: on purpose: the prompt is a request, and you want the model
                #: hearing the ordering from both directions.
            ),
            #: ---- TODO (Step 7.4d): Uncomment -- attach the functions you advertised.
            # functions=FUNCTIONS,
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
        #: ---- TODO (Step 7.4e): Comment out this greeting, and uncomment the
        #: one below it. The new one names what the agent will ask for, BEFORE
        #: the caller volunteers a full confirmation code -- or a diagnosis --
        #: out loud. A greeting is the cheapest privacy control you have. It
        #: costs one sentence and it steers the caller away from saying more
        #: than you need. Module 8 is where that idea gets teeth.
        greeting=(
            "Thank you for calling Northwind Clinic. I can help you check, book, "
            "or move an appointment. How can I help?"
        ),
        # greeting=(
        #     "Thank you for calling Northwind Clinic. To look up an "
        #     "appointment I'll need your date of birth and the last four "
        #     "digits of your confirmation code. How can I help?"
        # ),
    ),
)

#: ---- TODO (Step 7.5): Handle the call ------------------------------------
#: Uncomment handle_function_call. A FunctionCallRequest carries a "functions"
#: list, and each entry has .id, .name, and .arguments (a JSON *string*, not a
#: dict). For each one it looks the name up in FUNCTION_HANDLERS, calls it with
#: handler(**json.loads(arguments)), and sends the result back with json.dumps:
#: `content` goes over the wire as a string, and your handlers return dicts.
#:
#: Two things that will bite you:
#:
#:   * It catches exceptions and returns the error text as `content`. The agent
#:     is mid-turn and blocked waiting on you. A raised exception escapes into
#:     the SDK's receive loop, surfaces as EventType.ERROR, and drops the call.
#:
#:   * This runs on the SDK's receive loop -- the same thread delivering audio.
#:     A slow function stalls playback. Keep handlers fast, or hand the work to
#:     a thread and reply when it finishes. Routing audio through the browser
#:     does not change this: the bytes still pass through this thread on their
#:     way out.
#:
#: It prints the call and the result, so you can see what the LLM actually passed.
#:
# def handle_function_call(agent: AgentHandle, message: object) -> None:
#     """Run every function the agent asked for and return the results.
#
#     The agent is mid-turn and blocked on these responses, so failures are
#     reported back as the function's result rather than raised. A raised
#     exception would escape into the SDK's receive loop, surface as
#     EventType.ERROR, and drop the call.
#
#     This also runs on the receive loop -- the same thread delivering audio --
#     so a slow handler stalls playback for the whole conversation.
#
#     Args:
#         agent: The connected agent, used to send each response.
#         message: The FunctionCallRequest, carrying a list of calls.
#     """
#     for call in getattr(message, "functions", []) or []:
#         name = getattr(call, "name", "")
#         arguments = getattr(call, "arguments", "") or "{}"
#         print(f">> Function call: {name}({arguments})")
#
#         handler = FUNCTION_HANDLERS.get(name)
#         if handler is None:
#             result = {"error": f"No function named '{name}' is available."}
#         else:
#             try:
#                 result = handler(**json.loads(arguments))
#             except Exception as error:  # noqa: BLE001, RUF100 -- never let this reach the receive loop
#                 result = {"error": f"{name} failed: {error}"}
#
#         print(f">> Function result: {json.dumps(result)}")
#         agent.send_function_call_response(
#             AgentV1SendFunctionCallResponse(
#                 id=getattr(call, "id", ""),
#                 name=name,
#                 # content is a string on the wire; the handlers return dicts.
#                 content=json.dumps(result),
#             ),
#         )
#: --------------------------------------------------------------------------


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
    #: ---- TODO (Step 7.6): Dispatch the request ---------------------------
    #: Add a branch, above the LatencyReport one:
    #:
    # elif message_type == "FunctionCallRequest":
    #     handle_function_call(agent, message)
    #:
    #: Without it, the fallthrough at the bottom prints ">> FunctionCallRequest"
    #: and the agent waits forever for a reply that never comes -- a useful
    #: thing to see once on purpose.
    #: ----------------------------------------------------------------------
    elif message_type == "LatencyReport":
        # These arrive as a stream through the turn, and only one of them
        # carries total_latency. Printed raw, they bury the conversation --
        # Module 9 reduces the stream to one line, once there is a reason to
        # read it. The browser shows the number either way, on the right of the
        # activity line above the transcript.
        pass
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
