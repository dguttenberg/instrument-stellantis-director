"""Working-project state: the active (uploaded, human-edited) script + dials the
matrix runs against. Single-user local app — persisted as one JSON file. Seeds from
the bundled South:15 script on first use so the app is never empty."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict

from .config import DATA_DIR, get_settings
from .schemas.dials import Dials
from .schemas.script import Scene, Script

_DEFAULT_SCRIPT = DATA_DIR / "scripts" / "map_retail_ram_test_15_south.json"
_DEMO_DIALS = DATA_DIR / "dials" / "year_end_demo.json"


class Project(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script: Script
    dials: Dials


class ProjectStore:
    def __init__(self, path: Optional[Path] = None):
        self.path = Path(path) if path else get_settings().project_store_abspath

    def load(self) -> Project:
        if self.path.exists():
            return Project.model_validate_json(self.path.read_text(encoding="utf-8"))
        # Start BLANK so an upload visibly populates the matrix (extraction is obvious).
        # Not saved — stays empty until a deck is uploaded or the sample is loaded.
        return Project(
            script=Script(script_id="", total_scenes=0, scenes=[]),
            dials=Dials.model_validate_json(_DEMO_DIALS.read_text(encoding="utf-8")),
        )

    def load_sample(self) -> Project:
        """Populate the matrix from the bundled South:15 (no-file fallback / demo)."""
        return self.set_script(
            Script.model_validate_json(_DEFAULT_SCRIPT.read_text(encoding="utf-8")),
            dials=Dials.model_validate_json(_DEMO_DIALS.read_text(encoding="utf-8")),
        )

    def save(self, project: Project) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(project.model_dump_json(indent=2), encoding="utf-8")

    def set_script(self, script: Script, dials: Optional[Dials] = None) -> Project:
        current = self.load()
        project = Project(script=script, dials=dials or current.dials)
        self.save(project)
        return project

    def update_scene(self, scene_index: int, patch: dict) -> Optional[Scene]:
        project = self.load()
        for i, scene in enumerate(project.script.scenes):
            if scene.scene_index == scene_index:
                updated = scene.model_copy(update={k: v for k, v in patch.items() if v is not None})
                project.script.scenes[i] = updated
                self.save(project)
                return updated
        return None
