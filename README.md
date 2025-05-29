# Similarity Search WebApp

## Description
The Similarity Search WebApp is a Python-Flask-based web application designed to perform advanced similarity searches across PNR data. Utilizing a combination of algorithms for distance and age similarity, it offers users the ability to find a person from a watchlist.

## ⚙️ Prerequisites
- [Docker](https://www.docker.com/) installed and running
- [Docker Compose](https://docs.docker.com/compose/install/) (usually included with Docker Desktop)

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone <your_repo_url>
cd <repo_name>
```

### 2. Prepare Required Files
Manually prepare the following directories before starting:

- `model/`: contains prebuilt FAISS index shards and fitted models (e.g., scaler, encoder, TF-IDF, SVD, and parquet metadata)
- `data/geoCrosswalk`: contains supporting data

> 📦 You must manually place the trained indexes, models, and metadata into these folders. This is not automated.

> For access to the required files, please contact: m.f.fadlian@sheffield.ac.uk

---

## 📦 Docker Deployment

### 1. Configure Environment Variables
Create a file named `.env` in the root directory:
```env
CELERY_BROKER_URL=redis://redis:6379/0
result_backend=redis://redis:6379/0
```

### 2. Launch the Services
```bash
docker-compose up --build
```

This will:
- Build the FastAPI image using [Dockerfile.ss](Dockerfile.ss)
- Start the web service on [https://localhost:443](https://localhost:443)
- Start Redis service for optional caching or background task coordination

---

## 🧪 API Documentation
Once running, access the API documentation 
📄 [API Docs](./Similarity%20Search%20API%20Documentation.md)


<!-- **Swagger UI:**  
[https://localhost:443/docs](https://localhost:443/docs)

**Redoc:**  
[https://localhost:443/redoc](https://localhost:443/redoc) -->

---

## 🐳 `docker-compose.yml` Structure
Here’s an overview of the services used:

```yaml
services:
  web:
    build:
      context: .
      dockerfile: Dockerfile.ss
    container_name: fastapi_web
    command: uvicorn app.__init__:create_app --factory --host 0.0.0.0 --port 443
    ports:
      - "443:443"
    depends_on:
      - redis
    volumes:
      - ./app:/app/app
      - ./model:/app/model
      - ./data:/app/data
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0

  celery_worker:
  
    build:
      context: .
      dockerfile: Dockerfile.worker
    container_name: celery_worker
    command: celery -A app.tasks worker --loglevel=info --concurrency=1
    depends_on:
      - redis
    volumes:
      - ./app:/app/app
      - ./model:/app/model
      - ./data:/app/data
    user: "1000:1000"  
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/0

  redis:
    image: redis:alpine
    container_name: redis
    ports:
      - "6379:6379"
```

---

## 🗂 Folder Structure
```
├── model/                # Pretrained FAISS index + fitted models
├── data/                 # Parquet metadata files
├── local_storage/        # Temporary runtime cache
├── app/                  # Application source code
├── run.py                # FastAPI entrypoint
├── docker-compose.yml
├── Dockerfile.ss
└── Dockerfile.celery
```

---

## ✅ Done
Your FAISS similarity search API is now live and accessible at:
[https://localhost:443](https://localhost:443)




## Usage
After starting the application, navigate to `http://localhost:443` in your web browser to access the web interface. Enter your search parameters to begin finding similarities in your data.

## Query/Test Cases
All test case initiated by submitting the PNR Timeframe Parameter (Arrival Date From and Arrival Date To). We're going to use 1 January 2019 to 30 November 2019. 
ALL THE SEARCH PARAMETER NEEDS TO BE FILLED.


## 🧪 Test Case A

| Parameter          | Description                                   | Example Values |
|--------------------|-----------------------------------------------|----------------|
| First Name         | The first name of the individual to search    | Isidoro        |
| Surname            | The surname of the individual to search       | Soria          |
| Date of Birth      | The DOB of the individual (yyyy-mm-dd)        | 1980-11-18     |
| Origin IATA        | 3-letter IATA code for origin airport         | ORY            |
| Destination IATA   | 3-letter IATA code for destination airport    | LIS            |
| City Address       | Name of the city on the person's address      | Ties           |
| Address            | The person's address                          | (empty)        |
| Nationality        | Person's Nationality                          | ESP            |
| Sex                | Person's Sex                                  | M              |
| Name Threshold     | Threshold for the name similarity (0 to 100)  | 30             |
| Age Threshold      | Threshold for age similarity (0 to 100)       | 20             |
| Location Threshold | Threshold for location (0 to 100)             | 10             |

This test case will try to search **Isidoro Soria** who traveled from **Paris (ORY)** to **Lisbon (LIS)** on **9 June 2019**. This query demonstrates the fuzzy matching capability, especially in city name (`Ties`) and partial address. The address field is intentionally left empty.

### 🔁 Example API Request (cURL)
```bash
curl -X POST http://localhost:443/combined_operation   -H "Content-Type: application/json"   -d '{
    "arrival_date_from": "2019-06-09",
    "arrival_date_to": "2019-06-09",
    "flight_nbr": "91QK",
    "firstname": "Isidoro",
    "surname": "Soria",
    "dob": "1980-11-18",
    "iata_o": "ORY",
    "iata_d": "LIS",
    "city_name": "Ties",
    "address": "",
    "sex": "M",
    "nationality": "ESP",
    "nameThreshold": 30,
    "ageThreshold": 20,
    "locationThreshold": 10
  }'
```






##  Features

- **FAISS-Based Similarity Search**: Efficient approximate nearest neighbor (ANN) matching using FAISS, with support for millions of records.
- **Hybrid Feature Matching**: Combines text (name, address), categorical (gender, nationality), numeric (age), and geographic (airport/city coordinates) similarities.
- **Flexible Threshold Control**: Customizable thresholds for name, age, and location similarity allow precise tuning of match sensitivity.
- **Geolocation Matching**: Incorporates haversine-based distance computation between departure and arrival airports.
- **Prebuilt Index Loading**: Uses prepared FAISS indexes and metadata stored in `model/` and `data/` directories.
- **Dockerized Deployment**: Easily deployable via Docker Compose, including Redis and multiple service containers.
- **FastAPI Backend**: Clean RESTful interface with real-time scoring and metadata output.
- **Interactive API Docs**: Swagger and Redoc auto-generated documentation accessible at runtime.


## Contributing
Contributions to the Similarity Search WebApp are welcome. Please submit pull requests or open issues to suggest changes or add new features.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Contact
For support or inquiries, please contact via [GitHub issues](https://github.com/fafadlian). 
