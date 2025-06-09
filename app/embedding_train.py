import numpy as np
import pandas as pd
import re
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from scipy import sparse as sp
from config import NUMERIC_FEATURES, CATEGORICAL_FEATURES, TEXT_FEATURES

    # --- FastBM25 Vectorization ---
def safe_tokenize(text):
    """Generate 3-grams with guaranteed non-empty output"""
    text = str(text)  # Ensure we're working with strings
    if len(text) < 3:
        # For texts shorter than 3 chars, return the whole text as single token
        # plus padding if needed (e.g., "a" -> ["a__"])
        padded = text.ljust(3, '_')  # Pad with underscores
        return [padded]
    # Normal case: generate all possible 3-grams
    return [text[i:i+3] for i in range(len(text)-2)]


def normalize_text(text: str) -> str:
    if pd.isna(text):
        return ""
    # Lowercase
    text = text.lower()
    # Remove non-alphanumeric (keep letters & digits only)
    text = re.sub(r"[^\w]", "", text)
    return text

   

def embed_passengers_train(df, encoder=None, scaler=None, tfidf_name=None, tfidf_addr=None, svd_name=None, svd_addr=None, fit=True):
    # === Numeric Features ===
    df_numeric = df[NUMERIC_FEATURES].fillna(-9999)
    df_numeric = np.clip(df_numeric, -1e5, 1e5)
    if fit:
        scaler = StandardScaler()
        numeric_data = scaler.fit_transform(df_numeric)
        numeric_data *= 0.1
    else:
        numeric_data = scaler.transform(df_numeric)

    # === Categorical Features ===
    df_cat = df[CATEGORICAL_FEATURES].fillna("unknown")
    if fit:
        encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
        categorical_data = encoder.fit_transform(df_cat)
    else:
        categorical_data = encoder.transform(df_cat)

    categorical_data[:, 0] *= 0.5  # Reduce weight of 'sex'
    categorical_data[:, 1] *= 0.4  # Reduce weight of 'nationality'

   # === Text Normalization ===
    for col in ["firstname", "surname", "address"]:
        df[col] = df[col].fillna("").apply(normalize_text)

    # === Compose text blocks and prevent empty strings ===
    full_name = (df["firstname"] + " " + df["surname"]).str.strip()
    address_block = df["address"].str.strip()

    # Replace fully empty strings with 'emptydoc' to avoid empty TF-IDF vocab
    full_name = full_name.mask(full_name.str.fullmatch(r"\s*"), "emptydoc")
    address_block = address_block.mask(address_block.str.fullmatch(r"\s*"), "emptydoc")

    # === TF-IDF + SVD on Full Name ===

    tfidf_name = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_features=700)
    svd_name = TruncatedSVD(n_components=150, random_state=42)

    if full_name.str.strip().str.len().sum() == 0:
        raise ValueError("❌ All 'full_name' entries are empty after normalization.")

    X_name = tfidf_name.fit_transform(full_name)
    X_name_reduced = svd_name.fit_transform(X_name)



    # === TF-IDF + SVD on Address ===

    tfidf_addr = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_features=700)
    svd_addr = TruncatedSVD(n_components=75, random_state=42)

    if address_block.str.strip().str.len().sum() == 0:
        raise ValueError("❌ All 'address_block' entries are empty after normalization.")

    X_addr = tfidf_addr.fit_transform(address_block)
    X_addr_reduced = svd_addr.fit_transform(X_addr)


    # === Weighted Concatenation ===
    text_features = np.hstack([
        X_name_reduced * 1.5,
        X_addr_reduced * 0.8
    ])

    # === Final Embedding Concatenation ===
    embeddings = np.hstack([
        numeric_data,
        categorical_data,
        text_features
    ]).astype(np.float32)

    embeddings = np.nan_to_num(embeddings, nan=0.0)
    assert not np.isnan(embeddings).any(), "NaNs detected in final embeddings!"

    print("Train numeric:", numeric_data.shape[1])
    print("Train categorical:", categorical_data.shape[1])
    print("Train name reduced:", X_name_reduced.shape[1])
    print("Train address reduced:", X_addr_reduced.shape[1])
    print("Train final embedding:", embeddings.shape[1])

    return embeddings, encoder, scaler, tfidf_name, tfidf_addr, svd_name, svd_addr