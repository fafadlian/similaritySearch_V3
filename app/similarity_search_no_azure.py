from fuzzywuzzy import fuzz
import xml.etree.ElementTree as ET
import os
import glob
import pandas as pd
import numpy as np
import string
import joblib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

from app.data_loader import load_json_data
from app.loc_access import LocDataAccess
from app.location_similarity import haversine, location_similarity_score, location_matching, address_str_similarity_score
from app.age_similarity import age_similarity_score, calculate_age
from app.base_similarity import count_likelihood2, string_similarity
# from obstructor import introduce_dob_typos, introduce_error_airport, introduce_error_nat_city, introduce_error_sex, introduce_typos, update_loc_airport



# Firstname = 'Jamie'
# Surname = 'Smooth'
# name_comb = Firstname + ' ' + Surname
# OriginIATA = 'DXB'
# DestinationIATA = 'AMS' 
# DOB_q = '1973-05-22'
# CityName = 'DUBAI'
# Nationality = 'PYF'
# Sex = 'M'
# Address = '41658 Mckinney Ridges Apartment no. 270 Shawmouth, Wyoming 27446'


def process_files_in_parallel(json_files):
    all_data = pd.DataFrame()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(parse_json, file_path): file_path for file_path in json_files}
        for future in as_completed(futures):
            file_path = futures[future]
            try:
                data = future.result()
                all_data = pd.concat([all_data, data], ignore_index=True)
            except Exception as e:
                print(f"An error occurred while processing {file_path}: {e}")
    all_data.to_csv('parsedJSON_PNR.csv', index = False)
    return all_data



def find_similar_passengers(airport_data_access, firstname, surname, name, dob, iata_o, iata_d, city_name, address, sex, nationality, xml_dir, nameThreshold, ageThreshold, locationThreshold):
    airport_data_access = LocDataAccess.get_instance()  # Access the singleton instance
    all_data = pd.DataFrame()
    similar_passengers = pd.DataFrame()
    name_comb = firstname+" "+surname
    # List all XML files in the directory
    # print("name_comb: ", name_comb, " name: ,", name)
    xml_files = glob.glob(os.path.join(xml_dir, '*.xml'))
    json_files = glob.glob(os.path.join(xml_dir, '*.json'))

    logging.info(f"find_similar_passengers: xml_files={xml_files}")

    # Parse each XML file and aggregate data
    for file_path in xml_files:
        data = parse_xml(file_path)
        all_data = pd.concat([all_data, data], ignore_index=True)

    # Parse each JSON file and aggregate data
    # for file_path in json_files:
    #     data = parse_json(file_path)
    #     all_data = pd.concat([all_data, data], ignore_index=True)

    # Process all JSON files in parallel
    # all_data = process_files_in_parallel(json_files)


    # Perform similarity search on the aggregated data
    lon_o, lat_o = airport_data_access.get_airport_lon_lat_by_iata(iata_o)
    lon_d, lat_d = airport_data_access.get_airport_lon_lat_by_iata(iata_d)
    lon_c, lat_c = airport_data_access.get_airport_lon_lat_by_city(city_name)
    country = airport_data_access.get_country_by_city(city_name)
    ctry_org = airport_data_access.get_country_by_airport_iata(iata_o)
    ctry_dest = airport_data_access.get_country_by_airport_iata(iata_d)
    city_org = airport_data_access.get_city_by_airport_iata(iata_o)
    city_dest = airport_data_access.get_city_by_airport_iata(iata_d)
    similar_passengers = perform_similarity_search(firstname, surname, name, iata_o, lat_o, lon_o, city_org, ctry_org, iata_d, lat_d, lon_d, city_dest, ctry_dest, dob, city_name, lat_c, lon_c, country,  nationality, sex, address, all_data, nameThreshold, ageThreshold, locationThreshold)

    # Replace NaN and infinite values
    similar_passengers.replace([np.inf, -np.inf, np.nan], None, inplace=True)
    # similar_passengers.fillna('', inplace=True)

    return similar_passengers

def is_series(value):
    return isinstance(value, pd.Series)


def perform_similarity_search(firstname, surname, name, iata_o, lat_o, lon_o, city_org, ctry_org, iata_d, lat_d, lon_d, city_dest, ctry_dest, dob, city_name, lat_c, lon_c, country,  nationality, sex, address, df, nameThreshold, ageThreshold, locationThreshold):
    similar_items = []
    max_distance = 20037.5
    similarity_df = pd.DataFrame()
    num_records = df.shape[0]
    model_path = 'model/None_xgboost_model.joblib'
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'unique_id'}, inplace=True)

    if firstname is None:
        firstname = ''
    if surname is None:
        surname = ''
    if name is None:
        name = ''
    if iata_o is None:
        iata_o = ''
    if city_org is None:
        city_org = ''
    if ctry_org is None:
        ctry_org = ''
    if iata_d is None:
        iata_d = ''
    if city_dest is None:
        city_dest = ''
    if ctry_dest is None:
        ctry_dest = ''
    if dob is None:
        dob = ''
    if city_name is None:
        city_name = ''
    if country is None:
        country = ''
    if nationality is None:
        nationality = ''
    if sex is None:
        sex = ''
    if address is None:
        address = ''
    if nameThreshold is None:
        nameThreshold = 0.0
    if ageThreshold is None:
        ageThreshold = 0.0
    if locationThreshold is None:
        locationThreshold = 0.0

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
    filtered_result_df.reset_index(drop=True, inplace=True)
    # filtered_result_df.to_csv('filtered_result_df.csv', index=False)
    # filtered_result_df.to_csv('filtered_result_df.csv')
    return filtered_result_df

def parse_xml(file_path):
    airport_data_access = LocDataAccess.get_instance()  # Access the singleton instance

    tree = ET.parse(file_path)
    root = tree.getroot()

    data = []
    # Fetch the IATA codes
    origin_code = root.find('.//FlightLeg/DepartureAirport').get('LocationCode') if root.find('.//FlightLeg/DepartureAirport') is not None else None
    destination_code = root.find('.//FlightLeg/ArrivalAirport').get('LocationCode') if root.find('.//FlightLeg/ArrivalAirport') is not None else None

    # Use LocDataAccess to get lat/lon for origin and destination
    origin_lon, origin_lat = airport_data_access.get_airport_lon_lat_by_iata(origin_code) if origin_code else (None, None)
    destination_lon, destination_lat = airport_data_access.get_airport_lon_lat_by_iata(destination_code) if destination_code else (None, None)

    for pnr in root.findall('.//PNR'):
        bookID = pnr.find('.//BookingRefID').get('ID') if pnr.find('.//BookingRefID') is not None else 'Unknown'
        for passenger in pnr.findall('.//Passenger'):
            firstname = passenger.find('.//GivenName').text.strip()
            surname = passenger.find('.//Surname').text.strip()
            name = passenger.find('.//GivenName').text.strip() + ' ' + passenger.find('.//Surname').text.strip()
            travel_doc_nbr = passenger.find('.//DOC_SSR/DOCO').get('TravelDocNbr') if passenger.find('.//DOC_SSR/DOCO') is not None else 'Unknown'
            place_of_issue = passenger.find('.//DOC_SSR/DOCO').get('PlaceOfIssue') if passenger.find('.//DOC_SSR/DOCO') is not None else 'Unknown'
            date_of_birth = passenger.find('.//DOC_SSR/DOCS').get('DateOfBirth') if passenger.find('.//DOC_SSR/DOCS') is not None else 'Unknown'
            nationality = passenger.find('.//DOC_SSR/DOCS').get('PaxNationality') if passenger.find('.//DOC_SSR/DOCS') is not None else 'Unknown'
            sex = passenger.find('.//DOC_SSR/DOCS').get('Gender') if passenger.find('.//DOC_SSR/DOCS') is not None else 'Unknown'
            city_name = passenger.find('.//DOC_SSR/DOCA').get('CityName') if passenger.find('.//DOC_SSR/DOCA') is not None else None
            address = passenger.find('.//DOC_SSR/DOCA').get('Address') if passenger.find('.//DOC_SSR/DOCA') is not None else None
            
            
            
            # Get lat/lon for the city
            city_lat, city_lon = airport_data_access.get_airport_lon_lat_by_city(city_name) if city_name else (None, None)
            city_org = airport_data_access.get_city_by_airport_iata(origin_code) if origin_code else (None)
            city_dest = airport_data_access.get_city_by_airport_iata(destination_code) if destination_code else (None)
            ctry_org = airport_data_access.get_country_by_airport_iata(origin_code) if origin_code else (None)
            ctry_dest = airport_data_access.get_country_by_airport_iata(destination_code) if destination_code else (None)
            country_of_address = airport_data_access.get_country_by_city(city_name) if city_name else (None)

            # Append data including lat/lon for origin, destination, and city
            data.append((file_path, bookID, firstname, surname, name, travel_doc_nbr, place_of_issue, origin_code, city_org, ctry_org, origin_lat, origin_lon, destination_code, city_dest, ctry_dest, destination_lat, destination_lon, date_of_birth, city_name, city_lat, city_lon, address,  country_of_address, nationality, sex))
    columns = ['FilePath', 'BookingID', 'Firstname', 'Surname', 'Name', 'Travel Doc Number', 'Place of Issue', 'OriginIATA', 'OriginCity', 'OriginCountry', 'OriginLat', 'OriginLon', 'DestinationIATA', 'DestinationCity', 'DestinationCountry', 'DestinationLat', 'DestinationLon', 'DOB', 'CityName', 'CityLat', 'CityLon', 'Address', 'Country of Address', 'Nationality', 'Sex']
    df = pd.DataFrame(data, columns=columns)
    # df.to_csv('parsedXML.csv', index = False)
    return df

def parse_json(file_path):
    airport_data_access = LocDataAccess.get_instance()  # Access the singleton instance

    with open(file_path, 'r') as file:
        data = json.load(file)

    flight_data = data['iata_pnrgov_notif_rq_obj']
    origin_code = flight_data.get('flight_leg_departure_airp_location_code')
    destination_code = flight_data.get('flight_leg_arrival_airp_location_code')

    # Use LocDataAccess to get lat/lon for origin and destination
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
            
            # Get lat/lon for the city
            city_lat, city_lon = airport_data_access.get_airport_lon_lat_by_city(city_name) if city_name else (None, None)
            city_org = airport_data_access.get_city_by_airport_iata(origin_code) if origin_code else (None)
            city_dest = airport_data_access.get_city_by_airport_iata(destination_code) if destination_code else (None)
            ctry_org = airport_data_access.get_country_by_airport_iata(origin_code) if origin_code else (None)
            ctry_dest = airport_data_access.get_country_by_airport_iata(destination_code) if destination_code else (None)
            country_of_address = airport_data_access.get_country_by_city(city_name) if city_name else (None)

            # Append data including lat/lon for origin, destination, and city
            data_list.append((file_path, bookID, firstname, surname, name, travel_doc_nbr, place_of_issue, origin_code, city_org, ctry_org, origin_lat, origin_lon, destination_code, city_dest, ctry_dest, destination_lat, destination_lon, date_of_birth, city_name, city_lat, city_lon, address,  country_of_address, nationality, sex))

    columns = ['FilePath', 'BookingID', 'Firstname', 'Surname', 'Name', 'Travel Doc Number', 'Place of Issue', 'OriginIATA', 'OriginCity', 'OriginCountry', 'OriginLat', 'OriginLon', 'DestinationIATA', 'DestinationCity', 'DestinationCountry', 'DestinationLat', 'DestinationLon', 'DOB', 'CityName', 'CityLat', 'CityLon', 'Address', 'Country of Address', 'Nationality', 'Sex']
    df = pd.DataFrame(data_list, columns=columns)
    return df



# Example usage
# user_query = 'Chris James'
# directory = 'XMLs'
# data, no_similar = find_similar_passengers(user_query, directory)
# print(data)
# print(no_similar)
