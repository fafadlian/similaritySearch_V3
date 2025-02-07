
import xml.etree.ElementTree as ET
import pandas as pd
import logging
import time
import os
from datetime import datetime
from app.loc_access import LocDataAccess
from dotenv import load_dotenv
import json
from app.loc_access import LocDataAccess


load_dotenv('environment.env')
STORAGE_PATH = os.getenv('STORAGE_PATH')

def parse_combined_xml(xml_content):
    logging.info("Parsing XML content")

    data = []
    airport_data_access = LocDataAccess.get_instance()

    # Iterate over each notification request node
    for notif_rq in xml_content.findall('.//IATA_PNRGOV_NotifRQ'):
        originator_code = notif_rq.find('.//Originator').get('AirlineCode', 'Unknown')
        
        for flight_leg in notif_rq.findall('.//FlightLeg'):
            flight_number = flight_leg.get('FlightNumber', 'Unknown')
            origin_code = flight_leg.find('.//DepartureAirport').get('LocationCode', 'Unknown')
            destination_code = flight_leg.find('.//ArrivalAirport').get('LocationCode', 'Unknown')
            origin_lon, origin_lat = airport_data_access.get_airport_lon_lat_by_iata(origin_code)
            destination_lon, destination_lat = airport_data_access.get_airport_lon_lat_by_iata(destination_code)
            
            for pnr in flight_leg.findall('.//PNR'):
                booking_id = pnr.find('.//BookingRefID').get('ID', 'Unknown')
                
                for passenger in pnr.findall('.//Passenger'):
                    firstname = passenger.find('.//GivenName').text if passenger.find('.//GivenName') is not None else 'Unknown'
                    surname = passenger.find('.//Surname').text if passenger.find('.//Surname') is not None else 'Unknown'
                    name = f"{firstname} {surname}"
                    
                    # Further details like travel documents, addresses, etc.
                    # Assuming DOC_SSR has important travel document info
                    doc_info = passenger.find('.//DOC_SSR')
                    if doc_info is not None:
                        travel_doc_nbr = doc_info.get('TravelDocNbr', 'Unknown')
                        place_of_issue = doc_info.get('PlaceOfIssue', 'Unknown')
                    else:
                        travel_doc_nbr, place_of_issue = 'Unknown', 'Unknown'
                    
                    data.append((
                        originator_code, flight_number, origin_code, destination_code, origin_lon, origin_lat,
                        destination_lon, destination_lat, booking_id, firstname, surname, name,
                        travel_doc_nbr, place_of_issue
                    ))

    columns = [
        'OriginatorCode', 'FlightNumber', 'OriginIATA', 'DestinationIATA', 'OriginLon', 'OriginLat',
        'DestinationLon', 'DestinationLat', 'BookingID', 'Firstname', 'Surname', 'FullName',
        'TravelDocNumber', 'PlaceOfIssue'
    ]
    df = pd.DataFrame(data, columns=columns)
    logging.info(f"Dataframe created with shape: {df.shape}")
    return df

def parse_combined_json(combined_data):
    logging.info(f"Parsing combined JSON data")
    start_time = time.time()

    airport_data_access = LocDataAccess.get_instance()  # Access the singleton instance

    all_data = []

    for data in combined_data:
        flight_data = data['iata_pnrgov_notif_rq_obj']
        origin_code = flight_data.get('flight_leg_departure_airp_location_code')
        destination_code = flight_data.get('flight_leg_arrival_airp_location_code')
        flight_leg_flight_number = flight_data.get('flight_leg_flight_number', 'Unknown')
        originator_airline_code = flight_data.get('originator_airline_code', 'Unknown')
        origin_lon, origin_lat = airport_data_access.get_airport_lon_lat_by_iata(origin_code) if origin_code else (None, None)
        destination_lon, destination_lat = airport_data_access.get_airport_lon_lat_by_iata(destination_code) if destination_code else (None, None)

        pnr_data = [
            (pnr, flight, passenger)
            for pnr in flight_data['pnr_obj']
            for flight in pnr['flight_obj']
            for passenger in pnr['passenger_obj']
        ]

        for pnr, flight, passenger in pnr_data:
            bookID = pnr.get('booking_refid', 'Unknown')
            operating_airline_flight_number = flight.get('operating_airline_flight_number', 'Unknown')
            departure_date_time = flight.get('departure_date_time', 'Unknown')
            arrival_date_time = flight.get('arrival_date_time', 'Unknown')

            firstname = passenger['doc_ssr_obj'].get('docs_first_givenname', '').strip()
            surname = passenger['doc_ssr_obj'].get('docs_surname', '').strip()
            name = f"{firstname} {surname}"
            travel_doc_nbr = passenger['doc_ssr_obj'].get('doco_travel_doc_nbr', 'Unknown')
            place_of_issue = passenger['doc_ssr_obj'].get('doco_placeof_issue', 'Unknown')
            date_of_birth = passenger['doc_ssr_obj'].get('docs_dateof_birth', 'Unknown')
            date_of_birth_raw = passenger['doc_ssr_obj'].get('docs_dateof_birth', 'Unknown')
            dob_object = datetime.strptime(date_of_birth_raw, "%d%b%y")
            date_of_birth = dob_object.strftime("%Y-%m-%d")
            nationality = passenger['doc_ssr_obj'].get('docs_pax_nationality', 'Unknown')
            sex = passenger['doc_ssr_obj'].get('docs_gender', 'Unknown')
            city_name = passenger['doc_ssr_obj'].get('doca_city_name')
            address = passenger['doc_ssr_obj'].get('doca_address')

            all_data.append((
                origin_code, destination_code, flight_leg_flight_number, originator_airline_code,
                operating_airline_flight_number, departure_date_time, arrival_date_time, bookID,
                firstname, surname, name, travel_doc_nbr, place_of_issue, date_of_birth, nationality, sex,
                city_name, address
            ))

    columns = ['OriginIATA', 'DestinationIATA', 'FlightLegFlightNumber', 'OriginatorAirlineCode',
                'OperatingAirlineFlightNumber', 'DepartureDateTime', 'ArrivalDateTime', 'BookingID',
                'Firstname', 'Surname', 'Name', 'Travel Doc Number', 'Place of Issue', 'DOB', 'Nationality', 'Sex',
                'CityName', 'Address']    
    df = pd.DataFrame(all_data, columns=columns)
    print("df shape: ", df.shape)   
    logging.info(f"Parsing completed in {time.time() - start_time:.2f} seconds")
    return df

# Function to fetch and parse similarity search results
def fetch_and_parse_combined_data(task_id, data_dir):
    try:
        # Construct the full path to the task's JSON file
        folder_path = os.path.join(STORAGE_PATH, f"task_{task_id}")
        file_path = os.path.join(folder_path, f"task_{task_id}.json")

        logging.info(f"checking local storage path: {STORAGE_PATH}")
        logging.info(f"checking if local storage path exists: {os.path.exists(STORAGE_PATH)}")
        logging.info(f"checking folder path: {folder_path}")
        logging.info(f"checking if folder exists: {os.path.exists(folder_path)}")
        logging.info(f"checking file path: {file_path}")
        logging.info(f"checking if file exists: {os.path.exists(file_path)}")
        logging.info(f"checking current working directory: {os.getcwd()}")

        # ✅ Wait for the file to be fully written (max 5 seconds)
        max_wait_time = 5  # Maximum time to wait for the file (seconds)
        wait_interval = 0.5  # Check every 0.5 seconds

        for _ in range(int(max_wait_time / wait_interval)):
            if os.path.exists(file_path):
                break
            logging.warning(f"🚨 File {file_path} is not ready yet. Waiting...")
            time.sleep(wait_interval)

        # ✅ If the file still does not exist, raise an error
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"🚨 The file {file_path} does not exist in local storage after waiting.")

        logging.info(f"📂 Fetching combined data from {file_path}")

        # Check if the file exists
        if os.path.exists(file_path):
            logging.info(f"Fetching combined data from {file_path}")
            with open(file_path, 'r') as file:
                raw_data = json.load(file)
                # If raw_data is a stringified JSON, parse it again
                if isinstance(raw_data, str):
                    raw_data = json.loads(raw_data)

                logging.info(f"Successfully fetched data from {file_path}")
        else:
            raise FileNotFoundError(f"The file {file_path} does not exist in local storage.")
    except Exception as e:
        logging.error(f"Error fetching combined data from {file_path}: {str(e)}")
        return None

    # Start parsing data
    logging.info(f"Parsing combined JSON data")
    start_time = time.time()

    all_data = []

    # Loop through each entry in the combined data
    for data in raw_data:
        # Extract flight details
        origin_code = data.get('flight_leg_departure_airp_location_code', 'Unknown')
        destination_code = data.get('flight_leg_arrival_airp_location_code', 'Unknown')
        flight_leg_flight_number = data.get('flight_leg_flight_number', 'Unknown')
        originator_airline_code = data.get('originator_airline_code', 'Unknown')
        flight_number = data.get('flight_number', 'Unknown')
        departure_date_time = data.get('departure_date_time', 'Unknown')
        arrival_date_time = data.get('arrival_date_time', 'Unknown')
        booking_refid = data.get('booking_refid', 'Unknown')

        # Extract passenger details
        passenger_id = data.get('passenger_id', 'Unknown')
        pnr_id = data.get('pnr_id', 'Unknown')
        given_name = data.get('given_name', '').strip()
        surname = data.get('surname', '').strip()
        full_name = data.get('full_name', f"{given_name} {surname}")
        travel_doc_nbr = data.get('doco_travel_doc_nbr', 'Unknown')
        place_of_issue = data.get('doco_placeof_issue', 'Unknown')
        date_of_birth_raw = data.get('docs_dateof_birth', 'Unknown')
        
        # Convert DOB to YYYY-MM-DD format
        try:
            dob_object = datetime.strptime(date_of_birth_raw, "%d%b%y")
            date_of_birth = dob_object.strftime("%Y-%m-%d")
        except ValueError:
            date_of_birth = 'Unknown'

        nationality = data.get('docs_pax_nationality', 'Unknown')
        gender = data.get('docs_gender', 'Unknown')
        city_name = data.get('doca_city_name', 'Unknown')
        address = data.get('doca_address', 'Unknown')

        # Append extracted data to list
        all_data.append((
            passenger_id, pnr_id, origin_code, destination_code, flight_leg_flight_number, 
            originator_airline_code, flight_number, departure_date_time, arrival_date_time, 
            booking_refid, given_name, surname, full_name, travel_doc_nbr, place_of_issue, 
            date_of_birth, nationality, gender, city_name, address
        ))

    # Define DataFrame columns
    columns = [
        'PassengerID', 'PNRID', 'OriginIATA', 'DestinationIATA', 'FlightLegFlightNumber',
        'OriginatorAirlineCode', 'FlightNumber', 'DepartureDateTime', 'ArrivalDateTime', 'BookingID',
        'Firstname', 'Surname', 'FullName', 'TravelDocNumber', 'PlaceOfIssue', 
        'DOB', 'Nationality', 'Sex', 'CityName', 'Address'
    ]

    # Convert to Pandas DataFrame
    df = pd.DataFrame(all_data, columns=columns)

    # Log completion
    logging.info(f"Parsing completed in {time.time() - start_time:.2f} seconds")
    logging.info(f"df shape: {df.shape}")

    return df
