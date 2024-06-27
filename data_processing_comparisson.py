import os
import requests
import json
import pandas as pd
import numpy as np
import joblib
import concurrent.futures
from functools import partial
import time
import dask.dataframe as dd
from dask import delayed
import dask
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, udf, lit
from pyspark.sql.types import FloatType, StringType, ArrayType, StructType, StructField


import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from app.loc_access import LocDataAccess
from app.location_similarity import haversine, location_similarity_score, location_matching, address_str_similarity_score
from app.age_similarity import age_similarity_score
from app.base_similarity import count_likelihood2, string_similarity
from app.azure_blob_storage import download_from_blob_storage, fetch_combined_data
from app.similarity_search import enrich_data
from app.data_parser import parse_combined_json
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import logging


import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Initialize Spark Session
spark = SparkSession.builder \
    .appName("SimilaritySearch") \
    .getOrCreate()

max_distance = 12000


def find_similar_passengers(airport_data_access, firstname, surname, name, dob, iata_o, iata_d, city_name, address, sex, nationality, data_dir, nameThreshold, ageThreshold, locationThreshold):
    # Fetch the combined JSON data from local storage
    with open('combined_pnr_data.json', 'r') as file:
        combined_data = json.load(file)

    all_data = parse_combined_json(combined_data)

    logging.info(f"all_data shape before enrichment: {all_data.shape}")
    start_time = time.time()
    all_data = enrich_data(all_data)
    print("")
    end_time = time.time()
    logging.info(f"Time for enriching data: {end_time - start_time:.2f} seconds")
    logging.info(f"all_data enriched shape: {all_data.shape}")
    
    lon_o, lat_o = airport_data_access.get_airport_lon_lat_by_iata(iata_o)
    lon_d, lat_d = airport_data_access.get_airport_lon_lat_by_iata(iata_d)
    lon_c, lat_c = airport_data_access.get_airport_lon_lat_by_city(city_name)
    country = airport_data_access.get_country_by_city(city_name)
    ctry_org = airport_data_access.get_country_by_airport_iata(iata_o)
    ctry_dest = airport_data_access.get_country_by_airport_iata(iata_d)
    city_org = airport_data_access.get_city_by_airport_iata(iata_o)
    city_dest = airport_data_access.get_city_by_airport_iata(iata_d)
    
    params = (
        firstname, surname, name, iata_o, lat_o, lon_o, city_org, ctry_org, iata_d, lat_d, lon_d, city_dest, ctry_dest, dob, city_name, lat_c, lon_c, country, nationality, sex, address, nameThreshold, ageThreshold, locationThreshold
    )
    

    results = evaluate_methods(df = all_data, params = params)
    return results

def perform_similarity_search(firstname, surname, name, iata_o, lat_o, lon_o, city_org, ctry_org, iata_d, lat_d, lon_d, city_dest, ctry_dest, dob, city_name, lat_c, lon_c, country, nationality, sex, address, nameThreshold, ageThreshold, locationThreshold, df, counts):
    max_distance = 12000
    # Check for duplicate columns
    
    num_records = df.shape[0]
    model_path = 'model/f1_xgboost_model.joblib'
    df.reset_index(inplace=True)
    df.rename(columns={'index': 'unique_id'}, inplace=True)
    similarity_df = pd.DataFrame()


    gender_counts = counts['gender_counts']
    origin_airport_counts = counts['origin_airport_counts']
    origin_city_counts = counts['origin_city_counts']
    origin_country_counts = counts['origin_country_counts']
    destination_airport_counts = counts['destination_airport_counts']
    destination_city_counts = counts['destination_city_counts']
    destination_country_counts = counts['destination_country_counts']
    city_address_counts = counts['city_address_counts']
    country_address_counts = counts['country_address_counts']
    nationality_counts = counts['nationality_counts']
    DOB_counts = counts['DOB_counts']
    firstname_counts = counts['firstname_counts']
    surname_counts = counts['surname_counts']

    similarity_df[['FNSimilarity', 'FN1', 'FN2', 'FN_rarity1', 'FN_rarity2', 'FN_prob1', 'FN_prob2']] = pd.DataFrame(df['Firstname'].map(lambda x: string_similarity(firstname, x, firstname_counts, num_records)).tolist(), index=df.index)
    similarity_df[['SNSimilarity', 'SN1', 'SN2', 'SN_rarity1', 'SN_rarity2', 'SN_prob1', 'SN_prob2']] = pd.DataFrame(df['Surname'].map(lambda x: string_similarity(surname, x, surname_counts, num_records)).tolist(), index=df.index)
    similarity_df[['DOBSimilarity', 'DOB1', 'DOB2', 'DOB_rarity1', 'DOB_rarity2', 'DOB_prob1', 'DOB_prob2']] = pd.DataFrame(df['DOB'].map(lambda x: string_similarity(dob, x, DOB_counts, num_records)).tolist(), index=df.index)
    similarity_df['AgeSimilarity'] = df['DOB'].map(lambda x: age_similarity_score(dob, x))
    similarity_df[['strAddressSimilarity', 'jcdAddressSimilarity']] = pd.DataFrame(df['Address'].map(lambda x: address_str_similarity_score(address, x)).tolist(), index=df.index)
    similarity_df['cityAddressMatch'] = df['CityName'].map(lambda x: location_matching(city_name, x))
    # similarity_df[['cityAddressRarity1', 'cityAddressProb1']] = count_likelihood2(city_name, city_address_counts, num_records)
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
    similarity_df.reset_index(inplace=True)
    similarity_df.rename(columns={'index': 'unique_id'}, inplace=True)

    duplicate_columns = similarity_df.columns[similarity_df.columns.duplicated()]
    if len(duplicate_columns) > 0:
        print("Duplicate columns found:", duplicate_columns)
        # Handle duplicate columns here
    else:
        print("No duplicate columns found")
    
    return similarity_df

def dask_similarity(params, df, counts):
    df = dd.from_pandas(df, npartitions=10)  # Convert Pandas DataFrame to Dask DataFrame with 10 partitions

    firstname, surname, name, iata_o, lat_o, lon_o, city_org, ctry_org, iata_d, lat_d, lon_d, city_dest, ctry_dest, dob, city_name, lat_c, lon_c, country, nationality, sex, address, nameThreshold, ageThreshold, locationThreshold = params

    num_records = df.shape[0].compute()
    max_distance = 12000
    gender_counts = counts['gender_counts']
    origin_airport_counts = counts['origin_airport_counts']
    origin_city_counts = counts['origin_city_counts']
    origin_country_counts = counts['origin_country_counts']
    destination_airport_counts = counts['destination_airport_counts']
    destination_city_counts = counts['destination_city_counts']
    destination_country_counts = counts['destination_country_counts']
    city_address_counts = counts['city_address_counts']
    country_address_counts = counts['country_address_counts']
    nationality_counts = counts['nationality_counts']
    DOB_counts = counts['DOB_counts']
    firstname_counts = counts['firstname_counts']
    surname_counts = counts['surname_counts']

    def compute_similarity(row):
        return {
            'FNSimilarity': string_similarity(firstname, row['Firstname'], firstname_counts, num_records),
            'SNSimilarity': string_similarity(surname, row['Surname'], surname_counts, num_records),
            'DOBSimilarity': string_similarity(dob, row['DOB'], DOB_counts, num_records),
            'AgeSimilarity': age_similarity_score(dob, row['DOB']),
            'strAddressSimilarity': address_str_similarity_score(address, row['Address'])[0],
            'jcdAddressSimilarity': address_str_similarity_score(address, row['Address'])[1],
            'cityAddressMatch': location_matching(city_name, row['CityName']),
            'countryAddressMatch': location_matching(country, row['Country of Address']),
            'sexMatch': location_matching(sex, row['Sex']),
            'natMatch': location_matching(nationality, row['Nationality']),
            'originAirportMatch': location_matching(iata_o, row['OriginIATA']),
            'destinationAirportMatch': location_matching(iata_d, row['DestinationIATA']),
            'orgdesAirportMatch': location_matching(iata_d, row['OriginIATA']),
            'desorgAirportMatch': location_matching(iata_o, row['DestinationIATA']),
            'originCityMatch': location_matching(city_org, row['OriginCity']),
            'destinationCityMatch': location_matching(city_dest, row['DestinationCity']),
            'orgdesCityMatch': location_matching(city_dest, row['OriginCity']),
            'desorgCityMatch': location_matching(city_org, row['DestinationCity']),
            'originCountryMatch': location_matching(ctry_org, row['OriginCountry']),
            'destinationCountryMatch': location_matching(ctry_dest, row['DestinationCountry']),
            'orgdesCountryMatch': location_matching(ctry_dest, row['OriginCountry']),
            'desorgCountryMatch': location_matching(ctry_org, row['DestinationCountry']),
            'originSimilarity': location_similarity_score(lon_o, lat_o, row['OriginLon'], row['OriginLat'], max_distance),
            'destinationSimilarity': location_similarity_score(lon_d, lat_d, row['DestinationLon'], row['DestinationLat'], max_distance),
            'orgdesSimilarity': location_similarity_score(lon_o, lat_o, row['DestinationLon'], row['DestinationLat'], max_distance),
            'desorgSimilarity': location_similarity_score(lon_d, lat_d, row['OriginLon'], row['OriginLat'], max_distance)
        }

        similarities.update({
            'FN_rarity1': count_likelihood2(firstname, firstname_counts, num_records)[0],
            'FN_rarity2': count_likelihood2(firstname, firstname_counts, num_records)[1],
            'FN_prob1': count_likelihood2(firstname, firstname_counts, num_records)[2],
            'FN_prob2': count_likelihood2(firstname, firstname_counts, num_records)[3],
            # Add similar calculations for other fields
            })
        return pd.Series(similarities)

    meta = {
        'FNSimilarity': 'f8', 'SNSimilarity': 'f8', 'DOBSimilarity': 'f8', 'AgeSimilarity': 'f8',
        'strAddressSimilarity': 'f8', 'jcdAddressSimilarity': 'f8', 'cityAddressMatch': 'f8',
        'countryAddressMatch': 'f8', 'sexMatch': 'f8', 'natMatch': 'f8', 'originAirportMatch': 'f8',
        'destinationAirportMatch': 'f8', 'orgdesAirportMatch': 'f8', 'desorgAirportMatch': 'f8',
        'originCityMatch': 'f8', 'destinationCityMatch': 'f8', 'orgdesCityMatch': 'f8',
        'desorgCityMatch': 'f8', 'originCountryMatch': 'f8', 'destinationCountryMatch': 'f8',
        'orgdesCountryMatch': 'f8', 'desorgCountryMatch': 'f8', 'originSimilarity': 'f8',
        'destinationSimilarity': 'f8', 'orgdesSimilarity': 'f8', 'desorgSimilarity': 'f8',
        'FN_rarity1': 'f8', 'FN_rarity2': 'f8', 'FN_prob1': 'f8', 'FN_prob2': 'f8',
        # Add similar metadata for other fields
    }

    similarity_df = df.apply(compute_similarity, axis=1, meta=meta).compute()
    similarity_df['unique_id'] = df.index

    return similarity_df

# def spark_similarity(params, df, counts):
#     firstname, surname, name, iata_o, lat_o, lon_o, city_org, ctry_org, iata_d, lat_d, lon_d, city_dest, ctry_dest, dob, city_name, lat_c, lon_c, country, nationality, sex, address, nameThreshold, ageThreshold, locationThreshold = params

#     num_records = df.shape[0]
#     max_distance = 12000
#     gender_counts = counts['gender_counts']
#     origin_airport_counts = counts['origin_airport_counts']
#     origin_city_counts = counts['origin_city_counts']
#     origin_country_counts = counts['origin_country_counts']
#     destination_airport_counts = counts['destination_airport_counts']
#     destination_city_counts = counts['destination_city_counts']
#     destination_country_counts = counts['destination_country_counts']
#     city_address_counts = counts['city_address_counts']
#     country_address_counts = counts['country_address_counts']
#     nationality_counts = counts['nationality_counts']
#     DOB_counts = counts['DOB_counts']
#     firstname_counts = counts['firstname_counts']
#     surname_counts = counts['surname_counts']

#     df = spark.createDataFrame(df)


#     string_similarity_fn_udf = udf(lambda name1, name2: string_similarity(name1, name2, counts['firstname_counts'], num_records), ArrayType(FloatType()))
#     string_similarity_sn_udf = udf(lambda name1, name2: string_similarity(name1, name2, counts['surname_counts'], num_records), ArrayType(FloatType()))
#     string_similarity_dob_udf = udf(lambda name1, name2: string_similarity(name1, name2, counts['DOB_counts'], num_records), ArrayType(FloatType()))
#     age_similarity_score_udf = udf(age_similarity_score, FloatType())
#     address_str_similarity_score_udf = udf(address_str_similarity_score, ArrayType(FloatType()))
#     location_matching_udf = udf(location_matching, FloatType())
#     location_similarity_score_udf = udf(location_similarity_score, ArrayType(FloatType()))
#     city_address_rarity_prob_udf = udf(lambda value: count_likelihood2(value, city_address_counts, num_records), ArrayType(FloatType()))
#     country_address_rarity_prob_udf = udf(lambda value: count_likelihood2(value, country_address_counts, num_records), ArrayType(FloatType()))
#     sex_rarity_prob_udf = udf(lambda value: count_likelihood2(value, gender_counts, num_records), ArrayType(FloatType()))
#     nat_rarity_prob_udf = udf(lambda value: count_likelihood2(value, nationality_counts, num_records), ArrayType(FloatType()))
#     origin_airport_rarity_prob_udf = udf(lambda value: count_likelihood2(value, origin_airport_counts, num_records), ArrayType(FloatType()))
#     destination_airport_rarity_prob_udf = udf(lambda value: count_likelihood2(value, destination_airport_counts, num_records), ArrayType(FloatType()))
#     origin_city_rarity_prob_udf = udf(lambda value: count_likelihood2(value, origin_city_counts, num_records), ArrayType(FloatType()))
#     destination_city_rarity_prob_udf = udf(lambda value: count_likelihood2(value, destination_city_counts, num_records), ArrayType(FloatType()))
#     destination_country_rarity_prob_udf = udf(lambda value: count_likelihood2(value, destination_country_counts, num_records), ArrayType(FloatType()))


#     similarity_df = df.withColumn("FNSimilarity", string_similarity_fn_udf(col("Firstname"), col("Firstname"))) \
#         .withColumn("SNSimilarity", string_similarity_sn_udf(col("Surname"), col("Surname"))) \
#         .withColumn("DOBSimilarity", string_similarity_dob_udf(col("DOB"), col("DOB"))) \
#         .withColumn("AgeSimilarity", age_similarity_score_udf(col("DOB"), col("DOB"))) \
#         .withColumn("strAddressSimilarity", address_str_similarity_score_udf(col("Address"), col("Address")).getItem(0)) \
#         .withColumn("jcdAddressSimilarity", address_str_similarity_score_udf(col("Address"), col("Address")).getItem(1)) \
#         .withColumn("cityAddressMatch", location_matching_udf(col("CityName"), col("CityName"))) \
#         .withColumn("countryAddressMatch", location_matching_udf(col("Country of Address"), col("Country of Address"))) \
#         .withColumn("sexMatch", location_matching_udf(col("Sex"), col("Sex"))) \
#         .withColumn("natMatch", location_matching_udf(col("Nationality"), col("Nationality"))) \
#         .withColumn("originAirportMatch", location_matching_udf(col("OriginIATA"), col("OriginIATA"))) \
#         .withColumn("destinationAirportMatch", location_matching_udf(col("DestinationIATA"), col("DestinationIATA"))) \
#         .withColumn("orgdesAirportMatch", location_matching_udf(col("OriginIATA"), col("DestinationIATA"))) \
#         .withColumn("desorgAirportMatch", location_matching_udf(col("DestinationIATA"), col("OriginIATA"))) \
#         .withColumn("originCityMatch", location_matching_udf(col("OriginCity"), col("OriginCity"))) \
#         .withColumn("destinationCityMatch", location_matching_udf(col("DestinationCity"), col("DestinationCity"))) \
#         .withColumn("orgdesCityMatch", location_matching_udf(col("OriginCity"), col("DestinationCity"))) \
#         .withColumn("desorgCityMatch", location_matching_udf(col("DestinationCity"), col("OriginCity"))) \
#         .withColumn("originCountryMatch", location_matching_udf(col("OriginCountry"), col("OriginCountry"))) \
#         .withColumn("destinationCountryMatch", location_matching_udf(col("DestinationCountry"), col("DestinationCountry"))) \
#         .withColumn("orgdesCountryMatch", location_matching_udf(col("OriginCountry"), col("DestinationCountry"))) \
#         .withColumn("desorgCountryMatch", location_matching_udf(col("DestinationCountry"), col("OriginCountry")))

# # Apply location similarity score functions
#     similarity_df = similarity_df.withColumn("originSimilarity", location_similarity_score_udf(col("OriginLon"), col("OriginLat"), col("OriginLon"), col("OriginLat"), max_distance).getItem(0)) \
#         .withColumn("originExpScore", location_similarity_score_udf(col("OriginLon"), col("OriginLat"), col("OriginLon"), col("OriginLat"), max_distance).getItem(1)) \
#         .withColumn("destinationSimilarity", location_similarity_score_udf(col("DestinationLon"), col("DestinationLat"), col("DestinationLon"), col("DestinationLat"), max_distance).getItem(0)) \
#         .withColumn("destinationExpScore", location_similarity_score_udf(col("DestinationLon"), col("DestinationLat"), col("DestinationLon"), col("DestinationLat"), max_distance).getItem(1)) \
#         .withColumn("orgdesSimilarity", location_similarity_score_udf(col("OriginLon"), col("OriginLat"), col("DestinationLon"), col("DestinationLat"), max_distance).getItem(0)) \
#         .withColumn("orgdesExpScore", location_similarity_score_udf(col("OriginLon"), col("OriginLat"), col("DestinationLon"), col("DestinationLat"), max_distance).getItem(1)) \
#         .withColumn("desorgSimilarity", location_similarity_score_udf(col("DestinationLon"), col("DestinationLat"), col("OriginLon"), col("OriginLat"), max_distance).getItem(0)) \
#         .withColumn("desorgExpScore", location_similarity_score_udf(col("DestinationLon"), col("DestinationLat"), col("OriginLon"), col("OriginLat"), max_distance).getItem(1))

# # Show the resultant DataFrame
#     return similarity_df.toPandas()

def calculate_counts(df):
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

    return {
        'gender_counts': gender_counts,
        'origin_airport_counts': origin_airport_counts,
        'origin_city_counts': origin_city_counts,
        'origin_country_counts': origin_country_counts,
        'destination_airport_counts': destination_airport_counts,
        'destination_city_counts': destination_city_counts,
        'destination_country_counts': destination_country_counts,
        'city_address_counts': city_address_counts,
        'country_address_counts': country_address_counts,
        'nationality_counts': nationality_counts,
        'DOB_counts': DOB_counts,
        'firstname_counts': firstname_counts,
        'surname_counts': surname_counts
    }

# Different methods to perform similarity search
def map_apply_similarity(params, df, counts):
    return perform_similarity_search(*params, df, counts)

def concurrency_thread_similarity(params, df, counts):
    with ThreadPoolExecutor() as executor:
        chunks = np.array_split(df, 10)  # Split into 10 chunks
        futures = [executor.submit(perform_similarity_search, *params, chunk, counts) for chunk in chunks]
        results = pd.concat([future.result() for future in as_completed(futures)])
    return results

def concurrency_process_similarity(params, df, counts):
    with ProcessPoolExecutor() as executor:
        chunks = np.array_split(df, 10)  # Split into 10 chunks
        futures = [executor.submit(perform_similarity_search, *params, chunk, counts) for chunk in chunks]
        results = pd.concat([future.result() for future in as_completed(futures)])
    return results

def split_df_similarity(params, df, counts):
    chunks = np.array_split(df, 10)  # Split into 10 chunks
    results = pd.concat([perform_similarity_search(*params, chunk, counts) for chunk in chunks])
    return results

def split_df_similarity_5(params, df, counts):
    chunks = np.array_split(df, 5)  # Split into 5 chunks
    results = pd.concat([perform_similarity_search(*params, chunk, counts) for chunk in chunks])
    return results

def split_df_similarity_20(params, df, counts):
    chunks = np.array_split(df, 20)  # Split into 20 chunks
    results = pd.concat([perform_similarity_search(*params, chunk, counts) for chunk in chunks])
    return results

def split_df_similarity_100(params, df, counts):
    chunks = np.array_split(df, 100)  # Split into 100 chunks
    results = pd.concat([perform_similarity_search(*params, chunk, counts) for chunk in chunks])
    return results

def split_df_similarity_140(params, df, counts):
    chunks = np.array_split(df, 140)  # Split into 20 chunks
    results = pd.concat([perform_similarity_search(*params, chunk, counts) for chunk in chunks])
    return results

def split_df_similarity_200(params, df, counts):
    chunks = np.array_split(df, 200)  # Split into 200 chunks
    results = pd.concat([perform_similarity_search(*params, chunk, counts) for chunk in chunks])
    return results


# Function to evaluate methods
def evaluate_methods(params, df):
    print("Evaluating methods")
    methods = {
        # "dask_similarity": dask_similarity,
        "map_apply": map_apply_similarity,
        "concurrency_thread": concurrency_thread_similarity,
        # "concurrency_process": concurrency_process_similarity,
        # "split_df_10": split_df_similarity,
        # "split_df_5": split_df_similarity_5,
        # "split_df_20": split_df_similarity_20,
        "split_df_100": split_df_similarity_100,
        "split_df_140": split_df_similarity_140
        # "spark_similarity": spark_similarity
        # "split_df_200": split_df_similarity_200,
        

    }
    
    results = {}
    counts = calculate_counts(df)

    for method_name, method in methods.items():
        start_time = time.time()
        result_df = method(params, df, counts)
        end_time = time.time()
        results[method_name] = (result_df, end_time - start_time)
        logging.info(f"Method {method_name} took {end_time - start_time:.2f} seconds")
        logging.info(f"Method {method_name} result shape: {result_df.shape}")
    
    return results


if __name__ == "__main__":
    # Load your data from local storage

    # Define your parameters
    airport_data_access = LocDataAccess.get_instance()
    params = (
        airport_data_access,  # airport_data_access
        'Dominick',  # firstname
        'Ortiz',   # surname
        'Dominick Ortiz',  # name
        '1980-10-03',  # dob
        'DXB',  # iata_o
        'ATH',  # iata_d
        'Dibai',  # city_name
        'Dubai',  # address
        'F',           # sex
        'MAC',         # nationality
        'data',        # data_dir
        0,            # nameThreshold
        0,             # ageThreshold
        0              # locationThreshold
    )

    results = find_similar_passengers(*params)
