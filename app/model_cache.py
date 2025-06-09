import joblib
import faiss
import pandas as pd
from functools import lru_cache

@lru_cache(maxsize=2)  # hold up to 2 shards in RAM
def load_model_bundle(shard_label: str):
    return {
        "encoder": joblib.load(f"model/encoder_{shard_label}.pkl"),
        "scaler": joblib.load(f"model/scaler_{shard_label}.pkl"),
        "tfidf_name": joblib.load(f"model/tfidf_name_{shard_label}.pkl"),
        "tfidf_addr": joblib.load(f"model/tfidf_addr_{shard_label}.pkl"),
        "svd_name": joblib.load(f"model/svd_name_{shard_label}.pkl"),
        "svd_addr": joblib.load(f"model/svd_addr_{shard_label}.pkl"),
        "index": faiss.read_index(f"model/faiss_IVF_{shard_label}.index", faiss.IO_FLAG_MMAP),
        "metadata": pd.read_parquet(f"model/metadata_{shard_label}.parquet")
    }
