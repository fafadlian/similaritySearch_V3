import numpy as np
import pandas as pd
import re
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from scipy import sparse as sp
from app.config import NUMERIC_FEATURES, CATEGORICAL_FEATURES, TEXT_FEATURES
import logging


def normalize_text(text: str) -> str:
    if pd.isna(text):
        return ""
    # Lowercase
    text = text.lower()
    # Remove non-alphanumeric (keep letters & digits only)
    text = re.sub(r"[^\w]", "", text)
    return text


def embed_passengers(
    df: pd.DataFrame,
    encoder: OneHotEncoder,
    scaler: StandardScaler,
    tfidf_name: TfidfVectorizer,
    tfidf_addr: TfidfVectorizer,
    svd_name: TruncatedSVD,
    svd_addr: TruncatedSVD,
):
    # === Numeric Features ===
    df_numeric = df[NUMERIC_FEATURES].copy().fillna(-9999)
    df_numeric = np.clip(df_numeric, -1e5, 1e5)
    numeric_data = scaler.transform(df_numeric) * 0.1

    # === Categorical Features ===
    df_cat = df[CATEGORICAL_FEATURES].copy().fillna("unknown")
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
    X_name = tfidf_name.transform(full_name)
    X_name_reduced = svd_name.transform(X_name)

    # === TF-IDF + SVD on Address ===
    X_addr = tfidf_addr.transform(address_block)
    X_addr_reduced = svd_addr.transform(X_addr)

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
    assert not np.isnan(embeddings).any(), "NaNs detected in final embeddings"

    logging.info(f"numeric_data shape     : {numeric_data.shape}")
    logging.info(f"categorical_data shape : {categorical_data.shape}")
    logging.info(f"text_features shape    : {text_features.shape}")
    logging.info(f"final embeddings shape : {embeddings.shape}")

    return embeddings, encoder, scaler, tfidf_name, tfidf_addr, svd_name, svd_addr
