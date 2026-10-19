# /// script
# requires-python = ">=3.13"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Check the workshop steps for the ways they rot. Maintainers only.

Ten near-identical copies of main.py drift quietly. The failure that actually
embarrasses you live is a step whose answer key -- the next folder -- no longer
matches what its own TODOs asked for. This catches the mechanical half of that.

Run it after editing any step:

    uv run scripts/verify_steps.py

Checks, in order of how badly each one fails a room:

  1. Every step compiles.
  2. No "TODO (Step N.x)" marker survives into folder N+1. A marker that leaks
     means the answer key is not actually finished.
  3. Every step folder has a LAB.md, and 10-final has a README.md.
  4. Step 1's setup check names the same models Step 2 configures.
  5. Each step's growth over its predecessor is plausible -- a step that got
     *smaller* almost always means an edit landed in the wrong folder.
  6. No module asserts a factual claim a later module disproves.
  7. Every advertised function schema names parameters its handler accepts,
     and matches the signature course/SCENARIO.md publishes.
  8. ruff passes on all of them, using the config in pyproject.toml.

That list is orientation, not an inventory. The registry in main() is the
authoritative one, and it is longer.

What it deliberately does not check: whether the code in step N+1 is a correct
implementation of step N's TODOs. Nothing but reading it will tell you that.

It also does not check the teaching material -- video narration, the on-screen
cards, the module quizzes, and the badge knowledge check. Those live in the private
deepgram-essentials-course-teaching repo, whose tools/verify_teaching.py reads
this repo's course/modules.yml so module identity cannot drift between the two.
Run both after changing a module's identity, ordering, or exemptions.
"""

import re
import subprocess
import sys
from itertools import pairwise
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
STEPS = REPO / "steps"

# "TODO (Step 9.1)", "TODO (Step 5.1)", and "TODO (Step 6b.1a)" alike. The step
# group has to allow a letter suffix: with a bare (\d+) the marker "TODO
# (Step 6b.1a)" matched nothing at all, so a leaked 6b marker was invisible.
MARKER = re.compile(r"TODO \(Step (\d+[a-z]?)(?:\.\w+)?\)")

MANIFEST = REPO / "course" / "modules.yml"
SCENARIO = REPO / "course" / "SCENARIO.md"
CAPSTONE = REPO / "course" / "capstone"

# Course-era prose must not sound like a room with an instructor in it. The
# allowlist file carries the legitimate hits -- "out loud" is usually the agent
# speaking, not the attendee -- so this check can stay strict.
INSTRUCTOR_LANGUAGE = re.compile(
    r"\u23f8|instructor|facilitator|the room|everyone|go around|your neighbor|run of show|sync point|check in with",
    re.IGNORECASE,
)
ALLOWLIST = REPO / "course" / ".language-allow"

# Headings every module lab carries, in this order. Eleven hand-edited files
# drift apart without something asserting the shape.
REQUIRED_SECTIONS = (
    "**Goal:**",
    "## Start here",
    "## How it works",
    "## Do this",
    "## Verify",
    "## Checkpoint",
    "## Stuck?",
    "## Recap",
)

# A doc-only module (the overview, the reference agent) has nothing to run, so
# "Do this" and "Verify" would be theatre. It still owes a goal and a recap.
DOC_ONLY_SECTIONS = ("**Goal:**", "## Recap")

# Retired with Contoso Bank and Lakeside Family Health. Any survivor is a
# module that did not get the Northwind Clinic rewrite.
#
# Two patterns, not one. The prose names are case-insensitive. The identifiers
# are case-SENSITIVE on purpose: a case-insensitive "ACCOUNTS" also matches the
# English word, and "Deepgram applies $200 in credit to new accounts" is not a
# missed rewrite.
RETIRED_PROSE = re.compile(r"Contoso|Lakeside|phone banking", re.IGNORECASE)
RETIRED_IDENTIFIERS = re.compile(r"\bACCOUNTS\b|\blookup_balance\b|\blist_recent_transactions\b")

# The two files whose job is to discuss what was retired and what is out of
# scope. Exempt, or they report themselves forever.
SCENARIO_EXEMPT = {"course/SCENARIO.md", "course/DEFERRED.md"}

# Strings that must be byte-identical everywhere they appear, because folder
# N+1 is folder N finished. See course/SCENARIO.md.
CASCADE_DIRS = ("07-function-calling", "08-healthcare", "09-optimize", "10-final")

# Factual claims the course used to make and no longer stands behind. The
# expensive failure is a fact taught early, measured later, and never corrected
# where it was first stated: the learner reads the wrong version several times
# and writes code against it before meeting the right one.
#
# LatencyReport does not arrive once per turn. Module 9 measured 36 in a single
# exchange with exactly one carrying total_latency, which is what the None check
# in every step's handler is for. Nine files said otherwise before this existed,
# one of them a quiz that graded the wrong answer correct.
RETIRED_CLAIMS = re.compile(
    r"once per turn|one report per turn|per-turn timings|fires once",
    re.IGNORECASE,
)

# Module 9 is where that claim gets measured and refuted, so its files have to
# be free to state the wrong thing in order to correct it. Whole-folder scoping
# rather than the line-level course/.language-allow mechanism: line numbers
# inside a lab under active editing rot immediately.
CLAIM_EXEMPT_PREFIX = "steps/09-optimize/"

# Capabilities the course deliberately does not teach. The capstone may not ask
# for them; only course/DEFERRED.md may name them.
DEFERRED_SURFACE = re.compile(
    r"defer_until_eot|UpdatePrompt|InjectAgentMessage|InjectUserMessage|mulaw|telephony|/v2/listen",
    re.IGNORECASE,
)


def manifest() -> dict:
    """Load and return course/modules.yml.

    Returns:
        The parsed manifest.

    Raises:
        SystemExit: If the manifest is missing or will not parse.
    """
    if not MANIFEST.exists():
        print(f"Manifest not found at {MANIFEST.relative_to(REPO)}")
        sys.exit(1)
    try:
        return yaml.safe_load(MANIFEST.read_text())
    except yaml.YAMLError as error:
        print(f"Manifest will not parse: {error}")
        sys.exit(1)


def modules() -> list[dict]:
    """Return the module entries from the manifest, in course order.

    Returns:
        A list of module dicts.
    """
    return manifest()["modules"]


def standalone_names() -> set[str]:
    """Return step folders exempt from the growth check.

    Returns:
        A set of folder names.
    """
    return {m["step_dir"] for m in modules() if m.get("standalone")}


def optional_names() -> set[str]:
    """Return step folders that are detours rather than links in the chain.

    Returns:
        A set of folder names.
    """
    return {m["step_dir"] for m in modules() if m.get("optional")}


def step_dirs() -> list[Path]:
    """Return every step folder that ships runnable code, in workshop order.

    Returns:
        Sorted list of directories under steps/ that contain a main.py.
    """
    return sorted(d for d in STEPS.iterdir() if d.is_dir() and (d / "main.py").exists())


def all_step_dirs() -> list[Path]:
    """Return every step folder, including doc-only ones like 00-overview.

    Returns:
        Sorted list of directories under steps/.
    """
    return sorted(d for d in STEPS.iterdir() if d.is_dir())


def check_compiles(steps: list[Path]) -> list[str]:
    """Byte-compile every step's main.py.

    Args:
        steps: Step folders to check.

    Returns:
        A list of failure messages, empty when every file compiles.
    """
    failures = []
    for step in steps:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(step / "main.py")],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            failures.append(f"{step.name}/main.py does not compile:\n{result.stderr}")
    return failures


def check_marker_leakage(steps: list[Path]) -> list[str]:
    """Confirm each step's TODO markers are resolved by the following step.

    Args:
        steps: Step folders, in order.

    Returns:
        A list of failure messages, empty when no marker leaks forward.
    """
    failures = []
    for step, answer_key in pairwise(steps):
        own = {m.group(1) for m in MARKER.finditer((step / "main.py").read_text())}
        leaked = {m.group(1) for m in MARKER.finditer((answer_key / "main.py").read_text())}
        for number in sorted(own & leaked):
            failures.append(
                f"{answer_key.name}/main.py still contains 'TODO (Step {number})' "
                f"markers that {step.name} asks the attendee to resolve -- "
                f"the answer key is unfinished.",
            )
    return failures


def check_docs(steps: list[Path]) -> list[str]:
    """Confirm every step ships the document an attendee is told to open.

    Covers doc-only steps such as 00-overview, which have no main.py and so
    never reach the code checks.

    Args:
        steps: Step folders to check. Ignored -- every folder is inspected.

    Returns:
        A list of failure messages, empty when every doc exists.
    """
    del steps
    failures = []
    doc_names = {m["step_dir"]: m.get("doc_name", "LAB.md") for m in modules()}
    for step in all_step_dirs():
        wanted = doc_names.get(step.name, "LAB.md")
        if not (step / wanted).exists():
            failures.append(f"{step.name}/ is missing {wanted}")
    return failures


def check_lab_links(_steps: list[Path]) -> list[str]:
    """Confirm every relative link in a step doc points at a file that exists.

    A broken "Next:" link strands an attendee mid-workshop, which is the kind
    of thing nobody notices until it happens in a room.

    Returns:
        A list of failure messages, empty when every link resolves.
    """
    link = re.compile(r"\]\((?!https?:)([^)#]+)\)")
    failures = []
    docs = sorted(STEPS.glob("*/*.md")) + sorted((REPO / "course").rglob("*.md")) + [REPO / "README.md"]
    for doc in docs:
        for target in link.findall(doc.read_text()):
            if not (doc.parent / target).exists():
                failures.append(f"{doc.relative_to(REPO)} links to missing {target}")
    return failures


def check_setup_models(_steps: list[Path]) -> list[str]:
    """Confirm Step 1 checks the same models Step 2 configures.

    Step 1 opens the agent connection for real, so it names the three models
    itself rather than importing another step. That is the second place they
    are written down, and the failure it invites is a room whose setup check
    passes on models the workshop no longer uses.

    Returns:
        A list of failure messages, empty when the two agree.
    """
    setup = (STEPS / "01-setup" / "main.py").read_text()
    connect = (STEPS / "02-connect" / "main.py").read_text()

    failures = []
    for constant in ("LISTEN_MODEL", "THINK_MODEL", "SPEAK_MODEL"):
        match = re.search(rf'^{constant} = "([^"]+)"', setup, re.MULTILINE)
        if match is None:
            failures.append(f"01-setup/main.py no longer defines {constant}")
        elif f'model="{match.group(1)}"' not in connect:
            failures.append(
                f"01-setup/main.py checks {constant} = {match.group(1)!r}, which "
                f"02-connect/main.py does not configure. The setup check is "
                f"proving the wrong pipeline works.",
            )
    return failures


def check_growth(steps: list[Path]) -> list[str]:
    """Flag any step whose main.py shrank relative to the step before it.

    Each step adds to its predecessor, so line counts should climb. A drop
    almost always means an edit landed in the wrong folder.

    Args:
        steps: Step folders, in order.

    Returns:
        A list of failure messages, empty when every step grew or held steady.
    """
    standalone = standalone_names()
    failures = []
    for previous, step in pairwise(steps):
        if previous.name in standalone or step.name in standalone:
            continue
        before = len((previous / "main.py").read_text().splitlines())
        after = len((step / "main.py").read_text().splitlines())
        # Resolving a TODO block usually nets out shorter than the instructions
        # it replaces, so allow real slack -- this is a tripwire, not a metric.
        if after < before - 60:
            failures.append(
                f"{step.name}/main.py is {before - after} lines shorter than "
                f"{previous.name}/main.py. Did an edit land in the wrong folder?",
            )
    return failures


def check_lint() -> list[str]:
    """Run ruff over the steps, scripts, and the shared browser bridge.

    web/ is in the list deliberately. Attendees read it, and the repo's whole
    quality story is docstrings on everything -- letting the one folder nobody
    edits escape that is worse than the one-word diff.

    Returns:
        A list containing ruff's output when it fails, empty when it passes or
        ruff is unavailable.
    """
    try:
        result = subprocess.run(
            ["uvx", "ruff", "check", "steps", "scripts", "web"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("  (skipped: uvx not found)")
        return []

    if result.returncode != 0:
        return [result.stdout or result.stderr]
    return []


def check_manifest(_steps: list[Path]) -> list[str]:
    """Confirm the manifest and the steps/ folder agree about what exists.

    Returns:
        A list of failure messages, empty when they agree.
    """
    failures = []
    mods = modules()
    listed = [m["step_dir"] for m in mods]
    on_disk = {d.name for d in all_step_dirs()}

    for name in sorted(set(listed) - on_disk):
        failures.append(f"course/modules.yml lists step_dir {name!r}, which does not exist")
    for name in sorted(on_disk - set(listed)):
        failures.append(f"steps/{name}/ is not listed in course/modules.yml")

    seen_ids = [m["id"] for m in mods]
    for module_id in sorted({i for i in seen_ids if seen_ids.count(i) > 1}):
        failures.append(f"course/modules.yml uses module id {module_id!r} more than once")
    for name in sorted({n for n in listed if listed.count(n) > 1}):
        failures.append(f"course/modules.yml maps step_dir {name!r} to more than one module")

    for name in manifest().get("chain", []):
        if name not in on_disk:
            failures.append(f"course/modules.yml chain names {name!r}, which does not exist")
    return failures


def check_module_artifacts(_steps: list[Path]) -> list[str]:
    """Confirm every module ships the documents the course needs from it.

    A module owes a lab. Its quiz and video script live in the teaching repo,
    whose verifier checks them against the same manifest.

    Returns:
        A list of failure messages, empty when every artifact is present.
    """
    failures = []
    for module in modules():
        folder = STEPS / module["step_dir"]
        doc = module.get("doc_name", "LAB.md")
        if not (folder / doc).exists():
            failures.append(f"{module['id']} ({module['step_dir']}/) is missing {doc}")
    return failures


def check_lab_sections(_steps: list[Path]) -> list[str]:
    """Confirm every module lab carries the required headings, in order.

    Returns:
        A list of failure messages, empty when every lab matches the shape.
    """
    failures = []
    for module in modules():
        path = STEPS / module["step_dir"] / module.get("doc_name", "LAB.md")
        if not path.exists():
            continue
        text = path.read_text()
        where = path.relative_to(REPO)

        wanted = DOC_ONLY_SECTIONS if module.get("doc_only") else REQUIRED_SECTIONS
        positions = []
        for section in wanted:
            index = text.find(section)
            if index == -1:
                failures.append(f"{where} is missing the {section!r} section")
            else:
                positions.append((section, index))
        for (first, at_first), (second, at_second) in pairwise(positions):
            if at_first > at_second:
                failures.append(f"{where} has {second!r} before {first!r}")
    return failures


def check_no_instructor_language(_steps: list[Path]) -> list[str]:
    """Confirm no course prose still addresses a room with an instructor in it.

    Returns:
        A list of failure messages, empty when the prose reads as self-paced.
    """
    allowed = set()
    if ALLOWLIST.exists():
        allowed = {
            line.strip()
            for line in ALLOWLIST.read_text().splitlines()
            if line.strip() and not line.startswith("#")
        }

    docs = (
        sorted(STEPS.glob("*/*.md"))
        + sorted((REPO / "course").rglob("*.md"))
        + [REPO / "README.md"]
    )
    failures = []
    for doc in docs:
        if not doc.exists():
            continue
        for number, line in enumerate(doc.read_text().splitlines(), start=1):
            match = INSTRUCTOR_LANGUAGE.search(line)
            if match is None:
                continue
            location = f"{doc.relative_to(REPO)}:{number}"
            if location in allowed:
                continue
            failures.append(f"{location} reads as instructor-led ({match.group(0)!r}): {line.strip()[:70]}")
    return failures


def check_scenario_consistency(_steps: list[Path]) -> list[str]:
    """Confirm the Northwind Clinic rewrite landed, and landed identically.

    Two separate failures live here. A surviving Contoso or Lakeside string
    means a module was missed. A prompt or keyterm list that differs between
    the cascade folders means the answer keys have diverged, which a learner
    discovers as an agent that changes personality halfway through the course.

    Returns:
        A list of failure messages, empty when the scenario is uniform.
    """
    failures = []

    searchable = sorted(STEPS.glob("*/*.md")) + sorted(STEPS.glob("*/main.py"))
    searchable += sorted((REPO / "course").rglob("*.md")) + [REPO / "README.md"]
    for path in searchable:
        if not path.exists() or str(path.relative_to(REPO)) in SCENARIO_EXEMPT:
            continue
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            match = RETIRED_PROSE.search(line) or RETIRED_IDENTIFIERS.search(line)
            if match is not None:
                failures.append(
                    f"{path.relative_to(REPO)}:{number} still carries retired scenario "
                    f"text ({match.group(0)!r})",
                )

    def keyterms_of(name: str) -> str | None:
        path = STEPS / name / "main.py"
        if not path.exists():
            return None
        match = re.search(r"^KEYTERMS = \[(.*?)\]", path.read_text(), re.MULTILINE | re.DOTALL)
        return match.group(1) if match else None

    present = [(name, keyterms_of(name)) for name in CASCADE_DIRS]
    defined = [(name, value) for name, value in present if value is not None]
    if defined:
        reference_name, reference = defined[0]
        for name, value in defined[1:]:
            if value != reference:
                failures.append(
                    f"steps/{name}/main.py KEYTERMS differs from steps/{reference_name}/main.py. "
                    f"The cascade folders must carry identical scenario strings.",
                )
    return failures


def claim_corpus() -> list[Path]:
    """Every file carrying prose a learner reads, for the claim check.

    Wider than check_scenario_consistency's corpus on purpose: it adds
    course/*.yml, which nothing else in this file reads as text.

    Returns:
        Existing paths, in a stable order.
    """
    paths = (
        sorted(STEPS.glob("*/*.md"))
        + sorted(STEPS.glob("*/main.py"))
        + sorted((REPO / "course").rglob("*.md"))
        + sorted((REPO / "course").glob("*.yml"))
        + [REPO / "README.md"]
    )
    return [path for path in paths if path.exists()]


def check_retired_claims(_steps: list[Path]) -> list[str]:
    """Confirm no module still asserts a claim a later module disproves.

    Returns:
        A list of failure messages, empty when no retired claim survives.
    """
    failures = []
    for path in claim_corpus():
        where = path.relative_to(REPO)
        if str(where).startswith(CLAIM_EXEMPT_PREFIX):
            continue
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            match = RETIRED_CLAIMS.search(line)
            if match is not None:
                failures.append(
                    f"{where}:{number} asserts a retired claim ({match.group(0)!r}). "
                    f"Only {CLAIM_EXEMPT_PREFIX} may characterize LatencyReport cardinality.",
                )
    return failures


def _param_names(params: str) -> list[str]:
    """Strip annotations and defaults from a parameter list.

    Args:
        params: The text between a def's parentheses.

    Returns:
        Bare parameter names, in order.
    """
    return [part.strip().split(":")[0].split("=")[0].strip() for part in params.split(",") if part.strip()]


def _signature_params(source: str, name: str) -> list[str] | None:
    """Extract one function's parameter names from a step's source.

    Matches a commented-out `def` as well as a live one, because Module 7 ships
    its handlers as TODO templates and that is exactly where a signature
    drifted away from the answer keys last time.

    Args:
        source: The text of a step's main.py.
        name: The function to find.

    Returns:
        Parameter names in order, or None when the function is absent.
    """
    match = re.search(rf"^#?\s*def {name}\(([^)]*)\)", source, re.MULTILINE)
    return None if match is None else _param_names(match.group(1))


def check_function_signatures(_steps: list[Path]) -> list[str]:
    """Confirm the advertised function schemas match the Python they call.

    Two failures live here, and ruff catches neither.

    course/SCENARIO.md calls itself the single source of truth and promises that
    changing a string there changes it in four places. Nothing enforced that for
    signatures, so `check_availability(date, ...)` sat in its table while three
    folders shipped `date_wanted`.

    The second is worse. A function is dispatched as
    handler(**json.loads(arguments)), so a JSON Schema property that is not a
    parameter of the handler is a TypeError mid-call, on a live conversation,
    with the caller listening to silence.

    Returns:
        A list of failure messages, empty when every signature agrees.
    """
    failures = []
    scenario = SCENARIO.read_text() if SCENARIO.exists() else ""
    advertised = re.findall(r"^\|\s*`(\w+)\(([^)]*)\)`\s*\|", scenario, re.MULTILINE)

    for folder in CASCADE_DIRS:
        path = STEPS / folder / "main.py"
        if not path.exists():
            continue
        source = path.read_text()
        where = path.relative_to(REPO)

        for name, params in advertised:
            found = _signature_params(source, name)
            if found is not None and found != _param_names(params):
                failures.append(
                    f"{where} defines {name}{tuple(found)}, but course/SCENARIO.md advertises "
                    f"{name}{tuple(_param_names(params))}. The bible is the source of truth.",
                )

        for name, block in re.findall(r'name="(\w+)"(.*?)(?=name="\w+"|\Z)', source, re.DOTALL):
            found = _signature_params(source, name)
            if found is None:
                failures.append(f"{where} advertises {name!r} but defines no such function")
                continue
            required = re.search(r'"required":\s*\[([^\]]*)\]', block)
            fields = [item.strip().strip('"') for item in (required.group(1).split(",") if required else [])]
            for field in [item for item in fields if item]:
                if field not in found:
                    failures.append(
                        f"{where}: {name} requires {field!r} in its JSON Schema, which is not a "
                        f"parameter of the handler. Dispatch is handler(**json.loads(arguments)), "
                        f"so that is a TypeError mid-call.",
                    )
    return failures


def check_capstone_scope(_steps: list[Path]) -> list[str]:
    """Confirm the capstone only asks for capabilities the course teaches.

    Returns:
        A list of failure messages, empty when the capstone is in scope.
    """
    failures = []
    for name in ("BRIEF.md", "RUBRIC.md", "SCORECARD.md", "CALLERS.md"):
        path = CAPSTONE / name
        if not path.exists():
            continue
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            match = DEFERRED_SURFACE.search(line)
            if match is not None:
                failures.append(
                    f"{path.relative_to(REPO)}:{number} asks for {match.group(0)!r}, which this "
                    f"course defers. Only course/DEFERRED.md may name it.",
                )
    return failures


def check_rubric(_steps: list[Path]) -> list[str]:
    """Confirm the rubric declares its six criteria and its pass mark.

    Returns:
        A list of failure messages, empty when the rubric is complete.
    """
    path = CAPSTONE / "RUBRIC.md"
    if not path.exists():
        return [f"{path.relative_to(REPO)} does not exist yet"]

    text = path.read_text()
    failures = []
    criteria = len(re.findall(r"^### ", text, re.MULTILINE))
    if criteria != 6:
        failures.append(f"{path.relative_to(REPO)} declares {criteria} criteria (### headings), needs 6")
    for needle in ("18", "24"):
        if needle not in text:
            failures.append(f"{path.relative_to(REPO)} never mentions {needle} -- state the pass mark as 18/24")
    return failures


def main() -> None:
    """Run every check and report. Exits non-zero if any check fails."""
    steps = step_dirs()
    if not steps:
        print(f"No step folders found under {STEPS}")
        sys.exit(1)

    print(f"Checking {len(steps)} steps: {', '.join(s.name for s in steps)}\n")

    # The two pairwise checks run over the main line only. Leaving a detour in
    # would pair it with its neighbours and assert relationships that were never
    # meant to hold.
    chain = [step for step in steps if step.name not in optional_names()]

    failures = []
    for label, check in (
        ("manifest matches steps/", lambda: check_manifest(steps)),
        ("compiles", lambda: check_compiles(steps)),
        ("no leaked TODO markers", lambda: check_marker_leakage(chain)),
        ("docs present", lambda: check_docs(steps)),
        ("module artifacts present", lambda: check_module_artifacts(steps)),
        ("labs carry the course sections", lambda: check_lab_sections(steps)),
        ("prose reads as self-paced", lambda: check_no_instructor_language(steps)),
        ("scenario is Northwind, and uniform", lambda: check_scenario_consistency(steps)),
        ("no retired claims survive", lambda: check_retired_claims(steps)),
        ("function schemas match their handlers", lambda: check_function_signatures(steps)),
        ("capstone stays in scope", lambda: check_capstone_scope(steps)),
        ("rubric is complete", lambda: check_rubric(steps)),
        ("doc links resolve", lambda: check_lab_links(steps)),
        ("setup checks the right models", lambda: check_setup_models(steps)),
        ("steps grow", lambda: check_growth(chain)),
        ("ruff", check_lint),
    ):
        print(f"- {label}")
        found = check()
        for failure in found:
            print(f"    FAIL: {failure}")
        failures.extend(found)

    if failures:
        print(f"\n{len(failures)} problem(s) found.")
        sys.exit(1)

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
