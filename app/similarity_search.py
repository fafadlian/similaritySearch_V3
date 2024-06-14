import os
import requests
import json
import pandas as pd
import joblib

import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.data_loader import load_json_data
from app.loc_access import LocDataAccess
from app.location_similarity import haversine, location_similarity_score, location_matching, address_str_similarity_score
from app.age_similarity import age_similarity_score, calculate_age
from app.base_similarity import count_likelihood2, string_similarity
from app.azure_blob_storage import upload_to_blob_storage, download_from_blob_storage, delete_all_files_in_directory
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import logging

logging.basicConfig(level=logging.INFO)


AZURE_STORAGE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
CONTAINER_NAME = os.getenv('CONTAINER_NAME')

blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)



def parse_xml(file_path):
    logging.info(f"Parsing XML file: {file_path}")
    airport_data_access = LocDataAccess.get_instance()  # Access the singleton instance
    xml_content = download_from_blob_storage(file_path)  # Download XML content from Azure Blob Storage
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

def parse_json(file_path):
    airport_data_access = LocDataAccess.get_instance()  # Access the singleton instance
    json_content = download_from_blob_storage(file_path)  # Download JSON content from Azure Blob Storage
    data = json.loads(json_content)

    flight_data = data['iata_pnrgov_notif_rq_obj']
    origin_code = flight_data.get('flight_leg_departure_airp_location_code')
    destination_code = flight_data.get('flight_leg_arrival_airp_location_code')
    origin_lon, origin_lat = airport_data_access.get_airport_lon_lat_by_iata(origin_code) if origin_code else (None, None)
    destination_lon, destination_lat = airport_data_access.get_airport_lon_lat_by_iata(destination_code) if destination_code else (None, None)

    data_list = []

    for pnr in flight_data['pnr_obj']:
        bookID = pnr.get('booking_refid', 'Unknown')
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

            data_list.append((file_path, bookID, firstname, surname, name, travel_doc_nbr, place_of_issue, origin_code, city_org, ctry_org, origin_lat, origin_lon, destination_code, city_dest, ctry_dest, destination_lat, destination_lon, date_of_birth, city_name, city_lat, city_lon, address,  country_of_address, nationality, sex))

    columns = ['FilePath', 'BookingID', 'Firstname', 'Surname', 'Name', 'Travel Doc Number', 'Place of Issue', 'OriginIATA', 'OriginCity', 'OriginCountry', 'OriginLat', 'OriginLon', 'DestinationIATA', 'DestinationCity', 'DestinationCountry', 'DestinationLat', 'DestinationLon', 'DOB', 'CityName', 'CityLat', 'CityLon', 'Address', 'Country of Address', 'Nationality', 'Sex']
    df = pd.DataFrame(data_list, columns=columns)
    return df

def find_similar_passengers(airport_data_access, firstname, surname, name, dob, iata_o, iata_d, city_name, address, sex, nationality, xml_dir, nameThreshold, ageThreshold, locationThreshold):
    airport_data_access = LocDataAccess.get_instance()  # Access the singleton instance
    all_data = pd.DataFrame()
    similar_passengers = pd.DataFrame()
    name_comb = firstname + " " + surname

    # List all XML files in the directory
    logging.info(f"Searching for XML files in the directory {xml_dir}")
    xml_files = [blob.name for blob in blob_service_client.get_container_client(CONTAINER_NAME).list_blobs(name_starts_with=xml_dir) if blob.name.endswith('.xml')]
    logging.info(f"Found {len(xml_files)} XML files in the directory")
    # json_files = [blob.name for blob in blob_service_client.get_container_client(CONTAINER_NAME).list_blobs(name_starts_with=xml_dir) if blob.name.endswith('.json')]

    # Parse each XML file and aggregate data
    for file_path in xml_files:
        data = parse_xml(file_path)
        all_data = pd.concat([all_data, data], ignore_index=True)

    logging.info(f"all_data shape: {all_data.shape}")

    # Parse each JSON file and aggregate data
    # for file_path in json_files:
    #     data = parse_json(file_path)
    #     all_data = pd.concat([all_data, data], ignore_index=True)

    # Perform similarity search on the aggregated data
    lon_o, lat_o = airport_data_access.get_airport_lon_lat_by_iata(iata_o)
    lon_d, lat_d = airport_data_access.get_airport_lon_lat_by_iata(iata_d)
    lon_c, lat_c = airport_data_access.get_airport_lon_lat_by_city(city_name)
    country = airport_data_access.get_country_by_city(city_name)
    ctry_org = airport_data_access.get_country_by_airport_iata(iata_o)
    ctry_dest = airport_data_access.get_country_by_airport_iata(iata_d)
    city_org = airport_data_access.get_city_by_airport_iata(iata_o)
    city_dest = airport_data_access.get_city_by_airport_iata(iata_d)
    similar_passengers = perform_similarity_search(firstname, surname, name, iata_o, lat_o, lon_o, city_org, ctry_org, iata_d, lat_d, lon_d, city_dest, ctry_dest, dob, city_name, lat_c, lon_c, country, nationality, sex, address, all_data, nameThreshold, ageThreshold, locationThreshold)

    return similar_passengers

def perform_similarity_search(firstname, surname, name, iata_o, lat_o, lon_o, city_org, ctry_org, iata_d, lat_d, lon_d, city_dest, ctry_dest, dob, city_name, lat_c, lon_c, country,  nationality, sex, address, df, nameThreshold, ageThreshold, locationThreshold):
    similar_items = []
    max_distance = 20037.5
    similarity_df = pd.DataFrame()
    num_records = df.shape[0]
    model_path = 'model/None_xgboost_model.joblib'
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'unique_id'}, inplace=True)

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


    similarity_df[['FNSimilarity', 'FN1', 'FN2', 'FN_rarity1', 'FN_rarity2', 'FN_prob1', 'FN_prob2']] = df['Firstname'].apply(lambda x: string_similarity(firstname, x, firstname_counts, num_records))
    similarity_df[['SNSimilarity', 'SN1', 'SN2', 'SN_rarity1', 'SN_rarity2', 'SN_prob1', 'SN_prob2']] = df['Surname'].apply(lambda x: string_similarity(surname, x, surname_counts, num_records))
    similarity_df[['DOBSimilarity', 'DOB1', 'DOB2', 'DOB_rarity1', 'DOB_rarity2', 'DOB_prob1', 'DOB_prob2']] = df['DOB'].apply(lambda x: string_similarity(dob, x, DOB_counts, num_records))
    similarity_df['AgeSimilarity']= df['DOB'].apply(lambda x: age_similarity_score(dob, x))
    similarity_df[['strAddressSimilarity', 'jcdAddressSimilarity']] = df['Address'].apply(lambda x: address_str_similarity_score(address, x))
    similarity_df['cityAddressMatch'] = df['CityName'].apply(lambda x: location_matching(city_name, x))
    similarity_df[['cityAddressRarity1', 'cityAddressProb1']] = count_likelihood2(city_name, city_address_counts, num_records)
    similarity_df[['cityAddressRarity2', 'cityAddressProb2']] = df['CityName'].apply(lambda x: count_likelihood2(x, city_address_counts, num_records))
    similarity_df['countryAddressMatch'] = df['Country of Address'].apply(lambda x: location_matching(country, x))
    similarity_df[['countryAddressRarity1', 'countryAddressProb1']] = count_likelihood2(country, country_address_counts, num_records)
    similarity_df[['countryAddressRarity2', 'countryAddressProb2']] = df['Country of Address'].apply(lambda x: count_likelihood2(x, country_address_counts, num_records))
    similarity_df['sexMatch'] = df['Sex'].apply(lambda x: location_matching(sex, x))
    similarity_df[['sexRarity1', 'sexProb1']] = count_likelihood2(sex, gender_counts, num_records)
    similarity_df[['sexRarity2', 'sexProb2']] = df['Sex'].apply(lambda x: count_likelihood2(x, gender_counts, num_records))
    similarity_df['natMatch'] = df['Nationality'].apply(lambda x: location_matching(nationality, x))
    similarity_df[['natRarity1', 'natProb1']] = count_likelihood2(nationality, nationality_counts, num_records)
    similarity_df[['natRarity2', 'natProb2']] = df['Nationality'].apply(lambda x: count_likelihood2(x, nationality_counts, num_records))
    similarity_df['originAirportMatch'] = df['OriginIATA'].apply(lambda x: location_matching(iata_o, x))
    similarity_df[['originAirportRarity1', 'originAirportProb1']] = count_likelihood2(iata_o, origin_airport_counts, num_records)
    similarity_df[['originAirportRarity2', 'originAirportProb2']] = df['OriginIATA'].apply(lambda x: count_likelihood2(x, origin_airport_counts, num_records))
    similarity_df['destinationAirportMatch'] = df['DestinationIATA'].apply(lambda x: location_matching(iata_d, x))
    similarity_df[['destinationAirportRarity1', 'destinationAirportProb1']] = count_likelihood2(iata_o, origin_airport_counts, num_records)
    similarity_df[['destinationAirportRarity2', 'destinationAirportProb2']] = df['DestinationIATA'].apply(lambda x: count_likelihood2(x, destination_airport_counts, num_records))    
    similarity_df['orgdesAirportMatch'] = df['OriginIATA'].apply(lambda x:location_matching(iata_d, x))
    similarity_df['desorgAirportMatch'] = df['DestinationIATA'].apply(lambda x:location_matching(iata_o, x))   
    similarity_df['originCityMatch'] = df['OriginCity'].apply(lambda x: location_matching(city_org, x))
    similarity_df[['originCityRarity1', 'originCityProb1']] = count_likelihood2(city_org, origin_city_counts, num_records)
    similarity_df[['originCityRarity2', 'originCityProb2']] = df['OriginCity'].apply(lambda x: count_likelihood2(x, origin_city_counts, num_records))
    similarity_df['destinationCityMatch'] = df['DestinationCity'].apply(lambda x: location_matching(city_dest, x))
    similarity_df[['destinationCityRarity1', 'destinationCityProb1']] = count_likelihood2(city_dest, destination_city_counts, num_records)
    similarity_df[['destinationCityRarity2', 'destinationCityProb2']] = df['DestinationCity'].apply(lambda x: count_likelihood2(x, destination_city_counts, num_records))    
    similarity_df['orgdesCityMatch'] = df['OriginCity'].apply(lambda x:location_matching(city_dest, x))
    similarity_df['desorgCityMatch'] = df['DestinationCity'].apply(lambda x:location_matching(city_org, x))
    similarity_df['originCountryMatch'] = df['OriginCountry'].apply(lambda x: location_matching(ctry_org, x))
    similarity_df[['originCountryRarity1', 'originCountryProb1']] = count_likelihood2(ctry_org, origin_country_counts, num_records)
    similarity_df[['originCountryRarity2', 'originCountryProb2']] = df['OriginCountry'].apply(lambda x: count_likelihood2(x, origin_country_counts, num_records))
    similarity_df['destinationCountryMatch'] = df['DestinationCountry'].apply(lambda x: location_matching(ctry_dest, x))
    similarity_df[['destinationCountryRarity1', 'destinationCountryProb1']] = count_likelihood2(ctry_dest, destination_country_counts, num_records)
    similarity_df[['destinationCountryRarity2', 'destinationCountryProb2']] = df['DestinationCountry'].apply(lambda x: count_likelihood2(x, destination_country_counts, num_records))   
    similarity_df['orgdesCountryMatch'] = df['OriginCountry'].apply(lambda x:location_matching(ctry_dest, x))
    similarity_df['desorgCountryMatch'] = df['DestinationCountry'].apply(lambda x:location_matching(ctry_org, x))
    similarity_df[['originSimilarity', 'originExpScore']] = df.apply(lambda row: location_similarity_score(lon_o, lat_o, row['OriginLon'], row['OriginLat'], max_distance), axis=1, result_type='expand')
    similarity_df[['destinationSimilarity', 'destinationExpScore']] = df.apply(lambda row: location_similarity_score(lon_d, lat_d, row['DestinationLon'], row['DestinationLat'], max_distance), axis=1, result_type='expand')
    similarity_df[['orgdesSimilarity', 'orgdesExpScore']] = df.apply(lambda row: location_similarity_score(lon_o, lat_o, row['DestinationLon'], row['DestinationLat'], max_distance), axis=1, result_type='expand')
    similarity_df[['desorgSimilarity', 'desorgExpScore']] = df.apply(lambda row: location_similarity_score(lon_d, lat_d, row['OriginLon'], row['OriginLat'], max_distance), axis=1, result_type='expand')
    
    similarity_df.reset_index(inplace=True)
    similarity_df.rename(columns={'index': 'unique_id'}, inplace=True)
    expected_columns = ['FNSimilarity', 'FN_rarity1', 'FN_rarity2', 'FN_prob1', 'FN_prob2', 
                    'SNSimilarity', 'SN_rarity1', 'SN_rarity2', 'SN_prob1', 'SN_prob2', 
                    'AgeSimilarity', 'jcdAddressSimilarity', 'cityAddressMatch', 'cityAddressRarity1', 
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
    coldrop = ['Class', 'Mark', 'DOBSimilarity', 'strAddressSimilarity',
               'DOB_rarity1', 'DOB_rarity2', 'DOB_prob1', 'DOB_prob2',
               'unique_id']
    test = similarity_df.drop(columns=coldrop, errors='ignore')
    for col in expected_columns:
        if col not in test.columns:
            test[col] = 0  # or some default value

    # Reorder the DataFrame columns
    test = test[expected_columns]

    model = joblib.load(model_path)
    predictions = model.predict(test)
    df['predictions'] = predictions
    result_df = pd.merge(df, similarity_df, on='unique_id', how='inner')
    nameThreshold = float(nameThreshold) if nameThreshold else 0
    ageThreshold = float(ageThreshold) if ageThreshold else 0
    locationThreshold = float(locationThreshold) if locationThreshold else 0

    filtered_result_df = result_df[(result_df['FNSimilarity'] >= nameThreshold) &
                        (result_df['SNSimilarity'] >= nameThreshold) &
                        (result_df['AgeSimilarity'] >= ageThreshold)
                        ]
    # filtered_result_df.to_csv('test/filtered_resilt_df.csv')
    filtered_result_df.sort_values(by = ['predictions'], ascending = False, inplace = True)
    # filtered_result_df.to_csv('filtered_result_df.csv')
    return filtered_result_df