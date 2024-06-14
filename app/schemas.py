from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field
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
