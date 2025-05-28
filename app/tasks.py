from app.celery_app import celery_app
from app.utils import compute_relative_age, enrich_location, infer_shards_for_date
from app.embedding import embed_passengers
from app.faiss_search import faiss_search_with_metadata
from app.similarity_metrics import compute_similarity_features
from app.loc_access import LocDataAccess
from app.model_cache import load_model_bundle
import pandas as pd
import numpy as np
import logging




@celery_app.task
def process_similarity_task(data):
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
        "iata_o": data.get("departure_airport", ""),
        "iata_d": data.get("arrival_airport", ""),
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
        lat_o=lon_o,
        lon_o=lat_o,
        lat_d=lon_d,
        lon_d=lat_d,
    )

    enriched_matches = pd.concat([matches, sim_df], axis=1)
    enriched_matches.replace([np.inf, -np.inf], np.nan, inplace=True)
    enriched_matches.fillna(0, inplace=True)

    return enriched_matches.to_dict(orient="records")