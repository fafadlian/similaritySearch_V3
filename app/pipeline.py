# app/pipeline.py
import numpy as np
import pandas as pd
from app.loc_access import LocDataAccess
from app.model_cache import load_model_bundle
from app.faiss_search import faiss_search_with_metadata
from app.embedding import embed_passengers
from app.similarity_metrics import compute_similarity_features
from app.utils import compute_relative_age, enrich_location, infer_shards_for_date

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

    shard_label = infer_shards_for_date(data["arrival_date_from"], data["shards"])
    models = load_model_bundle(shard_label)

    # Embed
    embedding, _, _, _, _ = embed_passengers(query_df, models["encoder"], models["scaler"], models["tfidf"], models["svd"])
    embedding = np.nan_to_num(embedding.astype("float32"))

    matches = faiss_search_with_metadata(embedding, models["index"], models["metadata"]["travel_doc"].values, models["metadata"])

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
        0.3 * filtered_matches["FNSimilarity"] +
        0.3 * filtered_matches["SNSimilarity"] +
        0.1 * filtered_matches["DOBSimilarity"] +
        0.1 * filtered_matches["strAddressSimilarity"] +
        0.1 * filtered_matches["AgeSimilarity"] +
        0.05 * filtered_matches["originSimilarity"] +
        0.05 * filtered_matches["destinationSimilarity"]
    ).round(4)

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
