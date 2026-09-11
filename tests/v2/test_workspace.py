from pathlib import Path

import pytest

from agent_os.workspace import Workspace, WorkspaceError


def test_workspace_reads_and_writes_only_inside_root(tmp_path: Path):
    workspace = Workspace(tmp_path / "workspace")

    written = workspace.write_text("notes/result.txt", "verified")
    assert written == "notes/result.txt"
    assert workspace.read_text("notes/result.txt") == "verified"
    assert workspace.exists("notes/result.txt")


def test_workspace_rejects_parent_escape(tmp_path: Path):
    workspace = Workspace(tmp_path / "workspace")

    with pytest.raises(WorkspaceError, match="workspace_path_escape"):
        workspace.read_text("../outside.txt")


def test_workspace_rejects_absolute_paths(tmp_path: Path):
    workspace = Workspace(tmp_path / "workspace")

    with pytest.raises(WorkspaceError, match="absolute_path_not_allowed"):
        workspace.read_text(str(tmp_path / "outside.txt"))


def test_workspace_rejects_symlink_escape(tmp_path: Path):
    workspace_root = tmp_path / "workspace"
    workspace = Workspace(workspace_root)

    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    link = workspace_root / "escape.txt"
    link.symlink_to(outside)

    with pytest.raises(WorkspaceError, match="workspace_path_escape"):
        workspace.read_text("escape.txt")


def test_workspace_lists_entries_deterministically(tmp_path: Path):
    workspace = Workspace(tmp_path / "workspace")
    workspace.write_text("b.txt", "b")
    workspace.write_text("a.txt", "a")
    workspace.write_text("nested/c.txt", "c")

    entries = workspace.list()

    assert [entry.name for entry in entries] == ["a.txt", "b.txt", "nested"]
    assert entries[0].is_file is True
    assert entries[2].is_directory is True


def test_workspace_blocks_root_delete(tmp_path: Path):
    workspace = Workspace(tmp_path / "workspace")

    with pytest.raises(WorkspaceError, match="workspace_root_delete_blocked"):
        workspace.delete(".")


def test_workspace_enforces_read_limit(tmp_path: Path):
    workspace = Workspace(tmp_path / "workspace")
    workspace.write_text("large.txt", "123456")

    with pytest.raises(WorkspaceError, match="workspace_file_too_large"):
        workspace.read_text("large.txt", max_bytes=3)
