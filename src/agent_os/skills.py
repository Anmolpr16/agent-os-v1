from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class Skill:
    name: str
    version: str = "1.0.0"
    description: str = ""
    objective: str = ""
    inputs: list[str] = field(default_factory=list)
    procedure: list[str] = field(default_factory=list)
    failure_conditions: list[str] = field(default_factory=list)
    rubric: dict[str, float] = field(default_factory=dict)


def load_skill(path: str | Path) -> Skill:
    path = Path(path)
    text = path.read_text(encoding="utf-8")

    # V1 uses a simple JSON frontmatter format:
    #
    # {
    #   "name": "research",
    #   ...
    # }
    #
    # followed by Markdown procedure lines.

    if text.startswith("{"):
        end = text.find("\n---\n")

        if end != -1:
            metadata = json.loads(text[:end])
            body = text[end + 5:]
        else:
            metadata = json.loads(text)
            body = ""
    else:
        metadata = {}
        body = text

    procedure = metadata.get("procedure", [])

    if not procedure:
        procedure = [
            line.strip()[2:].strip()
            for line in body.splitlines()
            if line.strip().startswith("- ")
        ]

    return Skill(
        name=metadata.get("name", path.stem),
        version=metadata.get("version", "1.0.0"),
        description=metadata.get("description", ""),
        objective=metadata.get("objective", ""),
        inputs=metadata.get("inputs", []),
        procedure=procedure,
        failure_conditions=metadata.get("failure_conditions", []),
        rubric=metadata.get("rubric", {}),
    )
from .skill_registry import SkillRegistry, SkillVersion
