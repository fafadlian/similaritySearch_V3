from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, Literal

from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional
from datetime import date, datetime

class FlightSearchRequest(BaseModel):
    arrival_date_from: Optional[datetime]
    arrival_date_to: Optional[datetime]
    flight_nbr: Optional[str]

class SimilaritySearchRequest(BaseModel):
    task_id: str
    firstname: Optional[str]
    surname: Optional[str]
    dob: Optional[str]
    iata_o: Optional[str]
    iata_d: Optional[str]
    city_name: Optional[str]
    address: Optional[str]
    sex: Optional[str]
    nationality: Optional[str]
    nameThreshold: Optional[float]
    ageThreshold: Optional[float]
    locationThreshold: Optional[float]

class CombinedRequest(BaseModel):
    arrival_date_from: datetime
    arrival_date_to: datetime
    flight_nbr: Optional[str] = None
    firstname: str
    surname: str
    dob: str
    iata_o: Optional[str] = None
    iata_d: Optional[str] = None
    city_name: Optional[str] = None
    address: Optional[str] = None
    sex: str
    nationality: Optional[str] = Field(
        default=None,
        description="Use ISO-3 code for country (e.g., 'GBR', 'DZA'). Country names are not recommended."
    )
    nameThreshold: Optional[float] = 0.0
    ageThreshold: Optional[float] = 0.0
    locationThreshold: Optional[float] = 0.0

    @field_validator("dob", mode="before")
    @classmethod
    def validate_dob_format(cls, v):
        if not v or not v.strip():
            raise ValueError("`dob` is required. You may enter an approximate date in 'YYYY-MM-DD' format.")
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("`dob` must be in 'YYYY-MM-DD' format. You may enter an approximate date.")
        return v

    @field_validator("sex", mode="before")
    @classmethod
    def normalize_and_validate_sex(cls, v):
        if not v:
            raise ValueError("`sex` is required and must be 'M' or 'F'.")
        v_lower = v.strip().lower()
        if v_lower in {"f", "female"}:
            return "F"
        elif v_lower in {"m", "male"}:
            return "M"
        else:
            raise ValueError("`sex` must be 'M' or 'F' (case-insensitive).")

    @model_validator(mode="after")
    def check_required_fields(self):
        errors = []

        if not self.arrival_date_from:
            errors.append("`arrival_date_from` is required. Use 'YYYY-MM-DD' format.")
        if not self.arrival_date_to:
            errors.append("`arrival_date_to` is required. Use 'YYYY-MM-DD' format.")
        if not self.firstname or not self.firstname.strip():
            errors.append("`firstname` is required and cannot be empty.")
        if not self.surname or not self.surname.strip():
            errors.append("`surname` is required and cannot be empty.")

        if errors:
            raise ValueError(" | ".join(errors))

        return self
