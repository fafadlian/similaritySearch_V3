import numpy as np
import pandas as pd
import re
from dateutil.parser import parse
from metaphone import doublemetaphone
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from app.dob_vectorisers import get_dob_char_vectorizer, get_dob_token_vectorizer
from sklearn.decomposition import TruncatedSVD
from scipy import sparse as sp
from app.config import NUMERIC_FEATURES, CATEGORICAL_FEATURES, TEXT_FEATURES
import logging


def normalize_text(text: str) -> str:
    if pd.isna(text):
        return ""
    text = text.lower()
    return re.sub(r"[^\w]", "", text)


def strip_vowels(text: str) -> str:
    return re.sub(r"[aeiou]", "", text)


def get_metaphone_code(text: str) -> str:
    code = doublemetaphone(text)
    return code[0] or code[1] or "emptyphon"

def normalize_dob(dob_str):
    if isinstance(dob_str, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", dob_str):
        return dob_str
    return "0000-00-00"
    
def dob_tokenizer(dob):
    return dob.split("-") if isinstance(dob, str) else ["0000", "00", "00"]


def embed_passengers(
    df: pd.DataFrame,
    encoder: OneHotEncoder,
    scaler: StandardScaler,
    tfidf_name: TfidfVectorizer,
    tfidf_addr: TfidfVectorizer,
    svd_name: TruncatedSVD,
    svd_addr: TruncatedSVD,
    tfidf_consonant: TfidfVectorizer,
    svd_consonant: TruncatedSVD,
    tfidf_phonetic: TfidfVectorizer,
    svd_phonetic: TruncatedSVD,
    tfidf_dob_char: TfidfVectorizer,
    tfidf_dob_token: TfidfVectorizer,
):
    # === Numeric Features ===
    df_numeric = df[NUMERIC_FEATURES].copy().fillna(-9999)
    df_numeric = np.clip(df_numeric, -1e5, 1e5)
    numeric_data = scaler.transform(df_numeric) * 0.1

    # === Categorical Features ===
    df_cat = df[CATEGORICAL_FEATURES].copy().fillna("unknown")
    categorical_data = encoder.transform(df_cat)
    categorical_data[:, 0] *= 0.5  # 'sex'
    categorical_data[:, 1] *= 0.01  # 'nationality'

    # === Normalize text columns ===
    df["firstname"] = df["firstname"].fillna("").apply(normalize_text)
    df["surname"] = df["surname"].fillna("").apply(normalize_text)
    df["address"] = df["address"].fillna("").apply(normalize_text)
    df["dob"] = df["dob"].fillna("").apply(normalize_dob)
    dob = df["dob"]
    dob[dob == ""] = "0000-00-00"


    full_name = (df["firstname"] + " " + df["surname"]).str.strip().replace(r"^\s*$", "emptydoc", regex=True)
    address_block = df["address"].str.strip().replace(r"^\s*$", "emptydoc", regex=True)

    # === Enrich name representations ===
    name_consonant = full_name.apply(strip_vowels)
    name_phonetic = full_name.apply(get_metaphone_code)

    # === TF-IDF + SVD on Full Name ===
    X_name = tfidf_name.transform(full_name)
    X_name_reduced = svd_name.transform(X_name)

    # === TF-IDF + SVD on Consonant-only Name ===
    X_consonant = tfidf_consonant.transform(name_consonant)
    X_consonant_reduced = svd_consonant.transform(X_consonant)

    # === TF-IDF + SVD on Phonetic Code ===
    X_phonetic = tfidf_phonetic.transform(name_phonetic)
    X_phonetic_reduced = svd_phonetic.transform(X_phonetic)

    # === TF-IDF + SVD on Address ===
    X_addr = tfidf_addr.transform(address_block)
    X_addr_reduced = svd_addr.transform(X_addr)

    # === TF-IDF + SVD on DOB ===
    X_dob_char = tfidf_dob_char.transform(dob)
    X_dob_token = tfidf_dob_token.transform(dob)
    X_dob_combined = sp.hstack([X_dob_char, X_dob_token], format='csr').toarray()
    X_dob_combined = X_dob_combined.astype(np.float32)

    # === Weighted Concatenation ===
    text_features = np.hstack([
        X_name_reduced * 1.5,
        X_consonant_reduced * 1.0,
        X_phonetic_reduced * 0.8,
        X_addr_reduced * 0.8,
        X_dob_combined * 0.7

    ])

    # === Final Embedding ===
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

    return embeddings
