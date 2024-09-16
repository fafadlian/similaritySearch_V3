
from fuzzywuzzy import fuzz
import pandas as pd
import numpy as np

def count_likelihood2(x, counter, num_records):
    """
    Calculates the likelihood based on counts from the counter, with internal defaults for unseen categories.

    :param x: The category to look up.
    :param counter: A dictionary with counts of each category.
    :param num_records: The total number of records.
    :return: A pandas Series containing the rarity and probability.
    """
    # Default values for unseen categories
    default_rarity = 100.0
    default_prob = 0.0
    
    if isinstance(x, pd.Series):
        x = x.iloc[0] if not x.empty else np.nan

    if pd.isnull(x) or not isinstance(x, str):
        return pd.Series([default_rarity, default_prob])
    
    x_lower = x.lower()
    x_count = counter.get(x_lower, 0)
    
    if x_count > 0 and num_records > 0:
        rarity = min((x_count / num_records) * 100, 100)  # Scale rarity to 0-100
        prob = min((1 / x_count) * 100, 100)  # Scale probability to 0-100
    else:
        rarity = default_rarity
        prob = default_prob

    return pd.Series([rarity, prob])

    
def string_similarity(string1, string2, string_counts, num_records):
    """
    Calculate string similarity, rarity, and probability.

    :param string1: First string to compare.
    :param string2: Second string to compare.
    :param string_counts: A dictionary with counts of each string.
    :param num_records: The total number of records.
    :return: A pandas Series containing similarity, rarity, and probability metrics.
    """
    if not isinstance(num_records, int) or num_records <= 0:
        raise ValueError("num_records must be a positive integer.")
    
    if pd.isnull(string1) or pd.isnull(string2):
        return pd.Series([np.nan, string1, string2, np.nan, np.nan, np.nan, np.nan])
    
    string1_lower = string1.lower()
    string2_lower = string2.lower()
    
    str_similarity = fuzz.ratio(string1_lower, string2_lower)
    
    count1 = string_counts.get(string1_lower, 0)
    count2 = string_counts.get(string2_lower, 0)
    
    rarity1 = min((count1 / num_records) * 100, 100)
    rarity2 = min((count2 / num_records) * 100, 100)
    
    prob1 = 100 if count1 == 0 else min((1 / count1) * 100, 100)
    prob2 = 100 if count2 == 0 else min((1 / count2) * 100, 100)
    
    return pd.Series([str_similarity, string1, string2, rarity1, rarity2, prob1, prob2])