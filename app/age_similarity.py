from datetime import datetime
from fuzzywuzzy import fuzz
import pandas as pd
import numpy as np
import logging

def calculate_age(dob):
    """Calculate age from pandas Timestamp."""
    if pd.isnull(dob):
        return np.nan

    try:
        dob = pd.to_datetime(dob)
    except Exception:
        logging.info("Invalid DOB value")
        return np.nan

    today = pd.Timestamp.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return max(age, 0)

def age_similarity_score(query_dob, dob):
    """Calculate similarity between two datetime-based DOBs."""
    if pd.isnull(query_dob) or pd.isnull(dob):
        logging.info("Missing DOB for age similarity calculation")
        return 0

    query_age = calculate_age(query_dob)
    actual_age = calculate_age(dob)

    if np.isnan(query_age) or np.isnan(actual_age) or query_age == 0 or actual_age == 0:
        logging.info("Invalid DOB for age similarity calculation")
        return 0

    age_difference = abs(query_age - actual_age)
    if age_difference == 0:
        return 100

    max_age = max(actual_age, query_age)
    min_age = min(actual_age, query_age)

    if min_age == 0:
        return 0

    log_age_diff = np.log(max_age / min_age)
    return max(0, 100 - (log_age_diff * 100))


def dob_string_similarity(dob1, dob2):
    """
    Compute string similarity on two DOBs (datetime or string).
    Returns: [similarity, str_dob1, str_dob2, rarity1, rarity2, prob1, prob2]
    """
    if pd.isnull(dob1) or pd.isnull(dob2):
        return pd.Series([np.nan, dob1, dob2, np.nan, np.nan, np.nan, np.nan])

    try:
        dob1_str = pd.to_datetime(dob1).strftime('%Y-%m-%d')
        dob2_str = pd.to_datetime(dob2).strftime('%Y-%m-%d')
    except Exception:
        return pd.Series([np.nan, dob1, dob2, np.nan, np.nan, np.nan, np.nan])

    str_similarity = fuzz.ratio(dob1_str, dob2_str)
    return pd.Series([str_similarity, dob1_str, dob2_str, 0, 0, 0, 0])

# Example Usage
# dob_example = datetime(2000, 1, 1)  # Example DOB
# query_age =  12 # Example query age

# similarity_score = age_similarity_score(query_age, dob_example)
# print(f"Age similarity score: {similarity_score:.2f}")