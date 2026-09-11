from dataclasses import dataclass, field
from pathlib import Path

from agent_os.instruction_loader import InstructionResolver


@dataclass
class Skill:
    """Structured representation of an agent skill plus scoped instructions."""

    name: str
    version: str
    objective: str
    inputs: list[str] = field(default_factory=list)
    procedure: list[str] = field(default_factory=list)
    failure_conditions: list[str] = field(default_factory=list)
    evaluation_rubric: list[str] = field(default_factory=list)
    instructions: str = ""
    instruction_sources: list[str] = field(default_factory=list)


def _section(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    target = heading.strip().lower()
    found = False
    result = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("#"):
            current = stripped.lstrip("#").strip().lower()

            if current == target:
                found = True
                continue

            if found:
                break

        elif found and stripped.startswith("- "):
            result.append(stripped[2:].strip())

        elif found:
            result.append(stripped)

    return [item for item in result if item]


def _numbered_section(
    text: str,
    heading: str,
) -> list[str]:
    lines = text.splitlines()
    target = heading.strip().lower()
    found = False
    result = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("#"):
            current = stripped.lstrip("#").strip().lower()

            if current == target:
                found = True
                continue

            if found:
                break

        if found:
            parts = stripped.split(".", 1)

            if len(parts) == 2 and parts[0].isdigit():
                result.append(parts[1].strip())

    return result


def load_skill(
    path: str,
    *,
    include_instructions: bool = True,
    instruction_root: str | Path | None = None,
) -> Skill:
    """Load a Markdown skill definition with optional scoped instructions."""

    skill_path = Path(path).resolve()

    text = skill_path.read_text(
        encoding="utf-8"
    )

    name = (
        _section(text, "Name") or ["unknown"]
    )[0]

    version = (
        _section(text, "Version") or ["1.0.0"]
    )[0]

    objective = (
        _section(text, "Objective") or [""]
    )[0]

    instructions = ""
    instruction_sources: list[str] = []

    if include_instructions:
        resolver = InstructionResolver(
            root=instruction_root
        )

        documents = resolver.discover(skill_path)

        instruction_sources = [
            document.path
            for document in documents
        ]

        instructions = resolver.resolve(skill_path)

    return Skill(
        name=name,
        version=version,
        objective=objective,
        inputs=_section(text, "Inputs"),
        procedure=_numbered_section(
            text,
            "Procedure",
        ),
        failure_conditions=_section(
            text,
            "Failure Conditions",
        ),
        evaluation_rubric=_section(
            text,
            "Evaluation Rubric",
        ),
        instructions=instructions,
        instruction_sources=instruction_sources,
    )
