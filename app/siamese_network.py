import joblib
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras.models import load_model
import os

from app.location_similarity import haversine, location_similarity_score, location_matching, address_str_similarity_score
from app.age_similarity import age_similarity_score
from app.base_similarity import count_likelihood2, string_similarity
import logging
import time
from datetime import datetime
from sklearn.preprocessing import LabelEncoder
from dotenv import load_dotenv
load_dotenv("environment.env")
SIAMESE_THRESHOLD = int(os.getenv("SIAMESE_THRESHOLD"))




siamese_encoder = load_model("model/siamese_encoder.h5", compile = False)  # Load Siamese Encoder
xgb_classifier = joblib.load("model/xgb_similarity_model.pkl")  # Load XGBoost Model
list_nationality = pd.read_csv("data\geoCrosswalk\GeoCrossWalkMed.csv")['HH_ISO'].unique().tolist()
list_nationality = ['Unknown' if (pd.isna(x) or x == '') else x for x in list_nationality]
if 'Unknown' not in list_nationality:
    list_nationality.append('Unknown')


def text_to_numeric(text, max_length=40):
    text = text.lower()[:max_length]
    return np.array([ord(char) % 256 for char in text] + [0] * (max_length - len(text)))

def normalize_dob(dob):
    reference_date = datetime(1900, 1, 1)

    if pd.isna(dob) or dob == '':
        dob = datetime(1900, 1, 1)  # Default for missing dates

    if isinstance(dob, float) or isinstance(dob, int):
        dob = str(int(dob))  # Convert float (e.g., 19680115) to string

    if isinstance(dob, datetime):
        return (dob - reference_date).days / 365.25  # Convert date to age in years

    try:
        return (datetime.strptime(dob.strip(), '%Y-%m-%d') - reference_date).days / 365.25
    except ValueError:
        return 0  # Default for invalid dates

def siamese_cleaning(df):


    df['Firstname'] = df['Firstname'].astype(str).str.lower()
    df['Surname'] = df['Surname'].astype(str).str.lower()
    df['Address'] = df['Address'].astype(str).str.lower()

    text_cols = ['Firstname', 'Surname', 'Address']
    for col in text_cols:
        df.loc[:, col] = df[col].replace('', 'MISSING').fillna("MISSING")

 # Convert to numeric first
        # Fix Categorical Column Missing Values
    df.loc[:, 'Sex'] = df['Sex'].replace('', 'Unknown').fillna("Unknown")
    df.loc[:, 'Nationality'] = df['Nationality'].replace('', 'Unknown').fillna("Unknown")

    return df


def get_siamese_embedding(df):
    le_nationality = LabelEncoder()
    le_nationality.fit(list_nationality)
    df['Nationality_embd'] = le_nationality.transform(df['Nationality'])
    le_sex = LabelEncoder()
    le_sex.fit(['Unknown', 'F', 'M'])
    df['Sex_embd'] = le_sex.transform(df['Sex'])
    df['DOB_embd'] = df['DOB'].apply(normalize_dob)




    num_cols = ['OriginLat', 'OriginLon','DestinationLat', 'DestinationLon']
    for col in num_cols:
        df[col] = df[col].astype(str).str.strip()  # Remove spaces
        df[col] = df[col].replace('', np.nan)  # Convert empty strings to NaN
        df[col] = df[col].apply(lambda x: pd.to_numeric(x, errors='coerce'))  # Convert to numeric
        df[col] = df[col].fillna(0).astype(float) 

    df['OriginLat'] /= 90.0
    df['OriginLon'] /= 180.0
    df['DestinationLat'] /= 90.0
    df['DestinationLon'] /= 180.0


    """Extract embeddings for each record using the Siamese model."""
    X_text = np.array([
        np.concatenate([
            text_to_numeric(df.iloc[i]['Firstname']),
            text_to_numeric(df.iloc[i]['Surname']),
            text_to_numeric(df.iloc[i]['Address'])
        ])
        for i in range(len(df))
    ], dtype=np.float32)

    X_cat = df[['Nationality_embd', 'Sex_embd']].values  # Categorical features
    logging.info(f"dtype of numerical features: {df[['DOB_embd', 'OriginLat', 'OriginLon', 'DestinationLat', 'DestinationLon']].dtypes}")
    X_num = df[['DOB_embd', 'OriginLat', 'OriginLon', 'DestinationLat', 'DestinationLon']].values  # Numerical features
    logging.info(f"d type: {X_text.dtype}, {X_cat.dtype}, {X_num.dtype}")

    # Get embeddings
    embeddings = siamese_encoder.predict([X_text, X_cat, X_num], verbose=0)
    return embeddings

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

def siamese_network(firstname, surname, name, iata_o, lat_o, lon_o, city_org, ctry_org, iata_d, lat_d, lon_d, city_dest, ctry_dest, dob, city_name, lat_c, lon_c, country,  nationality, sex, address, df, nameThreshold, ageThreshold, locationThreshold):
    """
    Performs similarity search using Siamese + XGBoost.
    
    Args:
        firstname, surname, dob, address, nationality, sex, origin_lat, origin_lon, dest_lat, dest_lon: Query person details
        df: DataFrame containing the database of passengers
    
    Returns:
        Filtered DataFrame ranked by similarity confidence.
    """
    # Step 1: Process the Query (Convert to Model Input)

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
    
    query_df = pd.DataFrame([{
        "Firstname": firstname,
        "Surname": surname,
        "Address": address,
        "Nationality": nationality,
        "Sex": sex,
        "DOB": dob,
        "OriginLat": lat_o,
        "OriginLon": lon_o,
        "DestinationLat": lat_d,
        "DestinationLon": lon_d
    }])

    query_df = siamese_cleaning(query_df)
    df = siamese_cleaning(df)

    df.reset_index(inplace=True)
    df.rename(columns={'index': 'unique_id'}, inplace=True)

    if nameThreshold>50 and ageThreshold>50:
        df = data_filtration(df, nameThreshold, ageThreshold, firstname, surname, dob)

    # Step 2: Extract Embeddings for Query & Database
    start_time = time.time()
    query_embedding = get_siamese_embedding(query_df)
    db_embeddings = get_siamese_embedding(df)
    end_time = time.time()
    logging.info(f"Time for computing embeddings: {end_time - start_time:.2f} seconds")

    start_time = time.time()
    # Step 3: Compute Feature Representation for XGBoost
    X_test = np.hstack([
        np.abs(db_embeddings - query_embedding),  # Distance-Based Features
        db_embeddings * query_embedding           # Interaction Features
    ])

    # Step 4: Predict Similarity Using XGBoost
    similarity_scores = xgb_classifier.predict_proba(X_test)[:, 1] * 100  # Convert to percentage
    end_time = time.time()
    logging.info(f"Time for computing XGBoost predictions: {end_time - start_time:.2f} seconds")

    # Step 5: Store Results in DataFrame (Maintain Original Columns)
    df['Confidence Level'] = similarity_scores

    # Step 6: Rank Results by Similarity
    df_filtered = df[df['Confidence Level'] >= SIAMESE_THRESHOLD]
    logging.info(f"Number of records with similarity >= {SIAMESE_THRESHOLD}: {df_filtered.shape[0]}")
    similarity_df = compute_similarity_features(df_filtered, firstname, surname, dob, address, city_name, country, sex, nationality, iata_o, city_org, ctry_org, iata_d, city_dest, ctry_dest, lat_o, lon_o, lat_d, lon_d, max_distance=12000)
    
    similarity_df['Siamese Similarity'] = df['Confidence Level']  # Normalize to [0,1]

    # ✅ Define Weights for Feature Contribution
    siamese_weight = 0.7
    feature_weight = 0.3

    # ✅ Compute Feature-Based Similarity Score (Aggregated)
    selected_features = [
        'FNSimilarity', 'SNSimilarity', 'DOBSimilarity', 'AgeSimilarity',
        'strAddressSimilarity', 'originSimilarity', 'destinationSimilarity'
    ]
    similarity_df['Feature-Based Similarity'] = similarity_df[selected_features].mean(axis=1)

    # ✅ Compute Final Compound Similarity Score
    similarity_df['Compound Similarity Score'] = (
        (similarity_df['Siamese Similarity'] * siamese_weight) +
        (similarity_df['Feature-Based Similarity'] * feature_weight)
    )

    result_df = df_filtered.copy()
    result_df = result_df.join(similarity_df)
    result_df = result_df.applymap(lambda x: np.round(x, 4) if isinstance(x, (int, float)) else x)

    filtered_result_df = result_df[
        (result_df['FNSimilarity'] >= nameThreshold) &
        (result_df['SNSimilarity'] >= nameThreshold) &
        (result_df['AgeSimilarity'] >= ageThreshold) &
        (result_df['Compound Similarity Score'] >= 10) &
        (result_df['Confidence Level'] >= 1)
    ]

    filtered_result_df.drop_duplicates(
        subset=['PassengerID', 'DOB', 'PNRID', 'iata_pnrgov_notif_rq_id', 'TravelDocNumber', 'FlightNumber', 
                'OriginatorAirlineCode', 'DepartureDateTime', 'ArrivalDateTime', 'FlightLegFlightNumber'], inplace = True
    )

    filtered_result_df.sort_values(by=['Confidence Level', 'Compound Similarity Score'], ascending=False, inplace=True)




    return filtered_result_df

def compute_similarity_features(df, firstname, surname, dob, address, city_name, country, sex, nationality, iata_o, city_org, ctry_org, iata_d, city_dest, ctry_dest, lat_o, lon_o, lat_d, lon_d, max_distance=12000):
    """
    Computes all similarity features and ensures expected columns exist.
    """
    start_time = time.time()
    num_records = df.shape[0]
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
    start_time = time.time()
    similarity_df = pd.DataFrame(index=df.index)

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
    logging.info(f"Time for calculating similarities: {end_time - start_time:.2f} seconds")

    return similarity_df
