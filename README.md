# Similarity Search WebApp

## Description
The Similarity Search WebApp is a Python-Flask-based web application designed to perform advanced similarity searches across PNR data. Utilizing a combination of algorithms for distance and age similarity, it offers users the ability to find a person from a watchlist.

## Installation
To run this application, ensure you have Docker installed on your machine.

1. Clone the repository to your local machine. 
2. You will need python 3.11 and postgreSQL to run this project
3. Navigate to the project directory.
4. Install the required libraries 
```bash 
pip install requirements.txt 
```
5. Set up environment variables: create a environment.env file in the project root and provide the necessary configurations: 
```sh
#local storage
STORAGE_PATH=local_storage

#celery config
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

#postgresql config
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=<your_db_name>
POSTGRES_USER=<your_db_user/owner>
POSTGRES_PASSWORD=<your_db_password>
POSTGRES_SSLMODE=disable
DATABASE_URL=postgresql+psycopg2://<db_username>:<db_password>@localhost:5432/similaritysearch

#rmt api and app
ACCESS_TOKEN=<your_RMT_access_token>
REFRESH_TOKEN=<your_RMT_refresh_token>
USERNAME=<your_RMT_username>
PASSWORD=<your_RMT_password>
APP_ENV=development
APP_DEBUG=True
APP_PORT=8000
```
5. Start redis from terminal: 
```sh 
redis-server 
```
6. Open two terminal tabs and run these to run celery workers: 
```sh 
celery -A app.celery_init.celery worker --loglevel=info
celery -A app.celery_init.celery beat --loglevel=info 
```

5. Run the the following command: ````uvicorn run:app --host 0.0.0.0 --port 443 --log-level info````


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
