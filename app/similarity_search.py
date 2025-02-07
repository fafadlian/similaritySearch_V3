import os
import requests
import json
import pandas as pd
import numpy as np
import joblib
import concurrent.futures
from functools import partial
import time
import datetime

import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.loc_access import LocDataAccess
from app.data_parser import parse_combined_json, parse_combined_xml, fetch_and_parse_combined_data
from app.location_similarity import haversine, location_similarity_score, location_matching, address_str_similarity_score
from app.age_similarity import age_similarity_score
from app.base_similarity import count_likelihood2, string_similarity

# from app.azure_blob_storage import upload_to_blob_storage, download_from_blob_storage, delete_all_files_in_directory, fetch_combined_data
from app.local_storage import upload_to_local_storage, download_from_local_storage, delete_all_files_in_directory, fetch_combined_data
# from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

import logging


logging.basicConfig(level=logging.INFO)


AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
CONTAINER_NAME = os.getenv('CONTAINER_NAME')

# blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)


def enrich_data(df):
    airport_data_access = LocDataAccess.get_instance()

    # Fetch lat/lon for origin and destination airports using vectorized operations
    origin_locs = df['OriginIATA'].map(lambda x: airport_data_access.get_airport_lon_lat_by_iata(x) if x else (None, None))
    destination_locs = df['DestinationIATA'].map(lambda x: airport_data_access.get_airport_lon_lat_by_iata(x) if x else (None, None))

    df[['OriginLat', 'OriginLon']] = pd.DataFrame(origin_locs.tolist(), index=df.index)
    df[['DestinationLat', 'DestinationLon']] = pd.DataFrame(destination_locs.tolist(), index=df.index)

    # Fetch city information using vectorized operations
    city_locs = df['CityName'].map(lambda x: airport_data_access.get_airport_lon_lat_by_city(x) if x else (None, None))
    df[['CityLat', 'CityLon']] = pd.DataFrame(city_locs.tolist(), index=df.index)
    
    df['OriginCity'] = df['OriginIATA'].map(lambda x: airport_data_access.get_city_by_airport_iata(x) if x else None)
    df['DestinationCity'] = df['DestinationIATA'].map(lambda x: airport_data_access.get_city_by_airport_iata(x) if x else None)
    
    df['OriginCountry'] = df['OriginIATA'].map(lambda x: airport_data_access.get_country_by_airport_iata(x) if x else None)
    df['DestinationCountry'] = df['DestinationIATA'].map(lambda x: airport_data_access.get_country_by_airport_iata(x) if x else None)
    
    df['Country of Address'] = df['CityName'].map(lambda x: airport_data_access.get_country_by_city(x) if x else None)
    
    return df



def parse_combined_data(combined_data):
    logging.info(f"Parsing combined JSON data")
    logging.info(f"combined_data type: {type(combined_data)}, content: {combined_data[:2]}")
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
    logging.info(f"Parsing completed in {time.time() - start_time:.2f} seconds")
    return df

def parse_json(file_path):
    logging.info(f"Parsing JSON file: {file_path}")
    airport_data_access = LocDataAccess.get_instance()  # Access the singleton instance
    # json_content = download_from_blob_storage(file_path)  # Download JSON content from Azure Blob Storage
    json_content = download_from_local_storage(file_path)  # Download JSON content from local storage
    logging.info(f"ready to parse: {file_path}")
    data = json.loads(json_content)

    flight_data = data['iata_pnrgov_notif_rq_obj']
    origin_code = flight_data.get('flight_leg_departure_airp_location_code')
    destination_code = flight_data.get('flight_leg_arrival_airp_location_code')
    flight_leg_flight_number = flight_data.get('flight_leg_flight_number', 'Unknown')
    originator_airline_code = flight_data.get('originator_airline_code', 'Unknown')
    origin_lon, origin_lat = airport_data_access.get_airport_lon_lat_by_iata(origin_code) if origin_code else (None, None)
    destination_lon, destination_lat = airport_data_access.get_airport_lon_lat_by_iata(destination_code) if destination_code else (None, None)

    data_list = []

    for pnr in flight_data['pnr_obj']:
        bookID = pnr.get('booking_refid', 'Unknown')
        for flight in pnr['flight_obj']:
            operating_airline_flight_number = flight.get('operating_airline_flight_number', 'Unknown')
            departure_date_time = flight.get('departure_date_time', 'Unknown')
            arrival_date_time = flight.get('arrival_date_time', 'Unknown')
            
            for passenger in pnr['passenger_obj']:
                firstname = passenger['doc_ssr_obj'].get('docs_first_givenname', '').strip()
                surname = passenger['doc_ssr_obj'].get('docs_surname', '').strip()
                name = f"{firstname} {surname}"
                travel_doc_nbr = passenger['doc_ssr_obj'].get('doco_travel_doc_nbr', 'Unknown')
                place_of_issue = passenger['doc_ssr_obj'].get('doco_placeof_issue', 'Unknown')
                date_of_birth = passenger['doc_ssr_obj'].get('docs_dateof_birth', 'Unknown')
                nationality = passenger['doc_ssr_obj'].get('docs_pax_nationality', 'Unknown')
                sex = passenger['doc_ssr_obj'].get('docs_gender', 'Unknown')
                city_name = passenger['doc_ssr_obj'].get('doca_city_name')
                address = passenger['doc_ssr_obj'].get('doca_address')
                
                city_lat, city_lon = airport_data_access.get_airport_lon_lat_by_city(city_name) if city_name else (None, None)
                city_org = airport_data_access.get_city_by_airport_iata(origin_code) if origin_code else (None)
                city_dest = airport_data_access.get_city_by_airport_iata(destination_code) if destination_code else (None)
                ctry_org = airport_data_access.get_country_by_airport_iata(origin_code) if origin_code else (None)
                ctry_dest = airport_data_access.get_country_by_airport_iata(destination_code) if destination_code else (None)
                country_of_address = airport_data_access.get_country_by_city(city_name) if city_name else (None)

                data_list.append((file_path, bookID, firstname, surname, name, travel_doc_nbr, place_of_issue, origin_code, city_org, ctry_org, origin_lat, origin_lon, destination_code, city_dest, ctry_dest, destination_lat, destination_lon, date_of_birth, city_name, city_lat, city_lon, address, country_of_address, nationality, sex, flight_leg_flight_number, originator_airline_code, operating_airline_flight_number, departure_date_time, arrival_date_time))

    columns = ['FilePath', 'BookingID', 'Firstname', 'Surname', 'Name', 'Travel Doc Number', 'Place of Issue', 'OriginIATA', 'OriginCity', 'OriginCountry', 'OriginLat', 'OriginLon', 'DestinationIATA', 'DestinationCity', 'DestinationCountry', 'DestinationLat', 'DestinationLon', 'DOB', 'CityName', 'CityLat', 'CityLon', 'Address', 'Country of Address', 'Nationality', 'Sex', 'FlightLegFlightNumber', 'OriginatorAirlineCode', 'OperatingAirlineFlightNumber', 'DepartureDateTime', 'ArrivalDateTime']
    df = pd.DataFrame(data_list, columns=columns)
    return df
  
def find_similar_passengers(task_id, airport_data_access, firstname, surname, name, dob, iata_o, iata_d, city_name, address, sex, nationality, folder_name, nameThreshold, ageThreshold, locationThreshold):
    # Fetch the combined JSON data from Azure Blob Storage
    all_data = fetch_and_parse_combined_data(task_id, folder_name)
    
    # Parse the combined data
    logging.info(f"all_data shape before enrichment: {all_data.shape}")
    start_time = time.time()
    all_data = enrich_data(all_data)
    end_time = time.time()
    logging.info(f"Time for enriching data: {end_time - start_time:.2f} seconds")
    logging.info(f"all_data enriched shape: {all_data.shape}")
    # Perform similarity search on the aggregated data
    start_time = time.time()
    lon_o, lat_o = airport_data_access.get_airport_lon_lat_by_iata(iata_o)
    lon_d, lat_d = airport_data_access.get_airport_lon_lat_by_iata(iata_d)
    lon_c, lat_c = airport_data_access.get_airport_lon_lat_by_city(city_name)
    country = airport_data_access.get_country_by_city(city_name)
    ctry_org = airport_data_access.get_country_by_airport_iata(iata_o)
    ctry_dest = airport_data_access.get_country_by_airport_iata(iata_d)
    city_org = airport_data_access.get_city_by_airport_iata(iata_o)
    city_dest = airport_data_access.get_city_by_airport_iata(iata_d)
    end_time = time.time()
    logging.info(f"Time for fetching location data: {end_time - start_time:.2f} seconds")
    start_time = time.time()
    similar_passengers = perform_similarity_search(firstname, surname, name, iata_o, lat_o, lon_o, city_org, ctry_org, iata_d, lat_d, lon_d, city_dest, ctry_dest, dob, city_name, lat_c, lon_c, country, nationality, sex, address, all_data, nameThreshold, ageThreshold, locationThreshold)
    end_time = time.time()
    logging.info(f"Time for similarity search: {end_time - start_time:.2f} seconds")
    logging.info(f"similar_passengers shape: {similar_passengers.shape}")
    similar_passengers.replace([np.inf, -np.inf, np.nan], None, inplace=True)
    return similar_passengers

def perform_similarity_search(firstname, surname, name, iata_o, lat_o, lon_o, city_org, ctry_org, iata_d, lat_d, lon_d, city_dest, ctry_dest, dob, city_name, lat_c, lon_c, country,  nationality, sex, address, df, nameThreshold, ageThreshold, locationThreshold):
    similar_items = []
    max_distance = 12000
    similarity_df = pd.DataFrame()
    num_records = df.shape[0]
    model_path = 'model/f1_xgboost_model.joblib'
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'unique_id'}, inplace=True)

    start_time = time.time()
    gender_counts = df['Sex'].str.lower().value_counts(normalize=True)
    origin_airport_counts = df['OriginIATA'].str.lower().value_counts(normalize=True)
    origin_city_counts = df['OriginCity'].str.lower().value_counts(normalize=True)
    origin_country_counts = df['OriginCountry'].str.lower().value_counts(normalize=True)
    destination_airport_counts = df['DestinationIATA'].str.lower().value_counts(normalize=True)
    destination_city_counts = df['DestinationCity'].str.lower().value_counts(normalize=True)
    destination_country_counts = df['DestinationCountry'].str.lower().value_counts(normalize=True)
    city_address_counts = df['CityName'].str.lower().value_counts(normalize=True)
    country_address_counts = df['Country of Address'].str.lower().value_counts(normalize=True)
    nationality_counts = df['Nationality'].str.lower().value_counts(normalize=True)
    DOB_counts = df['DOB'].value_counts(normalize=True)
    firstname_counts = df['Firstname'].str.lower().value_counts(normalize=True)
    surname_counts = df['Surname'].str.lower().value_counts(normalize=True)
    end_time = time.time()
    logging.info(f"Time for calculating counts: {end_time - start_time:.2f} seconds")
    logging.info(f"Counts calculated")

    if nameThreshold>50 and ageThreshold>50:
        df = data_filtration(df, nameThreshold, ageThreshold, firstname, surname, dob)


    start_time = time.time()
    similarity_df[['FNSimilarity', 'FN1', 'FN2', 'FN_rarity1', 'FN_rarity2', 'FN_prob1', 'FN_prob2']] = pd.DataFrame(df['Firstname'].map(lambda x: string_similarity(firstname, x, firstname_counts, num_records)).tolist(), index=df.index)
    similarity_df[['SNSimilarity', 'SN1', 'SN2', 'SN_rarity1', 'SN_rarity2', 'SN_prob1', 'SN_prob2']] = pd.DataFrame(df['Surname'].map(lambda x: string_similarity(surname, x, surname_counts, num_records)).tolist(), index=df.index)
    similarity_df[['DOBSimilarity', 'DOB1', 'DOB2', 'DOB_rarity1', 'DOB_rarity2', 'DOB_prob1', 'DOB_prob2']] = pd.DataFrame(df['DOB'].map(lambda x: string_similarity(dob, x, DOB_counts, num_records)).tolist(), index=df.index)
    similarity_df['AgeSimilarity'] = df['DOB'].map(lambda x: age_similarity_score(dob, x))
    similarity_df[['strAddressSimilarity', 'jcdAddressSimilarity']] = pd.DataFrame(df['Address'].map(lambda x: address_str_similarity_score(address, x)).tolist(), index=df.index)
    similarity_df['cityAddressMatch'] = df['CityName'].map(lambda x: location_matching(city_name, x))
    similarity_df[['cityAddressRarity1', 'cityAddressProb1']] = count_likelihood2(city_name, city_address_counts, num_records)
    similarity_df[['cityAddressRarity2', 'cityAddressProb2']] = pd.DataFrame(df['CityName'].map(lambda x: count_likelihood2(x, city_address_counts, num_records)).tolist(), index=df.index)
    similarity_df['countryAddressMatch'] = df['Country of Address'].map(lambda x: location_matching(country, x))
    # similarity_df[['countryAddressRarity1', 'countryAddressProb1']] = count_likelihood2(country, country_address_counts, num_records)
    similarity_df[['countryAddressRarity2', 'countryAddressProb2']] = pd.DataFrame(df['Country of Address'].map(lambda x: count_likelihood2(x, country_address_counts, num_records)).tolist(), index=df.index)
    similarity_df['sexMatch'] = df['Sex'].map(lambda x: location_matching(sex, x))
    # similarity_df[['sexRarity1', 'sexProb1']] = count_likelihood2(sex, gender_counts, num_records)
    similarity_df[['sexRarity2', 'sexProb2']] = pd.DataFrame(df['Sex'].map(lambda x: count_likelihood2(x, gender_counts, num_records)).tolist(), index=df.index)
    similarity_df['natMatch'] = df['Nationality'].map(lambda x: location_matching(nationality, x))
    # similarity_df[['natRarity1', 'natProb1']] = count_likelihood2(nationality, nationality_counts, num_records)
    similarity_df[['natRarity2', 'natProb2']] = pd.DataFrame(df['Nationality'].map(lambda x: count_likelihood2(x, nationality_counts, num_records)).tolist(), index=df.index)
    similarity_df['originAirportMatch'] = df['OriginIATA'].map(lambda x: location_matching(iata_o, x))
    # similarity_df[['originAirportRarity1', 'originAirportProb1']] = count_likelihood2(iata_o, origin_airport_counts, num_records)
    similarity_df[['originAirportRarity2', 'originAirportProb2']] = pd.DataFrame(df['OriginIATA'].map(lambda x: count_likelihood2(x, origin_airport_counts, num_records)).tolist(), index=df.index)
    similarity_df['destinationAirportMatch'] = df['DestinationIATA'].map(lambda x: location_matching(iata_d, x))
    # similarity_df[['destinationAirportRarity1', 'destinationAirportProb1']] = count_likelihood2(iata_o, origin_airport_counts, num_records)
    similarity_df[['destinationAirportRarity2', 'destinationAirportProb2']] = pd.DataFrame(df['DestinationIATA'].map(lambda x: count_likelihood2(x, destination_airport_counts, num_records)).tolist(), index=df.index)
    similarity_df['orgdesAirportMatch'] = df['OriginIATA'].map(lambda x: location_matching(iata_d, x))
    similarity_df['desorgAirportMatch'] = df['DestinationIATA'].map(lambda x: location_matching(iata_o, x))
    similarity_df['originCityMatch'] = df['OriginCity'].map(lambda x: location_matching(city_org, x))
    # similarity_df[['originCityRarity1', 'originCityProb1']] = count_likelihood2(city_org, origin_city_counts, num_records)
    similarity_df[['originCityRarity2', 'originCityProb2']] = pd.DataFrame(df['OriginCity'].map(lambda x: count_likelihood2(x, origin_city_counts, num_records)).tolist(), index=df.index)
    similarity_df['destinationCityMatch'] = df['DestinationCity'].map(lambda x: location_matching(city_dest, x))
    # similarity_df[['destinationCityRarity1', 'destinationCityProb1']] = count_likelihood2(city_dest, destination_city_counts, num_records)
    similarity_df[['destinationCityRarity2', 'destinationCityProb2']] = pd.DataFrame(df['DestinationCity'].map(lambda x: count_likelihood2(x, destination_city_counts, num_records)).tolist(), index=df.index)
    similarity_df['orgdesCityMatch'] = df['OriginCity'].map(lambda x: location_matching(city_dest, x))
    similarity_df['desorgCityMatch'] = df['DestinationCity'].map(lambda x: location_matching(city_org, x))
    similarity_df['originCountryMatch'] = df['OriginCountry'].map(lambda x: location_matching(ctry_org, x))
    # similarity_df[['originCountryRarity1', 'originCountryProb1']] = count_likelihood2(ctry_org, origin_country_counts, num_records)
    similarity_df[['originCountryRarity2', 'originCountryProb2']] = pd.DataFrame(df['OriginCountry'].map(lambda x: count_likelihood2(x, origin_country_counts, num_records)).tolist(), index=df.index)
    similarity_df['destinationCountryMatch'] = df['DestinationCountry'].map(lambda x: location_matching(ctry_dest, x))
    # similarity_df[['destinationCountryRarity1', 'destinationCountryProb1']] = count_likelihood2(ctry_dest, destination_country_counts, num_records)
    similarity_df[['destinationCountryRarity2', 'destinationCountryProb2']] = pd.DataFrame(df['DestinationCountry'].map(lambda x: count_likelihood2(x, destination_country_counts, num_records)).tolist(), index=df.index)
    similarity_df['orgdesCountryMatch'] = df['OriginCountry'].map(lambda x: location_matching(ctry_dest, x))
    similarity_df['desorgCountryMatch'] = df['DestinationCountry'].map(lambda x: location_matching(ctry_org, x))
    similarity_df[['originSimilarity', 'originExpScore']] = df.apply(lambda row: location_similarity_score(lon_o, lat_o, row['OriginLon'], row['OriginLat'], max_distance), axis=1, result_type='expand')
    similarity_df[['destinationSimilarity', 'destinationExpScore']] = df.apply(lambda row: location_similarity_score(lon_d, lat_d, row['DestinationLon'], row['DestinationLat'], max_distance), axis=1, result_type='expand')
    similarity_df[['orgdesSimilarity', 'orgdesExpScore']] = df.apply(lambda row: location_similarity_score(lon_o, lat_o, row['DestinationLon'], row['DestinationLat'], max_distance), axis=1, result_type='expand')
    similarity_df[['desorgSimilarity', 'desorgExpScore']] = df.apply(lambda row: location_similarity_score(lon_d, lat_d, row['OriginLon'], row['OriginLat'], max_distance), axis=1, result_type='expand')
    end_time = time.time()
    logging.info(f"Time for calculating similarities: {end_time - start_time:.2f} seconds")

    similarity_df.reset_index(inplace=True)
    similarity_df.rename(columns={'index': 'unique_id'}, inplace=True)
    expected_columns = ['FNSimilarity', 'FN_rarity1', 'FN_rarity2', 'FN_prob1', 'FN_prob2', 
                    'SNSimilarity', 'SN_rarity1', 'SN_rarity2', 'SN_prob1', 'SN_prob2', 'DOBSimilarity', 'DOB_rarity1', 'DOB_rarity2', 'DOB_prob1', 'DOB_prob2',
                    'AgeSimilarity', 'strAddressSimilarity', 'jcdAddressSimilarity', 'cityAddressMatch', 'cityAddressRarity1', 
                    'cityAddressProb1', 'cityAddressRarity2', 'cityAddressProb2', 'countryAddressMatch', 
                    'countryAddressRarity1', 'countryAddressProb1', 'countryAddressRarity2', 'countryAddressProb2', 
                    'sexMatch', 'sexRarity1', 'sexProb1', 'sexRarity2', 'sexProb2', 'natMatch', 
                    'natRarity1', 'natProb1', 'natRarity2', 'natProb2', 'originAirportMatch', 
                    'originAirportRarity1', 'originAirportProb1', 'originAirportRarity2', 'originAirportProb2', 
                    'destinationAirportMatch', 'destinationAirportRarity1', 'destinationAirportProb1', 
                    'destinationAirportRarity2', 'destinationAirportProb2', 'orgdesAirportMatch', 
                    'desorgAirportMatch', 'originCityMatch', 'originCityRarity1', 'originCityProb1', 
                    'originCityRarity2', 'originCityProb2', 'destinationCityMatch', 'destinationCityRarity1', 
                    'destinationCityProb1', 'destinationCityRarity2', 'destinationCityProb2', 'orgdesCityMatch', 
                    'desorgCityMatch', 'originCountryMatch', 'originCountryRarity1', 'originCountryProb1', 
                    'originCountryRarity2', 'originCountryProb2', 'destinationCountryMatch', 'destinationCountryRarity1', 
                    'destinationCountryProb1', 'destinationCountryRarity2', 'destinationCountryProb2', 'orgdesCountryMatch', 
                    'desorgCountryMatch', 'originSimilarity', 'originExpScore', 'destinationSimilarity', 
                    'destinationExpScore', 'orgdesSimilarity', 'orgdesExpScore', 'desorgSimilarity', 'desorgExpScore']
    coldrop = ['Class', 'Mark',
               'unique_id']
    test = similarity_df.drop(columns=coldrop, errors='ignore')
    logging.info(f"test shape: {test.shape}")
    logging.info(f"similarity_df shape: {similarity_df.shape}")
    # logging.info(f"expected_columns: {expected_columns}")
    # logging.info(f"test columns: {test.columns}")
    for col in expected_columns:
        if col not in test.columns:
            test[col] = 0  # or some default value

    # Reorder the DataFrame columns
    test = test[expected_columns]

    model = joblib.load(model_path)
    logging.info(f"Loading model from {model_path}")
    feature_importances = model.feature_importances_
    normalised_importances = feature_importances / np.sum(feature_importances)

    logging.info(f"similarity_df shape: {similarity_df.shape}, normalised_importances len: {len(normalised_importances)}")
    extra_columns = [col for col in similarity_df.columns if col not in expected_columns and col not in ['unique_id']]
    logging.info(f"Extra columns in similarity_df: {extra_columns}")

    # Create a DataFrame for relevant columns
    relevant_similarities = test[expected_columns].copy()
    logging.info(f"relevant_similarities shape: {relevant_similarities.shape}")
    relevant_similarities = relevant_similarities.multiply(normalised_importances, axis=1)
    # relevant_similarities = relevant_similarities.applymap(lambda x: np.round(x, 3) if isinstance(x, (int, float)) else x)


    logging.info(f"predicted")
    start_time = time.time()
    df['Confidence Level'] = model.predict_proba(test)[:, 1]*100
    similarity_df['Compound Similarity Score'] = relevant_similarities.sum(axis=1)
    result_df = pd.merge(df, similarity_df, on='unique_id', how='inner')
    result_df = result_df.applymap(lambda x: np.round(x, 4) if isinstance(x, (int, float)) else x)
    end_time = time.time()
    logging.info(f"Time for calculating compound similarity and ML Model: {end_time - start_time:.2f} seconds")
    logging.info(f"result_df shape: {result_df.shape}")
    nameThreshold = float(nameThreshold) if nameThreshold else 0
    ageThreshold = float(ageThreshold) if ageThreshold else 0
    locationThreshold = float(locationThreshold) if locationThreshold else 0


    filtered_result_df = result_df[(result_df['FNSimilarity'] >= nameThreshold) &
                        (result_df['SNSimilarity'] >= nameThreshold) &
                        (result_df['AgeSimilarity'] >= ageThreshold) & 
                        (result_df['Compound Similarity Score'] >= 10) &
                        (result_df['Confidence Level'] >= 1)
                        ]
    
    # filtered_result_df = result_df[(result_df['FNSimilarity'] >= nameThreshold) &
    #                     (result_df['SNSimilarity'] >= nameThreshold) &
    #                     (result_df['AgeSimilarity'] >= ageThreshold)]

    # filtered_result_df = result_df.sort_values(by = ['Confidence Level', 'Compound Similarity Score'], ascending = False).head(10)
    
    filtered_result_df = filtered_result_df.copy()
    filtered_result_df.drop_duplicates(subset=['PassengerID', 'DOB', 'PNRID', 'iata_pnrgov_notif_rq_id', 'TravelDocNumber', 'FlightNumber', 'OriginatorAirlineCode', 
                                               'DepartureDateTime', 'ArrivalDateTime', 'FlightLegFlightNumber'], inplace=True)
    # filtered_result_df.to_csv('test/filtered_resilt_df.csv')
    filtered_result_df.sort_values(by = ['Confidence Level', 'Compound Similarity Score'], ascending = False, inplace = True)
    logging.info(f"Filtered result shape: {filtered_result_df.shape}")
    # filtered_result_df.to_csv('filtered_result_df.csv')
    return filtered_result_df


def data_filtration(df, nameThreshold, ageThreshold, firstname, surname, dob):
    if nameThreshold == 100:
        df = df[(df['Firstname'].str.lower() == firstname.lower()) & 
                (df['Surname'].str.lower() == surname.lower())]
    elif nameThreshold < 100:
        df = df[(df['Firstname'].str.startswith(firstname[0].lower()) | 
                 df['Firstname'].str.startswith(surname[0].lower())) &
                (df['Surname'].str.startswith(firstname[0].lower()) | 
                 df['Surname'].str.startswith(surname[0].lower()))]

    if ageThreshold == 100:
        df = df[df['DOB'] == dob]

    return df

        




def parse_xml(file_path):
    logging.info(f"Parsing XML file: {file_path}")
    airport_data_access = LocDataAccess.get_instance()  # Access the singleton instance
    # xml_content = download_from_blob_storage(file_path)  # Download XML content from Azure Blob Storage
    xml_content = download_from_local_storage(file_path)  # Download XML content from local storage
    logging.info(f"ready to parse: {file_path}")
    logging.info(f"xml_content: {xml_content}")
    root = ET.fromstring(xml_content)
    logging.info(f"rooting success: {root}")
    data = []

    origin_code = root.find('.//FlightLeg/DepartureAirport').get('LocationCode') if root.find('.//FlightLeg/DepartureAirport') is not None else None
    destination_code = root.find('.//FlightLeg/ArrivalAirport').get('LocationCode') if root.find('.//FlightLeg/ArrivalAirport') is not None else None
    origin_lon, origin_lat = airport_data_access.get_airport_lon_lat_by_iata(origin_code) if origin_code else (None, None)
    destination_lon, destination_lat = airport_data_access.get_airport_lon_lat_by_iata(destination_code) if destination_code else (None, None)

    for pnr in root.findall('.//PNR'):
        bookID = pnr.find('.//BookingRefID').get('ID') if pnr.find('.//BookingRefID') is not None else 'Unknown'
        for passenger in pnr.findall('.//Passenger'):
            firstname = passenger.find('.//GivenName').text.strip()
            surname = passenger.find('.//Surname').text.strip()
            name = f"{firstname} {surname}"
            travel_doc_nbr = passenger.find('.//DOC_SSR/DOCO').get('TravelDocNbr') if passenger.find('.//DOC_SSR/DOCO') is not None else 'Unknown'
            place_of_issue = passenger.find('.//DOC_SSR/DOCO').get('PlaceOfIssue') if passenger.find('.//DOC_SSR/DOCO') is not None else 'Unknown'
            date_of_birth = passenger.find('.//DOC_SSR/DOCS').get('DateOfBirth') if passenger.find('.//DOC_SSR/DOCS') is not None else 'Unknown'
            nationality = passenger.find('.//DOC_SSR/DOCS').get('PaxNationality') if passenger.find('.//DOC_SSR/DOCS') is not None else 'Unknown'
            sex = passenger.find('.//DOC_SSR/DOCS').get('Gender') if passenger.find('.//DOC_SSR/DOCS') is not None else 'Unknown'
            city_name = passenger.find('.//DOC_SSR/DOCA').get('CityName') if passenger.find('.//DOC_SSR/DOCA') is not None else None
            address = passenger.find('.//DOC_SSR/DOCA').get('Address') if passenger.find('.//DOC_SSR/DOCA') is not None else None
            
            city_lat, city_lon = airport_data_access.get_airport_lon_lat_by_city(city_name) if city_name else (None, None)
            city_org = airport_data_access.get_city_by_airport_iata(origin_code) if origin_code else (None)
            city_dest = airport_data_access.get_city_by_airport_iata(destination_code) if destination_code else (None)
            ctry_org = airport_data_access.get_country_by_airport_iata(origin_code) if origin_code else (None)
            ctry_dest = airport_data_access.get_country_by_airport_iata(destination_code) if destination_code else (None)
            country_of_address = airport_data_access.get_country_by_city(city_name) if city_name else (None)

            data.append((file_path, bookID, firstname, surname, name, travel_doc_nbr, place_of_issue, origin_code, city_org, ctry_org, origin_lat, origin_lon, destination_code, city_dest, ctry_dest, destination_lat, destination_lon, date_of_birth, city_name, city_lat, city_lon, address,  country_of_address, nationality, sex))
    
    columns = ['FilePath', 'BookingID', 'Firstname', 'Surname', 'Name', 'Travel Doc Number', 'Place of Issue', 'OriginIATA', 'OriginCity', 'OriginCountry', 'OriginLat', 'OriginLon', 'DestinationIATA', 'DestinationCity', 'DestinationCountry', 'DestinationLat', 'DestinationLon', 'DOB', 'CityName', 'CityLat', 'CityLon', 'Address', 'Country of Address', 'Nationality', 'Sex']
    df = pd.DataFrame(data, columns=columns)
    return df

