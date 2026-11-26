from pydantic import BaseModel, field_validator

ALLOWED_KEYS = [
    "full_name", "date_of_birth", "gender", "email", "phone",
    "college", "degree", "course", "overall_percentage", "graduation_year",
    "annual_family_income", "category", "scholarship_type",
]


class RawFact(BaseModel):
    key: str
    value: str
    page: int | None = None
    evidence: str
    confidence: float = 0.5

    @field_validator("value", "evidence", mode="before")
    @classmethod
    def _to_str(cls, v):
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return str(v)
        return v

    @field_validator("confidence")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))


class DocFacts(BaseModel):
    document_id: str
    filename: str
    facts: dict[str, dict]       # key -> {value, source{filename,page,evidence}, confidence}
    dropped: int | None = None   # facts rejected by validation (shown on extract only)