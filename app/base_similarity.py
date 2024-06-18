
from fuzzywuzzy import fuzz
import pandas as pd
import numpy as np

def count_likelihood2(x, counter, num_records):
    """
    Calculates the likelihood based on counts from the counter, with internal defaults for unseen categories.

    :param x: The category to look up.
    :param counter: A collection with counts of each category.
    :param num_records: The total number of records.
    :return: A pandas Series containing the rarity and probability.
    """
    # Default values for unseen categories
    default_rarity = 100.0  # Adjust as needed, e.g., for very rare categories
    default_prob = 0.0  # or some other sensible default for your use case
    if isinstance(x, pd.Series):
        x = x.iloc[0] if not x.empty else np.nan

    # Get the count of 'type', defaulting to 0 if not found
    if isinstance(x, str):
        x_count = counter.get(x.lower(), 0)
    else:
        x_count = np.nan
    
    # Calculate rarity and probability
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
    # Check for valid input
    if not isinstance(num_records, int) or num_records <= 0:
        raise ValueError("num_records must be a positive integer.")
    
    # Handle NaN values
    if pd.isnull(string1) or pd.isnull(string2):
        return pd.Series([np.nan, string1, string2, np.nan, np.nan, np.nan, np.nan])
    
    # Calculate string similarity
    try:
        str_similarity = fuzz.ratio(string1.lower(), string2.lower())
    except Exception as e:
        print(f"Error calculating string similarity: {e}")
        return pd.Series([np.nan, string1, string2, np.nan, np.nan, np.nan, np.nan])
    
    # Initialize default values for rarity and probabilities
    rarity1 = rarity2 = prob1 = prob2 = np.nan
    
    # Attempt to calculate counts and likelihoods, handling division by zero
    try:
        count1 = string_counts.get(string1.lower(), 0)
        count2 = string_counts.get(string2.lower(), 0)
        
        # Calculate rarity scores (direct count scaled to 0-100)
        rarity1 = min((count1 / num_records) * 100, 100)
        rarity2 = min((count2 / num_records) * 100, 100)

        # Calculate probability scores (1 / count scaled to 0-100)
        prob1 = 100 if count1 == 0 else min((1 / count1) * 100, 100)
        prob2 = 100 if count2 == 0 else min((1 / count2) * 100, 100)
    except ZeroDivisionError:
        print("Division by zero encountered in likelihood calculation.")
        prob1 = prob2 = 0
    except Exception as e:
        print(f"Error during likelihood calculation: {e}")
        prob1 = prob2 = np.nan
    
    return pd.Series([str_similarity, string1, string2, rarity1, rarity2, prob1, prob2])