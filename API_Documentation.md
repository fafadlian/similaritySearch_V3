
# Similarity Search API Documentation

## Overview
This API provides functionality for flight data fetching, similarity searches, and combined operations. The endpoints enable users to submit flight search parameters, perform similarity searches, and retrieve results.

## Endpoints

### Submit Flight Search Parameters
### Combined Operation
**Endpoint:**  
`http://127.0.0.1:443/combined_operation`

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
{"status":"success","message":"Operation completed successfully.","task_id":"ced5c5f7-675c-4826-a920-a8af8b048d6f","data":
  [
    {"unique_id":746,"PassengerID":"b46be59c-02fd-41c4-94f0-4023ffa382fb","PNRID":"3e321d99-b2df-418a-a74d-edef53649c56","iata_pnrgov_notif_rq_id":"4acdb7ad-0c83-4fa8-8c71-c32ba0d55f00","OriginIATA":"ATH","DestinationIATA":"LHR","FlightLegFlightNumber":"66GA","OriginatorAirlineCode":"BA","FlightNumber":"66GA","DepartureDateTime":"2019-02-01T12:27:50.000+00:00","ArrivalDateTime":"2019-02-01T16:00:59.000+00:00","BookingID":"ATH/KEF/RTH/8/310119/85032/13-2","Firstname":"Serapheim","Surname":"Perdikes","FullName":"Serapheim Perdikes","TravelDocNumber":"GRC_7246_1","PlaceOfIssue":"GRC","DOB":"1991-09-02","Nationality":"GRC","Sex":"M","CityName":"Trilofos","Address":"trilofos, mpotza 03, tk 51318 bolos","OriginLat":23.9445,"OriginLon":37.9364,"DestinationLat":-0.4619,"DestinationLon":51.4706,"CityLat":null,"CityLon":null,"OriginCity":"Athens","DestinationCity":"London","OriginCountry":"GRC","DestinationCountry":"GBR","Country of Address":null,"Confidence Level":16.772,"FNSimilarity":31,"FN1":"Fred","FN2":"Serapheim","FN_rarity1":0.0,"FN_rarity2":0.0002,"FN_prob1":100,"FN_prob2":100,"SNSimilarity":43,"SN1":"Copper","SN2":"Perdikes","SN_rarity1":0.0,"SN_rarity2":0.0001,"SN_prob1":100,"SN_prob2":100,"DOBSimilarity":80,"DOB1":"1990-01-02","DOB2":"1991-09-02","DOB_rarity1":0.0,"DOB_rarity2":0.0001,"DOB_prob1":100,"DOB_prob2":100,"AgeSimilarity":94.1159,"strAddressSimilarity":null,"jcdAddressSimilarity":null,"cityAddressMatch":0,"cityAddressRarity1":100.0,"cityAddressProb1":0.0,"cityAddressRarity2":0.0007,"cityAddressProb2":100.0,"countryAddressMatch":null,"countryAddressRarity2":100.0,"countryAddressProb2":0.0,"sexMatch":0,"sexRarity2":0.0543,"sexProb2":100.0,"natMatch":0,"natRarity2":0.0783,"natProb2":100.0,"originAirportMatch":0,"originAirportRarity2":0.08,"originAirportProb2":100.0,"destinationAirportMatch":0,"destinationAirportRarity2":0.0115,"destinationAirportProb2":100.0,"orgdesAirportMatch":0,"desorgAirportMatch":0,"originCityMatch":0,"originCityRarity2":0.08,"originCityProb2":100.0,"destinationCityMatch":0,"destinationCityRarity2":0.0149,"destinationCityProb2":100.0,"orgdesCityMatch":0,"desorgCityMatch":0,"originCountryMatch":0,"originCountryRarity2":0.08,"originCountryProb2":100.0,"destinationCountryMatch":0,"destinationCountryRarity2":0.0149,"destinationCountryProb2":100.0,"orgdesCountryMatch":0,"desorgCountryMatch":0,"originSimilarity":70.0301,"originExpScore":74.1041,"destinationSimilarity":46.2021,"destinationExpScore":58.3927,"orgdesSimilarity":46.2021,"orgdesExpScore":58.3927,"desorgSimilarity":70.0301,"desorgExpScore":74.1041,"Compound Similarity Score":49.3981},
    {"unique_id":1002,"PassengerID":"1c22bd97-c676-428b-a548-167ea45677b6","PNRID":"c44deda2-3b8b-47fa-aa76-5e294fbf4403","iata_pnrgov_notif_rq_id":"6d4ae999-b873-425e-93f6-cae98046b684","OriginIATA":"FCO","DestinationIATA":"ATH","FlightLegFlightNumber":"720","OriginatorAirlineCode":"AZ","FlightNumber":"720","DepartureDateTime":"2019-02-01T07:28:33.000+00:00","ArrivalDateTime":"2019-02-01T08:50:21.000+00:00","BookingID":"TLS/ATH/RTB/1/310119/98638/11","Firstname":"Frederic","Surname":"Pelletier","FullName":"Frederic Pelletier","TravelDocNumber":"FRA_89475_1","PlaceOfIssue":"FRA","DOB":"1983-12-25","Nationality":"FRA","Sex":"M","CityName":"Lavelanet","Address":"lavelanet, 4, rue dubois 20802 pintoboeuf","OriginLat":12.2389,"OriginLon":41.8003,"DestinationLat":23.9445,"DestinationLon":37.9364,"CityLat":null,"CityLon":null,"OriginCity":"Rome","DestinationCity":"Athens","OriginCountry":"ITA","DestinationCountry":"GRC","Country of Address":null,"Confidence Level":11.5057,"FNSimilarity":67,"FN1":"Fred","FN2":"Frederic","FN_rarity1":0.0,"FN_rarity2":0.0001,"FN_prob1":100,"FN_prob2":100,"SNSimilarity":40,"SN1":"Copper","SN2":"Pelletier","SN_rarity1":0.0,"SN_rarity2":0.0001,"SN_prob1":100,"SN_prob2":100,"DOBSimilarity":60,"DOB1":"1990-01-02","DOB2":"1983-12-25","DOB_rarity1":0.0,"DOB_rarity2":0.0001,"DOB_prob1":100,"DOB_prob2":100,"AgeSimilarity":84.1776,"strAddressSimilarity":null,"jcdAddressSimilarity":null,"cityAddressMatch":0,"cityAddressRarity1":100.0,"cityAddressProb1":0.0,"cityAddressRarity2":0.0001,"cityAddressProb2":100.0,"countryAddressMatch":null,"countryAddressRarity2":100.0,"countryAddressProb2":0.0,"sexMatch":0,"sexRarity2":0.0543,"sexProb2":100.0,"natMatch":0,"natRarity2":0.0022,"natProb2":100.0,"originAirportMatch":0,"originAirportRarity2":0.0078,"originAirportProb2":100.0,"destinationAirportMatch":0,"destinationAirportRarity2":0.0149,"destinationAirportProb2":100.0,"orgdesAirportMatch":0,"desorgAirportMatch":0,"originCityMatch":0,"originCityRarity2":0.0078,"originCityProb2":100.0,"destinationCityMatch":0,"destinationCityRarity2":0.0149,"destinationCityProb2":100.0,"orgdesCityMatch":0,"desorgCityMatch":0,"originCountryMatch":0,"originCountryRarity2":0.0078,"originCountryProb2":100.0,"destinationCountryMatch":0,"destinationCountryRarity2":0.0149,"destinationCountryProb2":100.0,"orgdesCountryMatch":0,"desorgCountryMatch":0,"originSimilarity":60.7719,"originExpScore":67.5514,"destinationSimilarity":70.0301,"destinationExpScore":74.1041,"orgdesSimilarity":70.0301,"orgdesExpScore":74.1041,"desorgSimilarity":60.7719,"desorgExpScore":67.5514,"Compound Similarity Score":38.2884},
    {"unique_id":928,"PassengerID":"5dae49f3-256e-4a55-91e4-e5583caadd80","PNRID":"f76cf22f-fcc9-46c2-a137-53bd3d1163b5","iata_pnrgov_notif_rq_id":"1d0ffc4e-cc9e-47b4-a3b0-d299cccb3240","OriginIATA":"ATH","DestinationIATA":"DUS","FlightLegFlightNumber":"9W","OriginatorAirlineCode":"A3","FlightNumber":"9W","DepartureDateTime":"2019-02-01T08:16:07.000+00:00","ArrivalDateTime":"2019-02-01T11:08:55.000+00:00","BookingID":"ATH/DUS/RTB/1/010219/94407/13","Firstname":"Arkhimedes","Surname":"Raptes","FullName":"Arkhimedes Raptes","TravelDocNumber":"GRC_3670_1","PlaceOfIssue":"GRC","DOB":"1993-05-23","Nationality":"GRC","Sex":"M","CityName":"Thessaloniki","Address":"thessaloniki, stenes 15, tk 181 35 trikala","OriginLat":23.9445,"OriginLon":37.9364,"DestinationLat":6.7668,"DestinationLon":51.2895,"CityLat":22.9709,"CityLon":40.5197,"OriginCity":"Athens","DestinationCity":"Duesseldorf","OriginCountry":"GRC","DestinationCountry":"DEU","Country of Address":"GRC","Confidence Level":1.2675,"FNSimilarity":43,"FN1":"Fred","FN2":"Arkhimedes","FN_rarity1":0.0,"FN_rarity2":0.0004,"FN_prob1":100,"FN_prob2":100,"SNSimilarity":33,"SN1":"Copper","SN2":"Raptes","SN_rarity1":0.0,"SN_rarity2":0.0001,"SN_prob1":100,"SN_prob2":100,"DOBSimilarity":70,"DOB1":"1990-01-02","DOB2":"1993-05-23","DOB_rarity1":0.0,"DOB_rarity2":0.0001,"DOB_prob1":100,"DOB_prob2":100,"AgeSimilarity":87.8639,"strAddressSimilarity":null,"jcdAddressSimilarity":null,"cityAddressMatch":0,"cityAddressRarity1":100.0,"cityAddressProb1":0.0,"cityAddressRarity2":0.0058,"cityAddressProb2":100.0,"countryAddressMatch":null,"countryAddressRarity2":0.0765,"countryAddressProb2":100.0,"sexMatch":0,"sexRarity2":0.0543,"sexProb2":100.0,"natMatch":0,"natRarity2":0.0783,"natProb2":100.0,"originAirportMatch":0,"originAirportRarity2":0.08,"originAirportProb2":100.0,"destinationAirportMatch":0,"destinationAirportRarity2":0.0012,"destinationAirportProb2":100.0,"orgdesAirportMatch":0,"desorgAirportMatch":0,"originCityMatch":0,"originCityRarity2":0.08,"originCityProb2":100.0,"destinationCityMatch":0,"destinationCityRarity2":0.0012,"destinationCityProb2":100.0,"orgdesCityMatch":0,"desorgCityMatch":0,"originCountryMatch":0,"originCountryRarity2":0.08,"originCountryProb2":100.0,"destinationCountryMatch":0,"destinationCountryRarity2":0.0158,"destinationCountryProb2":100.0,"orgdesCountryMatch":0,"desorgCountryMatch":0,"originSimilarity":70.0301,"originExpScore":74.1041,"destinationSimilarity":50.9314,"destinationExpScore":61.2206,"orgdesSimilarity":50.9314,"orgdesExpScore":61.2206,"desorgSimilarity":70.0301,"desorgExpScore":74.1041,"Compound Similarity Score":43.3679}
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


### Combined Operation:
```shell
curl -X POST http://127.0.0.1:443/combined_operation \
-H "Content-Type: application/json" \
-d '{
    "arrival_date_from": "2019-01-06",
    "arrival_date_to": "2019-01-09",
    "flight_nbr": "",
    "firstname": "collins",
    "surname": "browning",
    "dob": "1968-10-10",
    "iata_o": "DXB",
    "iata_d": "BUD",
    "city_name": "Singapore",
    "address": "singapore, 15 debra trafficway wadeshire w0 6fz",
    "sex": "M",
    "nationality": "SGP",
    "nameThreshold": 10,
    "ageThreshold": 10,
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
