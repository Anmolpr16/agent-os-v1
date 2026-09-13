__version__ = "2.0.0rc1"

from .workspace import Workspace, WorkspaceEntry, WorkspaceError

from .instruction_loader import (
    InstructionDocument,
    InstructionResolver,
    discover_instructions,
    load_instructions,
)
from .skill_repository import SkillRepository, PersistentSkillRegistry
