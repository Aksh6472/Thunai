"""ADR-010 / SECURITY §11.2: no protected attribute can reach the scoring input."""

from pydantic import BaseModel

from app.domain.config import ScoringConfig
from app.domain.models import AssessmentInput

PROTECTED = ("age", "gender", "sex", "religion", "caste", "location", "address", "language", "dob")


def _field_names(model: type[BaseModel], seen: set[type] | None = None) -> set[str]:
    seen = seen or set()
    if model in seen:
        return set()
    seen.add(model)
    names: set[str] = set()
    for name, field in model.model_fields.items():
        names.add(name)
        for arg in _nested_models(field.annotation):
            names |= _field_names(arg, seen)
    return names


def _nested_models(annotation: object) -> list[type[BaseModel]]:
    found: list[type[BaseModel]] = []
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        found.append(annotation)
    for arg in getattr(annotation, "__args__", ()) or ():
        found += _nested_models(arg)
    return found


def _is_protected(name: str) -> bool:
    parts = name.lower().split("_")
    return any(p in PROTECTED for p in parts)


def test_assessment_input_has_no_protected_attributes() -> None:
    names = _field_names(AssessmentInput)
    assert "payee_age_minutes" not in names  # evidence only, not an input field
    offending = sorted(n for n in names if _is_protected(n))
    assert not offending, f"protected attributes in scoring input: {offending}"


def test_scoring_config_has_no_protected_keys() -> None:
    offending = sorted(n for n in _field_names(ScoringConfig) if _is_protected(n))
    # Both are the age of the payee relationship (how long ago it was added), not a person's age.
    assert offending == ["max_age_hours", "min_payee_age_days"], offending
