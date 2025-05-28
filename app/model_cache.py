import joblib
import faiss
import pandas as pd
from functools import lru_cache

@lru_cache(maxsize=2)  # hold up to 2 shards in RAM
def load_model_bundle(shard_label: str):
    return {
        "encoder": joblib.load(f"model/encoder_{shard_label}.pkl"),
        "scaler": joblib.load(f"model/scaler_{shard_label}.pkl"),
        "tfidf": joblib.load(f"model/tfidf_{shard_label}.pkl"),
        "svd": joblib.load(f"model/svd_{shard_label}.pkl"),
        "index": faiss.read_index(f"model/faiss_flat_{shard_label}.index", faiss.IO_FLAG_MMAP),
        "metadata": pd.read_parquet(f"model/metadata_{shard_label}.parquet")
    }
