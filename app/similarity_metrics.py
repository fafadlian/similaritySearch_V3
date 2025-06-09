import pandas as pd
import numpy as np
from fuzzywuzzy import fuzz
from app.base_similarity import string_similarity, safe_string_similarity
from app.location_similarity import location_similarity_score, address_str_similarity_score, location_matching
from app.age_similarity import age_similarity_score, dob_string_similarity
from app.loc_access import LocDataAccess
import time
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def compute_similarity_features(df, firstname, surname, dob, address, city_name, country, sex, nationality, iata_o, city_org, ctry_org, iata_d, city_dest, ctry_dest, lat_o, lon_o, lat_d, lon_d, max_distance=2500):
    """
    Computes all similarity features and ensures expected columns exist.
    """
    similarity_df = pd.DataFrame(index=df.index)

    df['OriginCity'] = df['departure_airport'].map(LocDataAccess.get_instance().get_city_by_airport_iata)
    df['DestinationCity'] = df['arrival_airport'].map(LocDataAccess.get_instance().get_city_by_airport_iata)
    df['OriginCountry'] = df['departure_airport'].map(LocDataAccess.get_instance().get_country_by_airport_iata)
    df['DestinationCountry'] = df['arrival_airport'].map(LocDataAccess.get_instance().get_country_by_airport_iata)

    # similarity_df[['FNSimilarity', 'FN1', 'FN2', 'FN_rarity1', 'FN_rarity2', 'FN_prob1', 'FN_prob2']] = pd.DataFrame(df['firstname'].map(lambda x: safe_string_similarity(firstname, x)).tolist(),index=df.index)
    # similarity_df[['SNSimilarity', 'SN1', 'SN2', 'SN_rarity1', 'SN_rarity2', 'SN_prob1', 'SN_prob2']] = pd.DataFrame(df['surname'].map(lambda x: string_similarity(surname, x)).tolist(), index=df.index)
    # similarity_df[['FNSimilarity', 'FN1', 'FN2', 'FN_rarity1', 'FN_rarity2', 'FN_prob1', 'FN_prob2']] = pd.DataFrame(df['firstname'].map(lambda x: string_similarity(firstname, x)).tolist(), index=df.index)
    similarity_df['FNSimilarity'] = df['firstname'].map(lambda x: compute_string_similarity(firstname, x))
    similarity_df['SNSimilarity'] = df['surname'].map(lambda x: compute_string_similarity(surname, x))
    similarity_df[['DOBSimilarity', 'DOB1', 'DOB2', 'DOB_rarity1', 'DOB_rarity2', 'DOB_prob1', 'DOB_prob2']] = pd.DataFrame(df['dob'].map(lambda x: dob_string_similarity(dob, x)).tolist(), index=df.index)
    similarity_df['AgeSimilarity'] = df['dob'].map(lambda x: age_similarity_score(dob, x))
    similarity_df[['strAddressSimilarity', 'jcdAddressSimilarity']] = pd.DataFrame(df['address'].map(lambda x: address_str_similarity_score(address, x)).tolist(), index=df.index)
    similarity_df['cityAddressMatch'] = df['city'].map(lambda x: location_matching(city_name, x))
    similarity_df['countryAddressMatch'] = df['country'].map(lambda x: location_matching(country, x))
    similarity_df['sexMatch'] = df['gender'].map(lambda x: location_matching(sex, x))
    similarity_df['natMatch'] = df['nationality'].map(lambda x: location_matching(nationality, x))
    similarity_df['originAirportMatch'] = df['departure_airport'].map(lambda x: location_matching(iata_o, x))
    similarity_df['destinationAirportMatch'] = df['arrival_airport'].map(lambda x: location_matching(iata_d, x))
    similarity_df['orgdesAirportMatch'] = df['departure_airport'].map(lambda x: location_matching(iata_d, x))
    similarity_df['desorgAirportMatch'] = df['arrival_airport'].map(lambda x: location_matching(iata_o, x))
    similarity_df['originCityMatch'] = df['OriginCity'].map(lambda x: location_matching(city_org, x))
    similarity_df['destinationCityMatch'] = df['DestinationCity'].map(lambda x: location_matching(city_dest, x))
    similarity_df['orgdesCityMatch'] = df['OriginCity'].map(lambda x: location_matching(city_dest, x))
    similarity_df['desorgCityMatch'] = df['DestinationCity'].map(lambda x: location_matching(city_org, x))
    similarity_df['originCountryMatch'] = df['OriginCountry'].map(lambda x: location_matching(ctry_org, x))
    similarity_df['destinationCountryMatch'] = df['DestinationCountry'].map(lambda x: location_matching(ctry_dest, x))
    similarity_df['orgdesCountryMatch'] = df['OriginCountry'].map(lambda x: location_matching(ctry_dest, x))
    similarity_df['desorgCountryMatch'] = df['DestinationCountry'].map(lambda x: location_matching(ctry_org, x))
    similarity_df[['originSimilarity', 'originExpScore']] = df.apply(lambda row: location_similarity_score(lon_o, lat_o, row['dep_lon'], row['dep_lat'], max_distance), axis=1, result_type='expand')
    similarity_df[['destinationSimilarity', 'destinationExpScore']] = df.apply(lambda row: location_similarity_score(lon_d, lat_d, row['arr_lon'], row['arr_lat'], max_distance), axis=1, result_type='expand')
    similarity_df[['orgdesSimilarity', 'orgdesExpScore']] = df.apply(lambda row: location_similarity_score(lon_o, lat_o, row['arr_lon'], row['arr_lat'], max_distance), axis=1, result_type='expand')
    similarity_df[['desorgSimilarity', 'desorgExpScore']] = df.apply(lambda row: location_similarity_score(lon_d, lat_d, row['dep_lon'], row['arr_lat'], max_distance), axis=1, result_type='expand')
    
    # # Add query airport IATA codes to DataFrame (for comparison/debugging)
    # similarity_df["query_departure_airport"] = iata_o
    # similarity_df["query_arrival_airport"] = iata_d

    # # Also keep candidate airport IATA codes explicitly
    # similarity_df["candidate_departure_airport"] = df["departure_airport"]
    # similarity_df["candidate_arrival_airport"] = df["arrival_airport"]
    # similarity_df["query_dep_lon"] = lon_o
    # similarity_df["query_dep_lat"] = lat_o
    # similarity_df["query_arr_lon"] = lon_d
    # similarity_df["query_arr_lat"] = lat_d

    # # Candidate airport coordinates (from the matched dataframe)
    # similarity_df["candidate_dep_lon"] = df["dep_lon"]
    # similarity_df["candidate_dep_lat"] = df["dep_lat"]
    # similarity_df["candidate_arr_lon"] = df["arr_lon"]
    # similarity_df["candidate_arr_lat"] = df["arr_lat"]


    expected_columns = [
        'FNSimilarity', 'FN_rarity1', 'FN_rarity2', 'FN_prob1', 'FN_prob2',
        'SNSimilarity', 'SN_rarity1', 'SN_rarity2', 'SN_prob1', 'SN_prob2',
        'DOBSimilarity', 'DOB_rarity1', 'DOB_rarity2', 'DOB_prob1', 'DOB_prob2',
        'AgeSimilarity', 'strAddressSimilarity', 'jcdAddressSimilarity', 'cityAddressMatch',
        'countryAddressMatch', 'sexMatch', 'natMatch', 'originAirportMatch', 'destinationAirportMatch',
        'originCityMatch', 'destinationCityMatch', 'originCountryMatch', 'destinationCountryMatch',
        'orgdesAirportMatch', 'desorgAirportMatch', 'orgdesCityMatch', 'desorgCityMatch',
        'orgdesCountryMatch', 'desorgCountryMatch', 'originSimilarity', 'originExpScore',
        'destinationSimilarity', 'destinationExpScore', 'orgdesSimilarity', 'orgdesExpScore',
        'desorgSimilarity', 'desorgExpScore'
    ]

    # ✅ Fill missing columns with 0
    for col in expected_columns:
        if col not in similarity_df.columns:
            similarity_df[col] = 0

    end_time = time.time()

    return similarity_df


def compute_string_similarity(s1, s2):
    try:
        if pd.isnull(s1) or pd.isnull(s2):
            return 0
        similarity = fuzz.ratio(s1.lower(), s2.lower())
        logging.debug(f"String similarity between '{s1}' and '{s2}': {similarity}")
        return similarity # dummy rarity/probability for now
    except Exception as e:
        logging.error(f"❌ Error in safe_string_similarity: {e} | s1: {s1} | s2: {s2}")
        return 0