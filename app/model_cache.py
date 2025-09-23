from app.dob_vectorisers import get_dob_char_vectorizer, get_dob_token_vectorizer
import joblib
import faiss
from functools import lru_cache
import pandas as pd
import numpy as np

@lru_cache(maxsize=2)
def load_model_bundle(shard_label: str):
    # Build DOB vectorizers and load vocabularies
    tfidf_dob_char = get_dob_char_vectorizer()
    tfidf_dob_char.vocabulary_ = joblib.load(f"model/tfidf_dob_char_vocab_{shard_label}.pkl")
    tfidf_dob_char.fixed_vocabulary_ = True
    tfidf_dob_char.fit(["0000-00-00"])


    tfidf_dob_token = get_dob_token_vectorizer()
    tfidf_dob_token.vocabulary_ = joblib.load(f"model/tfidf_dob_token_vocab_{shard_label}.pkl")
    tfidf_dob_token.fixed_vocabulary_ = True
    tfidf_dob_token.fit(["0000-00-00"])  # <-- this initializes it too


    return {
        "encoder": joblib.load(f"model/encoder_{shard_label}.pkl"),
        "scaler": joblib.load(f"model/scaler_{shard_label}.pkl"),
        "tfidf_name": joblib.load(f"model/tfidf_name_{shard_label}.pkl"),
        "svd_name": joblib.load(f"model/svd_name_{shard_label}.pkl"),
        "tfidf_addr": joblib.load(f"model/tfidf_addr_{shard_label}.pkl"),
        "svd_addr": joblib.load(f"model/svd_addr_{shard_label}.pkl"),
        "tfidf_consonant": joblib.load(f"model/tfidf_consonant_{shard_label}.pkl"),
        "svd_consonant": joblib.load(f"model/svd_consonant_{shard_label}.pkl"),
        "tfidf_phonetic": joblib.load(f"model/tfidf_phonetic_{shard_label}.pkl"),
        "svd_phonetic": joblib.load(f"model/svd_phonetic_{shard_label}.pkl"),
        "tfidf_dob_char": tfidf_dob_char,
        "tfidf_dob_token": tfidf_dob_token,
        "index": faiss.read_index(f"model/faiss_IVF_{shard_label}.index", faiss.IO_FLAG_MMAP),
        "metadata": pd.read_parquet(f"model/metadata_{shard_label}.parquet")
    }
