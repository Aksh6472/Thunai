"""Load and validate the versioned scoring config (AI_DESIGN §6, §11).

An invalid config must stop the app at startup (fail closed at deploy time).
"""

from pathlib import Path

import yaml
from pydantic import ValidationError

from app.domain.config import ScoringConfig

DEFAULT_SCORING_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "scoring_v1.yaml"


class ScoringConfigError(RuntimeError):
    """The scoring config file is missing, unparsable or fails validation."""


def load_scoring_config(path: Path = DEFAULT_SCORING_CONFIG_PATH) -> ScoringConfig:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ScoringConfigError(f"cannot read scoring config {path.name}: {exc}") from exc
    try:
        return ScoringConfig.from_mapping(data)
    except ValidationError as exc:
        raise ScoringConfigError(f"invalid scoring config {path.name}: {exc}") from exc
