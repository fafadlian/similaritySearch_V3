import os
import joblib
import faiss
import pandas as pd
from dateutil.relativedelta import relativedelta
from embedding_train import embed_passengers_train


def split_and_index_metadata(
    df,
    PROCESSED_METADATA_PATH,
    PREPROCESSOR_DIR,
    FAISS_INDEX_DIR,
    start_date="2019-01-01",
    end_date="2020-01-01",
    time_window_months=2
):
    """
    Splits metadata into fixed non-overlapping time windows (default 2 months),
    then creates and saves FAISS index, encoder, scaler, and TFIDF vectorizer for each shard.
    """
    df["departure_time"] = pd.to_datetime(df["departure_time"])
    df["arrival_time"] = pd.to_datetime(df["arrival_time"])
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    shard_labels = []

    current = start_date

    while current < end_date:
        window_start = current
        window_end = current + relativedelta(months=time_window_months)

        if window_end > end_date:
            window_end = end_date

        label = f"{window_start.strftime('%Y-%m-%d')}_{(window_end - pd.Timedelta(days=1)).strftime('%Y-%m-%d')}"
        # label = f"{window_start.strftime('%Y-%m-%d')}_{window_end.strftime('%Y-%m-%d')}"

        df_shard = df[
            (df["departure_time"] >= window_start) &
            (df["departure_time"] < window_end)]
        print("df_shard len:", len(df_shard), "label:", label)



        # print(f"🔍 Shard: {label} | Range: {window_start.date()} to {(window_end - pd.Timedelta(days=1)).date()} | Records: {len(df_shard)}")

        if df_shard.empty:
            current = window_end
            continue

        shard_labels.append(label)


        # Save metadata
        df_shard.to_parquet(os.path.join(PROCESSED_METADATA_PATH, f"metadata_{label}.parquet"), index=False)

        # Compute embeddings and preprocessing objects
        embeddings, encoder, scaler, tfidf_name, tfidf_addr, svd_name, svd_addr, tfidf_consonant, svd_consonant, tfidf_phonetic, svd_phonetic, tfidf_dob_char, tfidf_dob_token  = embed_passengers_train(df_shard, fit=True)

        joblib.dump(encoder, os.path.join(PREPROCESSOR_DIR, f"encoder_{label}.pkl"))
        joblib.dump(scaler, os.path.join(PREPROCESSOR_DIR, f"scaler_{label}.pkl"))
        joblib.dump(tfidf_name, os.path.join(PREPROCESSOR_DIR, f"tfidf_name_{label}.pkl"))
        joblib.dump(tfidf_addr, os.path.join(PREPROCESSOR_DIR, f"tfidf_addr_{label}.pkl"))
        joblib.dump(svd_name, os.path.join(PREPROCESSOR_DIR, f"svd_name_{label}.pkl"))
        joblib.dump(svd_addr, os.path.join(PREPROCESSOR_DIR, f"svd_addr_{label}.pkl"))
        joblib.dump(tfidf_consonant, os.path.join(PREPROCESSOR_DIR, f"tfidf_consonant_{label}.pkl"))
        joblib.dump(svd_consonant, os.path.join(PREPROCESSOR_DIR, f"svd_consonant_{label}.pkl"))
        joblib.dump(tfidf_phonetic, os.path.join(PREPROCESSOR_DIR, f"tfidf_phonetic_{label}.pkl"))
        joblib.dump(svd_phonetic, os.path.join(PREPROCESSOR_DIR, f"svd_phonetic_{label}.pkl"))
        joblib.dump(tfidf_dob_char.vocabulary_, os.path.join(PREPROCESSOR_DIR, f"tfidf_dob_char_vocab_{label}.pkl"))
        joblib.dump(tfidf_dob_token.vocabulary_, os.path.join(PREPROCESSOR_DIR, f"tfidf_dob_token_vocab_{label}.pkl"))


        # Build FAISS HNSW Index
        # index = faiss.IndexHNSWFlat(embeddings.shape[1], 32)
        # index.hnsw.efConstruction = 200
        # index.add(embeddings)
        # faiss.write_index(index, os.path.join(FAISS_INDEX_DIR, f"faiss_hnsw_{label}.index"))

        # Build FAISS IVF index
        # Number of clusters (you can tune this)
        # nlist = 500  # e.g. 100–1000 for moderate dataset sizes
        # quantizer = faiss.IndexFlatL2(embeddings.shape[1])  # same dimension
        # index = faiss.IndexIVFFlat(quantizer, embeddings.shape[1], nlist, faiss.METRIC_L2)
        # assert not index.is_trained
        # index.train(embeddings)
        # assert index.is_trained
        # index.add(embeddings)

        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(embeddings)
        faiss.write_index(index, os.path.join(FAISS_INDEX_DIR, f"faiss_IVF_{label}.index"))
        # print(f"✅ Saved shard {label}: {len(df_shard)} records | dim: {embeddings.shape[1]} | IVF(nlist={nlist})")
        current = window_end  # Advance to next non-overlapping window

    return shard_labels
