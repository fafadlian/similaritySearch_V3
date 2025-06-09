
# Similarity Search API Documentation

## Overview
This API allows clients to perform person similarity searches based on flight records, comparing a query profile against indexed passenger data using embedding, geolocation, and domain-specific scoring features. It supports fine-grained filtering and returns ranked results.

---

## Endpoint: `POST /combined_operation`

### Purpose
Performs similarity search for a person against FAISS-indexed passenger data within a given arrival date range.

### Request Example
```json
{
  "arrival_date_from": "2019-12-01",
  "arrival_date_to": "2019-12-20",
  "flight_nbr": "",
  "firstname": "Al",
  "surname": "Clark",
  "dob": "1970-01-01",
  "iata_o": "LHR",
  "iata_d": "ATH",
  "city_name": "",
  "address": "44 maurice fort east sian ph24 4jh",
  "sex": "F",
  "nationality": "",
  "nameThreshold": 30,
  "ageThreshold": 20,
  "locationThreshold": 20
}
```

### Required Fields
- `arrival_date_from`, `arrival_date_to`: ISO 8601 date range (YYYY-MM-DD). Must include leading zeros (e.g., 2019-01-05)
- `firstname`, `surname`: Strings with minimum 1 character
- `dob`: Date of birth string in YYYY-MM-DD format (e.g., 1970-01-01)
- `sex`: Accepted values are M for Males and F for Females

### Optional Fields
- `iata_o`, `iata_d`: 3-letter IATA airport codes (e.g., LHR, ATH)
- `flight_nbr`: Legacy Field. No longer used
- `city_name`:
- `address`: String address
- `nationality`: ISO 3166-1 alpha-3 country code (e.g., GBR, DZA, SGP)
- `nameThreshold`, `ageThreshold`, `locationThreshold`: Similarity thresholds (0-100)

---

### Success Response (Matches Found)
```json
{
  "status": "success",
  "data": [
    {
      "unique_id": 0,
      "PassengerID": "",
      "PNRID": "",
      "OriginIATA": "LHR",
      "DestinationIATA": "ATH",
      "FlightNumber": "601",
      "Firstname": "Alice",
      "Surname": "Clarke",
      "FullName": "Alice Clarke",
      "DOB": "1979-12-29T00:00:00",
      "Nationality": "GBR",
      "Sex": "F",
      "Address": "bristol, flat 85 deborah stream",
      "DepartureDateTime": "2019-12-15T12:59:44",
      "ArrivalDateTime": "2019-12-15T15:52:58",
      "Confidence Level": 32.5377,
      "FNSimilarity": 57,
      "SNSimilarity": 91,
      "DOBSimilarity": 60,
      "AgeSimilarity": 79.93,
      "strAddressSimilarity": 37.0,
      "originSimilarity": 100.0,
      "destinationSimilarity": 100.0,
      "Compound Similarity Score": 71.3966
    }
  ]
}
```

### Success Response (No Matches)
```json
{
  "status": "success",
  "message": "No similar passengers found.",
  "data": []
}
```

### Error Response
```json
{
  "status": "error",
  "message": "`dob` must be in 'YYYY-MM-DD' format. You may enter an approximate date."
}
```

---

---

### Output Fields

### FAISS Distance vs. Compound Score
- `FAISS Distance`: A raw distance from the FAISS index in embedding space (lower = closer). Used by the system to retrieve nearest neighbors.
- `Confidence Level`: Derived from FAISS distance using the formula `1 / (1 + faiss_distance)` and scaled to percentage. It represents how close a match is in embedding space.
- `Compound Similarity Score`: A weighted sum of interpretable features (e.g., name, address, age, location) intended to support human decision-making. Unlike FAISS distance, it incorporates domain-specific logic and heuristics.
- **Core Identity**:
  - `Firstname`, `Surname`: Matched passenger names
  - `FullName`: Concatenated first and last name
  - `DOB`: Date of birth (ISO 8601 format with time)
  - `Sex`: `M` or `F`
  - `Nationality`: ISO-3 code (e.g., `GBR`, `FRA`)
  - `Address`, `CityName`, `CityLat`, `CityLon`, `Country of Address`
  - `PlaceOfIssue`: Same as nationality
  - `PassengerID`, `PNRID`, `iata_pnrgov_notif_rq_id`: Legacy fields, always empty or 0 for compatibility

- **Flight Info**:
  - `OriginIATA`, `DestinationIATA`: IATA codes
  - `FlightNumber`: Airline flight code
  - `OriginatorAirlineCode`: Airline 2-letter or 3-letter code
  - `DepartureDateTime`, `ArrivalDateTime`: Timestamps in ISO 8601 format
  - `BookingID`: Booking reference
  - `OriginLat`, `OriginLon`, `DestinationLat`, `DestinationLon`: Flight geocoordinates
  - `OriginCity`, `DestinationCity`, `OriginCountry`, `DestinationCountry`

- **Scoring Fields**:
  - `FNSimilarity`, `SNSimilarity`: Name similarity scores (0–100)
  - `DOBSimilarity`, `AgeSimilarity`: Date of birth and relative age comparison
  - `strAddressSimilarity`, `jcdAddressSimilarity`: Fuzzy address and Jaccard similarity
  - `originSimilarity`, `destinationSimilarity`: Location distance scores
  - `Compound Similarity Score`: Final weighted score for ranking
  - `Confidence Level`: 1 / (1 + FAISS distance) * 100, capped to 4 decimals

- **Matching Flags** (binary 0/100 or categorical):
  - `cityAddressMatch`, `countryAddressMatch`, `sexMatch`, `natMatch`
  - `originAirportMatch`, `destinationAirportMatch`, `originCityMatch`, `destinationCityMatch`
  - `originCountryMatch`, `destinationCountryMatch`, etc.

- **Statistical Rarity Fields** (legacy fields, always 0):
  - `FN_rarity1`, `FN_rarity2`, `FN_prob1`, `FN_prob2`
  - `SN_rarity1`, `SN_rarity2`, `SN_prob1`, `SN_prob2`
  - `DOB_rarity1`, `DOB_rarity2`, `DOB_prob1`, `DOB_prob2`
  - Other *_rarity2 and *_prob2 fields

### Compound Similarity Score

This score is designed to be human-interpretable and balances multiple dimensions of similarity:

```
0.35 * FNSimilarity +
0.25 * SNSimilarity +
0.10 * DOBSimilarity +
0.05 * AgeSimilarity +
0.10 * strAddressSimilarity +
0.075 * originSimilarity +
0.075 * destinationSimilarity
```

---

## How it works?

1. Build Phase: Docker container is built and models are generated, including FAISS indexes using PIU data. Only done once.

2. Submit Query: User sends a query with fields like name, DOB, location, etc.

3. Embedding: Query data is embedded using the same pipeline as indexed records.

4. FAISS Retrieval: Query embedding is matched against FAISS index of the correct shard (shard = 2-month window) and retrieves top 25 nearest candidates.

5. Time Filter: Matches are filtered based on arrival_date_from and arrival_date_to.

6. Similarity Scoring: Additional similarity features (e.g., names, address, geolocation) are computed for each candidate.

7. Post-filtering: Candidates are filtered again using thresholds for name, age, and optionally location.

8. Ranking: Remaining records are sorted by Compound Similarity Score.

## Notes
- Location enrichment is based on IATA and city lookups
- Filtering is applied post-embedding and retrieval
- Results are sorted by `Compound Similarity Score` in descending order
