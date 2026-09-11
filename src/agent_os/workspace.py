from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class WorkspaceError(RuntimeError):
    """Raised when a workspace operation violates the workspace boundary."""


@dataclass(frozen=True)
class WorkspaceEntry:
    name: str
    path: str
    is_file: bool
    is_directory: bool


class Workspace:
    """Sandboxed filesystem workspace rooted at one directory.

    All paths are resolved beneath the configured root. Absolute paths,
    parent traversal, and symlink escapes are rejected.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative_path: str | Path) -> Path:
        candidate = Path(relative_path)

        if candidate.is_absolute():
            raise WorkspaceError("absolute_path_not_allowed")

        resolved = (self.root / candidate).resolve()

        try:
            resolved.relative_to(self.root)
        except ValueError:
            raise WorkspaceError("workspace_path_escape") from None

        return resolved

    def exists(self, relative_path: str | Path) -> bool:
        return self._resolve(relative_path).exists()

    def read_text(self, relative_path: str | Path, *, max_bytes: int = 1_048_576) -> str:
        if max_bytes <= 0:
            raise ValueError("max_bytes must be positive")

        path = self._resolve(relative_path)

        if not path.exists():
            raise FileNotFoundError(str(relative_path))

        if not path.is_file():
            raise WorkspaceError("workspace_path_not_file")

        data = path.read_bytes()

        if len(data) > max_bytes:
            raise WorkspaceError("workspace_file_too_large")

        return data.decode("utf-8")

    def write_text(
        self,
        relative_path: str | Path,
        content: str,
        *,
        create_parents: bool = True,
    ) -> str:
        path = self._resolve(relative_path)

        if create_parents:
            path.parent.mkdir(parents=True, exist_ok=True)
        elif not path.parent.exists():
            raise FileNotFoundError(str(path.parent))

        if path.exists() and path.is_symlink():
            raise WorkspaceError("workspace_symlink_write_blocked")

        path.write_text(content, encoding="utf-8")
        return str(path.relative_to(self.root))

    def delete(self, relative_path: str | Path) -> None:
        path = self._resolve(relative_path)

        if not path.exists():
            raise FileNotFoundError(str(relative_path))

        if path == self.root:
            raise WorkspaceError("workspace_root_delete_blocked")

        if path.is_dir():
            raise WorkspaceError("workspace_directory_delete_blocked")

        path.unlink()

    def list(self, relative_path: str | Path = ".") -> list[WorkspaceEntry]:
        directory = self._resolve(relative_path)

        if not directory.exists():
            raise FileNotFoundError(str(relative_path))

        if not directory.is_dir():
            raise WorkspaceError("workspace_path_not_directory")

        entries: list[WorkspaceEntry] = []

        for path in sorted(directory.iterdir(), key=lambda item: item.name):
            resolved = path.resolve()

            try:
                resolved.relative_to(self.root)
            except ValueError:
                raise WorkspaceError("workspace_symlink_escape") from None

            entries.append(
                WorkspaceEntry(
                    name=path.name,
                    path=str(resolved.relative_to(self.root)),
                    is_file=path.is_file(),
                    is_directory=path.is_dir(),
                )
            )

        return entries
