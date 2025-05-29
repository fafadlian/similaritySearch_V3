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


### Test Case A

| Parameter          | Description                                   | Example Values |
|--------------------|-----------------------------------------------|----------------|
| First Name         | The first name of the individual to search    | Dominick          |
| Surname            | The surname of the individual to search       | Oritz          |
| Date of Birth      | The DOB individual to search       (dd/mm/yyyy)           | 30/10/1980             |
| Origin IATA        | 3-letter IATA code for origin airport         | DXB            |
| Destination IATA   | 3-letter IATA code for destination airport    | ATH            |
| City Address       | Name of the city on the person's address      | Dubai          |
| Address            | the person's address                          | 75655 Wilson Junction. Lake Johnshire, MH 63787  |
| Nationality        | Person's Nationality                          | Macau          |
| Sex                | Person's Sex                                  | Female           |
| Name Threshold     | Threshold for the name similarity (0 to 100)  | 70            |
| Age Threshold      | Threshold for age similarity (0 to 100)       | 50             |
| Location Threshold | Threshold for location (0 to 100)             | 95             |

This test case will try to search Dominique Ortiz that travels from Dubai (DXB) to Athens (ATH) with address in Dubai. The complete address is 75655 Wilson Junction, Lake Johnshire, MH 63787. We use slightly different values in the query for the purpose of showing how the 'fuzzy' similarity search works. He travels between 1 May 2019 – 3 May 2019




### Test Case B
We're looking someone with the name of Tom, one of the associates of the criminal organisation. However, we are uncertain about the surname, some of the authorities said that the name is either Davies, Davids, or Davis. He was born on November 1943. He travels from London to Athens on the first few days of March 2019. He’s known to have an apartment in Bright Gardens, Delacruzburg, London. He has a Malaysian passport.

Things to consider:
London has 6 airports (LCY, LHR, LGW, LTN, STN, SEN)
Tom could be a short version of Thomas or Tommy


Feel free to adjust the thresholds and see how the threshold affect the output. 


### Test Case C
We’re looking for a person that travels in the first week of April 2019 from somewhere in London to Athens. He has a Bahrain passport and was born in 1975. His first name is  قيد (Kayad) and his last name is (الدبغ) Aldabg. He is known to live in Rapids Suites, London.
Things to consider:
Only type the Latin Alphabet name
50 name threshold value
80 age/dob and location threshold value



## Features
- **Data Similarity Searches**: Perform searches based on multiple similarity criteria.
- **Adjustable Sensitivity (Threshold)**: Utilizes custom threshold for the similarity score.
- **Machine Learning Recommendation**: Utilise machine learing algorithm to assist user for the similarity search.
- **Interactive Web Interface**: Easy-to-use web interface for all user interactions.

## Contributing
Contributions to the Similarity Search WebApp are welcome. Please submit pull requests or open issues to suggest changes or add new features.

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Contact
For support or inquiries, please contact via [GitHub issues](https://github.com/fafadlian). 
