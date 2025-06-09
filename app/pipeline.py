# app/pipeline.py
import numpy as np
import logging
import pandas as pd
import time
from app.loc_access import LocDataAccess
from app.model_cache import load_model_bundle
from app.faiss_search import faiss_search_with_metadata
from app.embedding import embed_passengers
from app.similarity_metrics import compute_similarity_features
from app.utils import compute_relative_age, enrich_location, infer_shards_for_date, infer_shards_for_date_range

def run_similarity_pipeline(data: dict) -> dict:
    airport_data_access = LocDataAccess.get_instance()
    
    # Prepare query
    query = {
        "firstname": data.get("firstname", ""),
        "surname": data.get("surname", ""),
        "dob": data.get("dob", ""),
        "address": data.get("address", ""),
        "city": data.get("city_name", ""),
        "gender": data.get("sex", "unknown"),
        "nationality": data.get("nationality", "unknown"),
        "iata_o": data.get("iata_o", ""),
        "iata_d": data.get("iata_d", ""),
    }

    # Enrich location
    query_df = pd.DataFrame([query])
    query_df = compute_relative_age(query_df)
    query_df = enrich_location(query_df)

    # shard_label = infer_shards_for_date(data["arrival_date_from"], data["shards"])
    # models = load_model_bundle(shard_label)
    shard_labels = infer_shards_for_date_range(data["arrival_date_from"], data["arrival_date_to"], data["shards"])
    all_matches = []

    start_time = time.time()
    logging.info(f"Starting similarity search for query: {query} across shards length {len(shard_labels)}")
    for shard_label in shard_labels:
        models = load_model_bundle(shard_label)
        
        embedding, *_ = embed_passengers(
            query_df,
            models["encoder"],
            models["scaler"],
            models["tfidf_name"],
            models["tfidf_addr"],
            models["svd_name"],
            models["svd_addr"]
        )
        embedding = np.nan_to_num(embedding.astype("float32"))

        shard_matches = faiss_search_with_metadata(
            embedding, 
            models["index"], 
            models["metadata"]["travel_doc"].values, 
            models["metadata"]
        )

        all_matches.append(shard_matches)
    end_time = time.time()
    logging.info(f"Similarity search completed in {end_time - start_time:.2f} seconds")
    


    matches = pd.concat(all_matches, ignore_index=True)
    matches["departure_time"] = pd.to_datetime(matches["departure_time"], errors="coerce")
    matches["arrival_time"] = pd.to_datetime(matches["arrival_time"], errors="coerce")

    matches = matches[
        (matches["departure_time"] >= data["arrival_date_from"]) &
        (matches["arrival_time"] <= data["arrival_date_to"])
    ]
    logging.info(f"Found {len(matches)} matches across shards: {shard_labels}")
    if matches.empty:
        return {
            "status": "success",
            "message": "There are no similar passengers found.",
            "data": []
            }

    # Get additional fields
    lon_o, lat_o = airport_data_access.get_airport_lon_lat_by_iata(query["iata_o"])
    lon_d, lat_d = airport_data_access.get_airport_lon_lat_by_iata(query["iata_d"])
    lon_c, lat_c = airport_data_access.get_airport_lon_lat_by_city(query["city"])
    country = airport_data_access.get_country_by_city(query["city"])
    ctry_org = airport_data_access.get_country_by_airport_iata(query["iata_o"])
    ctry_dest = airport_data_access.get_country_by_airport_iata(query["iata_d"])
    city_org = airport_data_access.get_city_by_airport_iata(query["iata_o"])
    city_dest = airport_data_access.get_city_by_airport_iata(query["iata_d"])

    sim_df = compute_similarity_features(
        matches,
        firstname=query["firstname"],
        surname=query["surname"],
        dob=query["dob"],
        address=query["address"],
        city_name=query["city"],
        country=country,
        sex=query["gender"],
        nationality=query["nationality"],
        iata_o=query["iata_o"],
        city_org=city_org,
        ctry_org=ctry_org,
        iata_d=query["iata_d"],
        city_dest=city_dest,
        ctry_dest=ctry_dest,
        lon_o=lon_o,
        lat_o=lat_o,
        lon_d=lon_d,
        lat_d=lat_d,
    )

    enriched_matches = pd.concat([matches, sim_df], axis=1)

    # Replace invalid values before filtering
    enriched_matches.replace([np.inf, -np.inf], np.nan, inplace=True)
    enriched_matches.fillna(0, inplace=True)



    # Apply filters
    filters = (
        (enriched_matches["FNSimilarity"] >= data.get("nameThreshold", 30)) &
        (enriched_matches["SNSimilarity"] >= data.get("nameThreshold", 30))
    )

    if data.get("dob", "").strip():
        filters &= (enriched_matches["AgeSimilarity"] >= data.get("ageThreshold", 20))

    filtered_matches = enriched_matches[filters]

    # Now compute compound score
    filtered_matches["Compound Similarity Score"] = (
        0.35 * filtered_matches["FNSimilarity"] +
        0.25 * filtered_matches["SNSimilarity"] +
        0.10 * filtered_matches["DOBSimilarity"] +
        0.05 * filtered_matches["AgeSimilarity"] +
        0.10 * filtered_matches["strAddressSimilarity"] +
        0.075 * filtered_matches["originSimilarity"] +
        0.075 * filtered_matches["destinationSimilarity"]
    ).round(4)
    filtered_matches = filtered_matches.sort_values(by="Compound Similarity Score", ascending=False)

    rename_map = {
        "booking_ref": "BookingID",
        "travel_doc": "TravelDocNumber",
        "firstname": "Firstname",
        "surname": "Surname",
        "dob": "DOB",
        "gender": "Sex",
        "nationality": "Nationality",
        "city": "CityName",
        "address": "Address",
        "departure_time": "DepartureDateTime",
        "arrival_time": "ArrivalDateTime",
        "departure_airport": "OriginIATA",
        "arrival_airport": "DestinationIATA",
        "flight_number": "FlightNumber",
        "carrier": "OriginatorAirlineCode",
        "dep_lat": "OriginLat",
        "dep_lon": "OriginLon",
        "arr_lat": "DestinationLat",
        "arr_lon": "DestinationLon",
        "OriginCity": "OriginCity",
        "DestinationCity": "DestinationCity",
        "OriginCountry": "OriginCountry",
        "DestinationCountry": "DestinationCountry",
        "faiss_distance": "FAISS Distance",
        "confidence_score": "Confidence Level",
        "FNSimilarity": "FNSimilarity",
        "SNSimilarity": "SNSimilarity",
        "DOBSimilarity": "DOBSimilarity",
        "DOB1": "DOB1",
        "DOB2": "DOB2",
        "DOB_rarity1": "DOB_rarity1",
        "DOB_rarity2": "DOB_rarity2",
        "DOB_prob1": "DOB_prob1",
        "DOB_prob2": "DOB_prob2",
        "AgeSimilarity": "AgeSimilarity",
        "strAddressSimilarity": "strAddressSimilarity",
        "jcdAddressSimilarity": "jcdAddressSimilarity",
        "cityAddressMatch": "cityAddressMatch",
        "countryAddressMatch": "countryAddressMatch",
        "sexMatch": "sexMatch",
        "natMatch": "natMatch",
        "originAirportMatch": "originAirportMatch",
        "destinationAirportMatch": "destinationAirportMatch",
        "orgdesAirportMatch": "orgdesAirportMatch",
        "desorgAirportMatch": "desorgAirportMatch",
        "originCityMatch": "originCityMatch",
        "destinationCityMatch": "destinationCityMatch",
        "orgdesCityMatch": "orgdesCityMatch",
        "desorgCityMatch": "desorgCityMatch",
        "originCountryMatch": "originCountryMatch",
        "destinationCountryMatch": "destinationCountryMatch",
        "orgdesCountryMatch": "orgdesCountryMatch",
        "desorgCountryMatch": "desorgCountryMatch",
        "originSimilarity": "originSimilarity",
        "originExpScore": "originExpScore",
        "destinationSimilarity": "destinationSimilarity",
        "destinationExpScore": "destinationExpScore",
        "orgdesSimilarity": "orgdesSimilarity",
        "orgdesExpScore": "orgdesExpScore",
        "desorgSimilarity": "desorgSimilarity",
        "desorgExpScore": "desorgExpScore",
        "Compound Similarity Score": "Compound Similarity Score",
        "country": "Country of Address",
    }

    # Apply renaming
    filtered_matches.rename(columns=rename_map, inplace=True)

    # Optional: fill in constant or missing fields
    filtered_matches["FullName"] = filtered_matches["Firstname"] + " " + filtered_matches["Surname"]
    filtered_matches["PlaceOfIssue"] = filtered_matches["Nationality"]
    filtered_matches["PassengerID"] = ""  # or generate UUIDs
    filtered_matches["PNRID"] = ""
    filtered_matches["iata_pnrgov_notif_rq_id"] = ""
    filtered_matches["unique_id"] = 0
    filtered_matches["CityLat"] = ""
    filtered_matches["CityLon"] = ""
    filtered_matches["Confidence Level"] = (filtered_matches["Confidence Level"].fillna(0) * 100).round(4)

    ordered_columns = [
    "unique_id", "PassengerID", "PNRID", "iata_pnrgov_notif_rq_id",
    "OriginIATA", "DestinationIATA", "FlightLegFlightNumber",  # optional alias
    "OriginatorAirlineCode", "FlightNumber", "DepartureDateTime", "ArrivalDateTime",
    "BookingID", "Firstname", "Surname", "FullName", "TravelDocNumber", "PlaceOfIssue",
    "DOB", "Nationality", "Sex", "CityName", "Address",
    "OriginLat", "OriginLon", "DestinationLat", "DestinationLon", "CityLat", "CityLon",
    "OriginCity", "DestinationCity", "OriginCountry", "DestinationCountry", "Country of Address", "FAISS Distance", 
    "Confidence Level", "FNSimilarity", "FN1", "FN2", "FN_rarity1", "FN_rarity2", "FN_prob1", "FN_prob2",
    "SNSimilarity", "SN1", "SN2", "SN_rarity1", "SN_rarity2", "SN_prob1", "SN_prob2",
    "DOBSimilarity", "DOB1", "DOB2", "DOB_rarity1", "DOB_rarity2", "DOB_prob1", "DOB_prob2",
    "AgeSimilarity", "strAddressSimilarity", "jcdAddressSimilarity", "cityAddressMatch",
    "cityAddressRarity1", "cityAddressProb1", "cityAddressRarity2", "cityAddressProb2",
    "countryAddressMatch", "countryAddressRarity2", "countryAddressProb2",
    "sexMatch", "sexRarity2", "sexProb2", "natMatch", "natRarity2", "natProb2",
    "originAirportMatch", "originAirportRarity2", "originAirportProb2",
    "destinationAirportMatch", "destinationAirportRarity2", "destinationAirportProb2",
    "orgdesAirportMatch", "desorgAirportMatch",
    "originCityMatch", "originCityRarity2", "originCityProb2",
    "destinationCityMatch", "destinationCityRarity2", "destinationCityProb2",
    "orgdesCityMatch", "desorgCityMatch",
    "originCountryMatch", "originCountryRarity2", "originCountryProb2",
    "destinationCountryMatch", "destinationCountryRarity2", "destinationCountryProb2",
    "orgdesCountryMatch", "desorgCountryMatch",
    "originSimilarity", "originExpScore",
    "destinationSimilarity", "destinationExpScore",
    "orgdesSimilarity", "orgdesExpScore",
    "desorgSimilarity", "desorgExpScore",
    "Compound Similarity Score"]


    existing_ordered_cols = [col for col in ordered_columns if col in filtered_matches.columns]
    filtered_matches = filtered_matches[existing_ordered_cols]

    filtered_matches_json = filtered_matches.to_dict(orient="records")

    # Copy logic from inside your Celery task here
    
    


    ...
    
    if not filtered_matches_json:
        return {
            "status": "success",
            "message": "No similar passengers found.",
            "data": []
        }

    return {
        "status": "success",
        "data": filtered_matches_json
    }
