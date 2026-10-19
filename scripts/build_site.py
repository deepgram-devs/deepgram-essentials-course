# /// script
# requires-python = ">=3.13"
# dependencies = ["pyyaml==6.0.3"]
# ///
"""Generate the published site's markdown from the course source. Maintainers only.

    uv run scripts/build_site.py ../live-docs/workshops

The site keeps its own copy of each lab, with YAML front matter the Angular app
reads. Those copies used to be hand-forked, and nothing detected the drift.
This script makes the repo the single source of truth: labs come from
steps/*/LAB.md, so there is exactly one place to edit them.

Module quizzes are not published here. They live in the teaching repo and are
delivered through the LMS.
"""

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
STEPS = REPO / "steps"
MANIFEST = REPO / "course" / "modules.yml"
SLUG = "deepgram-essentials-course-py"


def main() -> None:
    """Write one markdown file per module into the site's workshop directory."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    out_dir = Path(sys.argv[1]).resolve() / "src" / "workshops" / SLUG
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = yaml.safe_load(MANIFEST.read_text())
    written = []

    for order, module in enumerate(manifest["modules"]):
        doc = STEPS / module["step_dir"] / module.get("doc_name", "LAB.md")
        text = doc.read_text()

        first = text.index("\n")
        body = text[first + 1 :].lstrip("\n")

        front: dict = {"title": module["title"], "order": order}
        if module.get("optional"):
            front["optional"] = True

        header = yaml.safe_dump(front, sort_keys=False, allow_unicode=True, width=10_000)
        target = out_dir / f"{module['step_dir']}.md"
        target.write_text(f"---\n{header}---\n\n{body}")
        written.append(target.name)

    workshop = {
        "title": manifest["course"]["title"],
        "tagline": "Build a production-shaped voice agent in Python, one module at a time",
        "description": (
            "A self-paced course. You build one voice agent for one client -- Northwind Clinic, a "
            "patient-access line -- and every module adds one capability to it: it listens on Flux, "
            "thinks with an LLM, answers in a natural voice, stops the moment you interrupt, verifies "
            "a caller, books an appointment exactly once, refuses to say what it should not, and "
            "reports what every turn cost. Every module is a complete, working program, so you can "
            "start at the beginning or drop in anywhere. At the end you submit your agent for the "
            f"{manifest['course']['badge']} badge."
        ),
    }
    (out_dir / "workshop.yml").write_text(
        yaml.safe_dump(workshop, sort_keys=False, allow_unicode=True, width=10_000),
    )

    print(f"Wrote {len(written)} modules to {out_dir.relative_to(Path.cwd()) if out_dir.is_relative_to(Path.cwd()) else out_dir}")
    for name in written:
        print(f"  {name}")


if __name__ == "__main__":
    main()
