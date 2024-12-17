
# Similarity Search API Documentation

## Overview
This API provides functionality for flight data fetching, similarity searches, and combined operations. The endpoints enable users to submit flight search parameters, perform similarity searches, and retrieve results.

## Endpoints

### Submit Flight Search Parameters
**Endpoint:**  
`http://0.0.0.0:443/submit_param`

**Request Method:**  
POST

**Request Example:**
```json
{
  "arrival_date_from": "2019-05-01",
  "arrival_date_to": "2019-05-03",
  "flight_nbr": ""
}
```

**Response:**
```json
{
  "status": "processing",
  "task_id": "7cb39633-4b65-49d9-8f18-9f86761e9293"
}
```

### Perform Similarity Search
**Endpoint:**  
`http://0.0.0.0:443/perform_similarity_search`

**Request Method:**  
POST

**Request Example:**
```json
{
  "task_id": "7cb39633-4b65-49d9-8f18-9f86761e9293",
  "firstname": "Fred",
  "surname": "Copper",
  "dob": "1990-01-02",
  "iata_o": "ALG",
  "iata_d": "ALG",
  "city_name": "",
  "address": "",
  "sex": "Female",
  "nationality": "Algeria",
  "nameThreshold": 30,
  "ageThreshold": 20,
  "locationThreshold": 10
}
```

**Response Example:**
```json
{
  "status": "success",
  "data":[
    {"unique_id":896,"OriginIATA":"ATH","DestinationIATA":"CDG","FlightLegFlightNumber":"4CA","OriginatorAirlineCode":"A3","OperatingAirlineFlightNumber":"612","DepartureDateTime":"2019-04-27 11:35:05+00:00","ArrivalDateTime":"2019-04-27 14:39:58+00:00","BookingID":"CDG-ATH-business-ID21","Firstname":"Justin","Surname":"Oliver","Name":"Justin Oliver","Travel Doc Number":"BRN_10724_1","Place of Issue":"CUB","DOB":"1964-01-08","Nationality":"CUB","Sex":"M","CityName":"Paris","Address":"967 Schmidt Club Apt. 785\nRobinsontown, MP 59371","OriginLat":23.9445,"OriginLon":37.9364,"DestinationLat":2.55,"DestinationLon":49.0128,"CityLat":2.55,"CityLon":49.0128,"OriginCity":"Athens","DestinationCity":"Paris","OriginCountry":"GRC","DestinationCountry":"FRA","Country of Address":"FRA","Confidence Level":35.0563,"FNSimilarity":40,"FN1":"John","FN2":"Justin","FN_rarity1":0.0003,"FN_rarity2":0.0002,"FN_prob1":100,"FN_prob2":100,"SNSimilarity":50,"SN1":"Copper","SN2":"Oliver","SN_rarity1":0.0,"SN_rarity2":0.0001,"SN_prob1":100,"SN_prob2":100,"DOBSimilarity":70,"DOB1":"1980-01-01","DOB2":"1964-01-08","DOB_rarity1":0.0,"DOB_rarity2":0.0001,"DOB_prob1":100,"DOB_prob2":100,"AgeSimilarity":68.9845,"strAddressSimilarity":null,"jcdAddressSimilarity":null,"cityAddressMatch":0,"cityAddressRarity1":100.0,"cityAddressProb1":0.0,"cityAddressRarity2":0.0146,"cityAddressProb2":100.0,"countryAddressMatch":null,"countryAddressRarity2":0.0146,"countryAddressProb2":100.0,"sexMatch":100,"sexRarity2":0.023,"sexProb2":100.0,"natMatch":0,"natRarity2":0.0001,"natProb2":100.0,"originAirportMatch":0,"originAirportRarity2":0.0205,"originAirportProb2":100.0,"destinationAirportMatch":0,"destinationAirportRarity2":0.01,"destinationAirportProb2":100.0,"orgdesAirportMatch":0,"desorgAirportMatch":0,"originCityMatch":0,"originCityRarity2":0.0205,"originCityProb2":100.0,"destinationCityMatch":0,"destinationCityRarity2":0.01,"destinationCityProb2":100.0,"orgdesCityMatch":0,"desorgCityMatch":0,"originCountryMatch":0,"originCountryRarity2":0.0205,"originCountryProb2":100.0,"destinationCountryMatch":0,"destinationCountryRarity2":0.01,"destinationCountryProb2":100.0,"orgdesCountryMatch":0,"desorgCountryMatch":0,"originSimilarity":17.0145,"originExpScore":43.6112,"destinationSimilarity":0.0,"destinationExpScore":26.9174,"orgdesSimilarity":0.0,"orgdesExpScore":35.2812,"desorgSimilarity":0.0,"desorgExpScore":33.539,"Compound Similarity Score":45.0669},
      {"unique_id":899,"OriginIATA":"ATH","DestinationIATA":"CDG","FlightLegFlightNumber":"4CA","OriginatorAirlineCode":"A3","OperatingAirlineFlightNumber":"3DG","DepartureDateTime":"2019-04-12 15:43:50+00:00","ArrivalDateTime":"2019-04-12 18:27:39+00:00","BookingID":"CDG-ATH-business-ID21","Firstname":"Justin","Surname":"Oliver","Name":"Justin Oliver","Travel Doc Number":"BRN_10724_1","Place of Issue":"CUB","DOB":"1964-01-08","Nationality":"CUB","Sex":"M","CityName":"Paris","Address":"967 Schmidt Club Apt. 785\nRobinsontown, MP 59371","OriginLat":23.9445,"OriginLon":37.9364,"DestinationLat":2.55,"DestinationLon":49.0128,"CityLat":2.55,"CityLon":49.0128,"OriginCity":"Athens","DestinationCity":"Paris","OriginCountry":"GRC","DestinationCountry":"FRA","Country of Address":"FRA","Confidence Level":35.0563,"FNSimilarity":40,"FN1":"John","FN2":"Justin","FN_rarity1":0.0003,"FN_rarity2":0.0002,"FN_prob1":100,"FN_prob2":100,"SNSimilarity":50,"SN1":"Copper","SN2":"Oliver","SN_rarity1":0.0,"SN_rarity2":0.0001,"SN_prob1":100,"SN_prob2":100,"DOBSimilarity":70,"DOB1":"1980-01-01","DOB2":"1964-01-08","DOB_rarity1":0.0,"DOB_rarity2":0.0001,"DOB_prob1":100,"DOB_prob2":100,"AgeSimilarity":68.9845,"strAddressSimilarity":null,"jcdAddressSimilarity":null,"cityAddressMatch":0,"cityAddressRarity1":100.0,"cityAddressProb1":0.0,"cityAddressRarity2":0.0146,"cityAddressProb2":100.0,"countryAddressMatch":null,"countryAddressRarity2":0.0146,"countryAddressProb2":100.0,"sexMatch":100,"sexRarity2":0.023,"sexProb2":100.0,"natMatch":0,"natRarity2":0.0001,"natProb2":100.0,"originAirportMatch":0,"originAirportRarity2":0.0205,"originAirportProb2":100.0,"destinationAirportMatch":0,"destinationAirportRarity2":0.01,"destinationAirportProb2":100.0,"orgdesAirportMatch":0,"desorgAirportMatch":0,"originCityMatch":0,"originCityRarity2":0.0205,"originCityProb2":100.0,"destinationCityMatch":0,"destinationCityRarity2":0.01,"destinationCityProb2":100.0,"orgdesCityMatch":0,"desorgCityMatch":0,"originCountryMatch":0,"originCountryRarity2":0.0205,"originCountryProb2":100.0,"destinationCountryMatch":0,"destinationCountryRarity2":0.01,"destinationCountryProb2":100.0,"orgdesCountryMatch":0,"desorgCountryMatch":0,"originSimilarity":17.0145,"originExpScore":43.6112,"destinationSimilarity":0.0,"destinationExpScore":26.9174,"orgdesSimilarity":0.0,"orgdesExpScore":35.2812,"desorgSimilarity":0.0,"desorgExpScore":33.539,"Compound Similarity Score":45.0669}
      ]
}
```

### Combined Operation
**Endpoint:**  
`http://0.0.0.0:443/combined_operation`

**Request Method:**  
POST

**Request Example:**
```json
{
  "arrival_date_from": "2019-05-01",
  "arrival_date_to": "2019-05-03",
  "flight_nbr": "",
  "firstname": "Fred",
  "surname": "Copper",
  "dob": "1990-01-02",
  "iata_o": "ALG",
  "iata_d": "ALG",
  "city_name": "",
  "address": "",
  "sex": "Female",
  "nationality": "Algeria",
  "nameThreshold": 30,
  "ageThreshold": 20,
  "locationThreshold": 10
}
```

**Response Example (Success):**
```json
{
  "status": "success",
  "message": "Operation completed successfully.",
  "task_id": "7cb39633-4b65-49d9-8f18-9f86761e9293",
  "data": [
      {"status":"success","message":"Operation completed successfully.","task_id":"3e8572b1-e41c-4251-ac4d-039ef99cc081","data":[{"unique_id":896,"OriginIATA":"ATH","DestinationIATA":"CDG","FlightLegFlightNumber":"4CA","OriginatorAirlineCode":"A3","OperatingAirlineFlightNumber":"612","DepartureDateTime":"2019-04-27 11:35:05+00:00","ArrivalDateTime":"2019-04-27 14:39:58+00:00","BookingID":"CDG-ATH-business-ID21","Firstname":"Justin","Surname":"Oliver","Name":"Justin Oliver","Travel Doc Number":"BRN_10724_1","Place of Issue":"CUB","DOB":"1964-01-08","Nationality":"CUB","Sex":"M","CityName":"Paris","Address":"967 Schmidt Club Apt. 785\nRobinsontown, MP 59371","OriginLat":23.9445,"OriginLon":37.9364,"DestinationLat":2.55,"DestinationLon":49.0128,"CityLat":2.55,"CityLon":49.0128,"OriginCity":"Athens","DestinationCity":"Paris","OriginCountry":"GRC","DestinationCountry":"FRA","Country of Address":"FRA","Confidence Level":35.0563,"FNSimilarity":40,"FN1":"John","FN2":"Justin","FN_rarity1":0.0003,"FN_rarity2":0.0002,"FN_prob1":100,"FN_prob2":100,"SNSimilarity":50,"SN1":"Copper","SN2":"Oliver","SN_rarity1":0.0,"SN_rarity2":0.0001,"SN_prob1":100,"SN_prob2":100,"DOBSimilarity":70,"DOB1":"1980-01-01","DOB2":"1964-01-08","DOB_rarity1":0.0,"DOB_rarity2":0.0001,"DOB_prob1":100,"DOB_prob2":100,"AgeSimilarity":68.9845,"strAddressSimilarity":null,"jcdAddressSimilarity":null,"cityAddressMatch":0,"cityAddressRarity1":100.0,"cityAddressProb1":0.0,"cityAddressRarity2":0.0146,"cityAddressProb2":100.0,"countryAddressMatch":null,"countryAddressRarity2":0.0146,"countryAddressProb2":100.0,"sexMatch":100,"sexRarity2":0.023,"sexProb2":100.0,"natMatch":0,"natRarity2":0.0001,"natProb2":100.0,"originAirportMatch":0,"originAirportRarity2":0.0205,"originAirportProb2":100.0,"destinationAirportMatch":0,"destinationAirportRarity2":0.01,"destinationAirportProb2":100.0,"orgdesAirportMatch":0,"desorgAirportMatch":0,"originCityMatch":0,"originCityRarity2":0.0205,"originCityProb2":100.0,"destinationCityMatch":0,"destinationCityRarity2":0.01,"destinationCityProb2":100.0,"orgdesCityMatch":0,"desorgCityMatch":0,"originCountryMatch":0,"originCountryRarity2":0.0205,"originCountryProb2":100.0,"destinationCountryMatch":0,"destinationCountryRarity2":0.01,"destinationCountryProb2":100.0,"orgdesCountryMatch":0,"desorgCountryMatch":0,"originSimilarity":17.0145,"originExpScore":43.6112,"destinationSimilarity":0.0,"destinationExpScore":26.9174,"orgdesSimilarity":0.0,"orgdesExpScore":35.2812,"desorgSimilarity":0.0,"desorgExpScore":33.539,"Compound Similarity Score":45.0669},
      {"unique_id":899,"OriginIATA":"ATH","DestinationIATA":"CDG","FlightLegFlightNumber":"4CA","OriginatorAirlineCode":"A3","OperatingAirlineFlightNumber":"3DG","DepartureDateTime":"2019-04-12 15:43:50+00:00","ArrivalDateTime":"2019-04-12 18:27:39+00:00","BookingID":"CDG-ATH-business-ID21","Firstname":"Justin","Surname":"Oliver","Name":"Justin Oliver","Travel Doc Number":"BRN_10724_1","Place of Issue":"CUB","DOB":"1964-01-08","Nationality":"CUB","Sex":"M","CityName":"Paris","Address":"967 Schmidt Club Apt. 785\nRobinsontown, MP 59371","OriginLat":23.9445,"OriginLon":37.9364,"DestinationLat":2.55,"DestinationLon":49.0128,"CityLat":2.55,"CityLon":49.0128,"OriginCity":"Athens","DestinationCity":"Paris","OriginCountry":"GRC","DestinationCountry":"FRA","Country of Address":"FRA","Confidence Level":35.0563,"FNSimilarity":40,"FN1":"John","FN2":"Justin","FN_rarity1":0.0003,"FN_rarity2":0.0002,"FN_prob1":100,"FN_prob2":100,"SNSimilarity":50,"SN1":"Copper","SN2":"Oliver","SN_rarity1":0.0,"SN_rarity2":0.0001,"SN_prob1":100,"SN_prob2":100,"DOBSimilarity":70,"DOB1":"1980-01-01","DOB2":"1964-01-08","DOB_rarity1":0.0,"DOB_rarity2":0.0001,"DOB_prob1":100,"DOB_prob2":100,"AgeSimilarity":68.9845,"strAddressSimilarity":null,"jcdAddressSimilarity":null,"cityAddressMatch":0,"cityAddressRarity1":100.0,"cityAddressProb1":0.0,"cityAddressRarity2":0.0146,"cityAddressProb2":100.0,"countryAddressMatch":null,"countryAddressRarity2":0.0146,"countryAddressProb2":100.0,"sexMatch":100,"sexRarity2":0.023,"sexProb2":100.0,"natMatch":0,"natRarity2":0.0001,"natProb2":100.0,"originAirportMatch":0,"originAirportRarity2":0.0205,"originAirportProb2":100.0,"destinationAirportMatch":0,"destinationAirportRarity2":0.01,"destinationAirportProb2":100.0,"orgdesAirportMatch":0,"desorgAirportMatch":0,"originCityMatch":0,"originCityRarity2":0.0205,"originCityProb2":100.0,"destinationCityMatch":0,"destinationCityRarity2":0.01,"destinationCityProb2":100.0,"orgdesCityMatch":0,"desorgCityMatch":0,"originCountryMatch":0,"originCountryRarity2":0.0205,"originCountryProb2":100.0,"destinationCountryMatch":0,"destinationCountryRarity2":0.01,"destinationCountryProb2":100.0,"orgdesCountryMatch":0,"desorgCountryMatch":0,"originSimilarity":17.0145,"originExpScore":43.6112,"destinationSimilarity":0.0,"destinationExpScore":26.9174,"orgdesSimilarity":0.0,"orgdesExpScore":35.2812,"desorgSimilarity":0.0,"desorgExpScore":33.539,"Compound Similarity Score":45.0669}]
  ]
}
```

**Response Example (No Flights Found):**
```json
{
  "status": "error",
  "message": "No flights found within the specified parameters."
}
```

**Response Example (No Similar Passengers):**
```json
{
  "status": "success",
  "message": "No similar passengers found.",
  "task_id": "7cb39633-4b65-49d9-8f18-9f86761e9293",
  "data": []
}
```

**Response Example (Task Timed Out):**
```json
{
  "status": "error",
  "message": "Task timed out while processing flights."
}
```

### Monitor Task Status (SSE)
**Endpoint:**  
`http://0.0.0.0:443/sse/{task_id}`

**Request Method:**  
GET

**Example:**
```shell
curl -X GET "http://0.0.0.0:443/sse/7cb39633-4b65-49d9-8f18-9f86761e9293"
```

**Response (Stream):**
```css
data: {"status": "pending", "message": "Task is still in progress."}
data: {"status": "completed", "message": "Task completed", "folder": "task_7cb39633-4b65-49d9-8f18-9f86761e9293"}
```

### Poll Task Status
**Endpoint:**  
`http://0.0.0.0:443/result/{task_id}`

**Request Method:**  
GET

**Example:**
```shell
curl -X GET "http://0.0.0.0:443/result/7cb39633-4b65-49d9-8f18-9f86761e9293"
```

**Response Example:**
```json
{
  "status": "completed",
  "message": "Task completed",
  "folder": "task_7cb39633-4b65-49d9-8f18-9f86761e9293"
}
```

### Delete Task
**Endpoint:**  
`http://0.0.0.0:443/delete_task`

**Request Method:**  
POST

**Request Example:**
```json
{
  "task_id": "7cb39633-4b65-49d9-8f18-9f86761e9293"
}
```

**Response Example:**
```json
{
  "status": "success",
  "message": "Task deleted successfully."
}
```

## Curl Request Examples

### Submit Parameters:
```shell
curl -X POST http://0.0.0.0:443/submit_param \
-H "Content-Type: application/json" \
-d '{"arrival_date_from": "2019-05-01", "arrival_date_to": "2019-05-03", "flight_nbr": ""}'
```

### Perform Similarity Search:
```shell
curl -X POST http://0.0.0.0:443/perform_similarity_search \
-H "Content-Type: application/json" \
-d '{
    "task_id": "7cb39633-4b65-49d9-8f18-9f86761e9293",
    "firstname": "Fred",
    "surname": "Copper",
    "dob": "1990-01-02",
    "iata_o": "ALG",
    "iata_d": "ALG",
    "city_name": "",
    "address": "",
    "sex": "Female",
    "nationality": "Algeria",
    "nameThreshold": 30,
    "ageThreshold": 20,
    "locationThreshold": 10
}'
```

### Combined Operation:
```shell
curl -X POST http://0.0.0.0:443/combined_operation \
-H "Content-Type: application/json" \
-d '{
    "arrival_date_from": "2019-05-01",
    "arrival_date_to": "2019-05-03",
    "flight_nbr": "",
    "firstname": "Fred",
    "surname": "Copper",
    "dob": "1990-01-02",
    "iata_o": "ALG",
    "iata_d": "ALG",
    "city_name": "",
    "address": "",
    "sex": "Female",
    "nationality": "Algeria",
    "nameThreshold": 30,
    "ageThreshold": 20,
    "locationThreshold": 10
}'
```

## Error Handling

### No Flights Found:
```json
{
  "status": "error",
  "message": "No flights found within the specified parameters."
}
```

### No Similar Passengers Found:
```json
{
  "status": "success",
  "message": "No similar passengers found.",
  "data": []
}
```

### Task Timed Out:
```json
{
  "status": "error",
  "message": "Task timed out while processing flights."
}
```

### Task Failed:
```json
{
  "status": "error",
  "message": "Similarity search failed."
}
```
