import numpy as np
import pandas as pd
import re
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
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
    encoder,
    scaler,
    tfidf_vectorizer,
    svd_model,
    chunk_size: int = 50000
):
    """
    Generate embeddings for passenger records by combining:
    - Scaled numeric features
    - One-hot encoded categorical features
    - TF-IDF vectorized name/address text

    Args:
        df (pd.DataFrame): Input passenger DataFrame
        encoder: Pre-fitted OneHotEncoder (or None if fitting)
        scaler: Pre-fitted StandardScaler (or None if fitting)
        tfidf_vectorizer: Pre-fitted TfidfVectorizer (or None if fitting)
        fit (bool): Whether to fit the encoders/scaler/vectorizer
        chunk_size (int): Chunk size for embedding processing

    Returns:
        tuple: (embeddings, fitted_encoder, fitted_scaler, fitted_tfidf)
    """
    # === Numeric Features ===
    df_numeric = df[NUMERIC_FEATURES].copy().fillna(-9999)
    df_numeric = np.clip(df_numeric, -1e5, 1e5)

    numeric_data = scaler.transform(df_numeric)

    # === Categorical Features ===
    df_cat = df[CATEGORICAL_FEATURES].copy().fillna("unknown")

    categorical_data = encoder.transform(df_cat)

    df = df.rename(columns={"firstname": "given_name"})
    # === Text Features (char n-gram TF-IDF) ===
    for col in TEXT_FEATURES:
        df[col] = df[col].apply(normalize_text)

    text_data = (
        df["given_name"].fillna("") + " " +
        df["surname"].fillna("") + " " +
        df["address"].fillna("")
    ).str.lower()
    text_data = text_data.replace(r'^\s*$', 'EMPTY_DOC', regex=True)

    text_vectors = tfidf_vectorizer.transform(text_data)
    text_vectors = text_vectors.toarray() if sp.issparse(text_vectors) else text_vectors
    text_vectors_reduced = svd_model.transform(text_vectors)

    # === Combine Features into Final Embeddings ===
    num_samples = len(df)
    embedding_dim = numeric_data.shape[1] + categorical_data.shape[1] + text_vectors_reduced.shape[1]
    embeddings = np.zeros((num_samples, embedding_dim), dtype=np.float32)

    for i in range(0, num_samples, chunk_size):
        end = min(i + chunk_size, num_samples)
        embeddings[i:end, :numeric_data.shape[1]] = numeric_data[i:end]
        embeddings[i:end, numeric_data.shape[1]:numeric_data.shape[1] + categorical_data.shape[1]] = categorical_data[i:end]
        embeddings[i:end, -text_vectors_reduced.shape[1]:] = text_vectors_reduced[i:end]

    embeddings = np.nan_to_num(embeddings, nan=0.0)
    assert not np.isnan(embeddings).any(), "NaNs detected in final embeddings"

    logging.info(f"numeric_data shape: {numeric_data.shape}")
    logging.info(f"categorical_data shape: {categorical_data.shape}")
    logging.info(f"text_vectors_reduced shape: {text_vectors_reduced.shape}")
    logging.info(f"embeddings shape: {embeddings.shape}")

    return embeddings, encoder, scaler, tfidf_vectorizer, svd_model
