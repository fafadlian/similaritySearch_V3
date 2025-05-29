from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, model_validator
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
    dob: Optional[str] = None
    iata_o: Optional[str] = None
    iata_d: Optional[str] = None
    city_name: Optional[str] = None
    address: Optional[str] = None
    sex: Optional[str] = None
    nationality: Optional[str] = None
    nameThreshold: Optional[float] = 0.0
    ageThreshold: Optional[float] = 0.0
    locationThreshold: Optional[float] = 0.0

    @model_validator(mode="after")
    def check_required_fields(self):
        errors = []

        if not self.arrival_date_from:
            errors.append("`arrival_date_from` is required and cannot be empty.")

        if not self.arrival_date_to:
            errors.append("`arrival_date_to` is required and cannot be empty.")

        if not self.firstname or not self.firstname.strip():
            errors.append("`firstname` is required and cannot be empty.")

        if not self.surname or not self.surname.strip():
            errors.append("`surname` is required and cannot be empty.")

        if errors:
            raise ValueError(" | ".join(errors))

        return self
