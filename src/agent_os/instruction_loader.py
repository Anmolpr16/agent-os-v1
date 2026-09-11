from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


INSTRUCTION_FILENAMES = ("AGENTS.md", "CLAUDE.md")


@dataclass(frozen=True)
class InstructionDocument:
    """A scoped agent instruction document."""

    name: str
    path: str
    scope: str
    content: str


class InstructionResolver:
    """Discover hierarchical AGENTS.md/CLAUDE.md instructions deterministically."""

    def __init__(
        self,
        root: str | Path | None = None,
        filenames: tuple[str, ...] = INSTRUCTION_FILENAMES,
    ) -> None:
        self.root = Path(root).resolve() if root is not None else None
        self.filenames = tuple(filenames)

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    @staticmethod
    def _repository_root(start: Path) -> Path:
        current = start if start.is_dir() else start.parent

        for candidate in (current, *current.parents):
            if (candidate / ".git").exists():
                return candidate

        return current

    def _start_directory(self, path: str | Path) -> Path:
        target = Path(path).resolve()

        if target.exists() and target.is_file():
            return target.parent

        if target.suffix:
            return target.parent

        return target

    def _scope_root(self, start: Path) -> Path:
        root = self.root or self._repository_root(start)

        if not self._is_within(start, root):
            raise ValueError("instruction_path_outside_root")

        return root

    def discover(self, path: str | Path) -> list[InstructionDocument]:
        """Return applicable instruction documents from root to nearest scope."""

        start = self._start_directory(path)
        root = self._scope_root(start)

        directories: list[Path] = []
        current = start

        while True:
            directories.append(current)

            if current == root:
                break

            parent = current.parent
            if parent == current or not self._is_within(parent, root):
                break

            current = parent

        documents: list[InstructionDocument] = []

        for directory in reversed(directories):
            for filename in self.filenames:
                candidate = directory / filename

                if not candidate.is_file():
                    continue

                content = candidate.read_text(encoding="utf-8").strip()

                if not content:
                    continue

                documents.append(
                    InstructionDocument(
                        name=filename,
                        path=str(candidate),
                        scope=str(directory),
                        content=content,
                    )
                )

        return documents

    def resolve(self, path: str | Path) -> str:
        """Return applicable instructions ordered from broadest to narrowest scope."""

        documents = self.discover(path)

        return "\n\n".join(
            f"# Instructions from {document.name} ({document.scope})\n\n"
            f"{document.content}"
            for document in documents
        )


def discover_instructions(
    path: str | Path,
    *,
    root: str | Path | None = None,
) -> list[InstructionDocument]:
    """Convenience API for scoped instruction discovery."""

    return InstructionResolver(root=root).discover(path)


def load_instructions(
    path: str | Path,
    *,
    root: str | Path | None = None,
) -> str:
    """Convenience API returning resolved hierarchical instructions."""

    return InstructionResolver(root=root).resolve(path)
