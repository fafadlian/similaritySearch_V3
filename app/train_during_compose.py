import os
import time
import pandas as pd
from glob import glob
import joblib
from multiprocessing import Pool, cpu_count
import faiss

from parser import parse_large_pnr_xml, compute_relative_age
from embedding_train import embed_passengers_train
from data_and_index_split import split_and_index_metadata

from loc_access import LocDataAccess
from config import (
    PREPROCESSOR_DIR,
    XML_FOLDER,
)

def parse_wrapper(xml_path):
    try:
        last_modified = os.path.getmtime(xml_path)
        return list(parse_large_pnr_xml(xml_path, last_modified=last_modified))
    except Exception as e:
        print(f" Error parsing {xml_path}: {e}")
        return []
# === Step 1: Parse XML ===
def parse_all_xml(folder, chunk_size=5000):
    from glob import glob
    from multiprocessing import Pool, cpu_count
    import pandas as pd

    print(f"Parsing from folder: {folder}")
    files = glob(os.path.join(folder, "*.xml"))
    print(f"Found {len(files)} XML files.")

    passengers = []
    with Pool(processes=cpu_count()) as pool:
        for result in pool.imap_unordered(parse_wrapper, files):
            passengers.extend(result)

    return pd.DataFrame(passengers)

def enrich_location(df):
    loc_access = LocDataAccess.get_instance()

    # Map IATA to lon/lat tuples
    df["dep_lon"], df["dep_lat"] = zip(*df["departure_airport"].map(loc_access.get_airport_lon_lat_by_iata))
    df["arr_lon"], df["arr_lat"] = zip(*df["arrival_airport"].map(loc_access.get_airport_lon_lat_by_iata))

    # Replace missing values with 0.0
    df["dep_lon"] = pd.to_numeric(df["dep_lon"], errors="coerce").fillna(0.0)
    df["dep_lat"] = pd.to_numeric(df["dep_lat"], errors="coerce").fillna(0.0)
    df["arr_lon"] = pd.to_numeric(df["arr_lon"], errors="coerce").fillna(0.0)
    df["arr_lat"] = pd.to_numeric(df["arr_lat"], errors="coerce").fillna(0.0)

    return df


if __name__ == "__main__":
    start = time.time()
    print("Training start (during Docker compose)...")

    # Step 1: Parse
    print("Parsing XML files...")
    print("Parsing from folder:", XML_FOLDER)
    df = parse_all_xml(folder="data/raw_xml")  # change folder if needed
    print(f"Parsed {len(df)} passengers.")

    # Save full metadata parquet (optional)
    # label = "2019-01-01_2020-01-01"  # Example label, adjust as needed
    df = compute_relative_age(df)
    df = enrich_location(df)
    # df.to_parquet(os.path.join(PREPROCESSOR_DIR, f"metadata_{label}.parquet"), index=False)


    labels = split_and_index_metadata(
        df,
        PREPROCESSOR_DIR,
        PREPROCESSOR_DIR,
        PREPROCESSOR_DIR,
        start_date="2019-01-01",
        end_date="2020-01-01",
        time_window_months=2
        )
    print(f"Created {len(labels)} shards: {labels}")
    print(f"labels: {labels}")


    # Step 2: Feature enrichment
    

    # Step 3: Embed and save FAISS index per shard
    # print("🔗 Creating FAISS index per shard...")
    # embeddings, encoder, scaler, tfidf, svd_model = embed_passengers_train(df, fit=True)


    # joblib.dump(encoder, os.path.join(PREPROCESSOR_DIR, f"encoder_{label}.pkl"))
    # joblib.dump(scaler, os.path.join(PREPROCESSOR_DIR, f"scaler_{label}.pkl"))
    # joblib.dump(tfidf, os.path.join(PREPROCESSOR_DIR, f"tfidf_{label}.pkl"))
    # joblib.dump(svd_model, os.path.join(PREPROCESSOR_DIR, f"svd_{label}.pkl"))
    # index = faiss.IndexFlatL2(embeddings.shape[1])
    # index.add(embeddings)
    # faiss.write_index(index, os.path.join(PREPROCESSOR_DIR, f"faiss_IVF_{label}.index"))



    print(f" Training complete in {round(time.time() - start, 2)} seconds.")