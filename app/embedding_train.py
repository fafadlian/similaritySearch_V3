import numpy as np
import pandas as pd
import re
from unidecode import unidecode
from dateutil.parser import parse

from metaphone import doublemetaphone

from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from dob_vectorisers import get_dob_char_vectorizer, get_dob_token_vectorizer

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
    if pd.isna(text) or not isinstance(text, str):
        return ""
    text = unidecode(text)
    text = text.lower()
    return re.sub(r"[^a-z0-9]", "", text)

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
    categorical_data[:, 1] *= 0.01  # Reduce weight of 'nationality'

    # === Normalize and combine names ===
    df["firstname"] = df["firstname"].fillna("").apply(normalize_text)
    df["surname"] = df["surname"].fillna("").apply(normalize_text)
    full_name = (df["firstname"] + " " + df["surname"]).str.strip().replace(r"^\s*$", "emptydoc", regex=True)
    df["dob"] = df["dob"].fillna("").apply(normalize_dob)
    dob = df["dob"]
    dob[dob == ""] = "0000-00-00"

    # === Address normalization ===
    df["address"] = df["address"].fillna("").apply(normalize_text)
    address_block = df["address"].str.strip().replace(r"^\s*$", "emptydoc", regex=True)

    # === Derive consonant-only and phonetic features ===
    name_consonant = full_name.apply(strip_vowels)
    name_phonetic = full_name.apply(get_metaphone_code)

    # === TF-IDF + SVD on full name ===
    tfidf_name = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 6), max_features=700)
    svd_name = TruncatedSVD(n_components=150, random_state=42)
    X_name = tfidf_name.fit_transform(full_name)
    X_name_reduced = svd_name.fit_transform(X_name)

    # === TF-IDF + SVD on consonant-only name ===
    tfidf_consonant = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 6), max_features=500)
    svd_consonant = TruncatedSVD(n_components=50, random_state=42)
    X_consonant = tfidf_consonant.fit_transform(name_consonant)
    X_consonant_reduced = svd_consonant.fit_transform(X_consonant)

    # === TF-IDF + SVD on phonetic code ===
    tfidf_phonetic = TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 4), max_features=300)
    svd_phonetic = TruncatedSVD(n_components=30, random_state=42)
    X_phonetic = tfidf_phonetic.fit_transform(name_phonetic)
    X_phonetic_reduced = svd_phonetic.fit_transform(X_phonetic)

    # === TF-IDF + SVD on Address ===
    tfidf_addr = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_features=700)
    svd_addr = TruncatedSVD(n_components=75, random_state=42)
    X_addr = tfidf_addr.fit_transform(address_block)
    X_addr_reduced = svd_addr.fit_transform(X_addr)

    #TF-IDF + SVD on DOB
    tfidf_dob_char = get_dob_char_vectorizer()
    tfidf_dob_token = get_dob_token_vectorizer()
    X_dob_char = tfidf_dob_char.fit_transform(dob)
    X_dob_token = tfidf_dob_token.fit_transform(dob)
    X_dob = sp.hstack([X_dob_char, X_dob_token], format='csr').toarray()
    X_dob = X_dob.astype(np.float32)



    # === Weighted Concatenation ===
    text_features = np.hstack([
        X_name_reduced * 1.5,
        X_consonant_reduced * 1.0,
        X_phonetic_reduced * 0.8,
        X_addr_reduced * 0.8,
        X_dob * 0.7
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

    return embeddings, encoder, scaler, tfidf_name, tfidf_addr, svd_name, svd_addr, tfidf_consonant, svd_consonant, tfidf_phonetic, svd_phonetic, tfidf_dob_char, tfidf_dob_token