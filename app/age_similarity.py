from datetime import datetime
import pandas as pd
import numpy as np

def calculate_age(dob):
    """Calculate age from DOB."""
    if not dob:
        return np.nan

    try:
        dob = datetime.strptime(dob, "%Y-%m-%d")
    except ValueError:
        return np.nan 

    today = datetime.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age

def age_similarity_score(query_dob, dob):
    """Calculate a normalized similarity score for age."""
    if not query_dob or not dob:
        return np.nan
    
    query_age = calculate_age(query_dob)
    actual_age = calculate_age(dob)

    if np.isnan(query_age) or np.isnan(actual_age):
        return 0
    
    age_difference = abs(query_age - actual_age)

    # Use logarithmic scale for age similarity
    if age_difference == 0:
        return 100

    max_age = max(actual_age, query_age)
    min_age = min(actual_age, query_age)
    log_age_diff = np.log(max_age / min_age)

    # Scale log_age_diff to a 0-100 score
    score = max(0, 100 - (log_age_diff * 100))

    return score

# Example Usage
# dob_example = datetime(2000, 1, 1)  # Example DOB
# query_age =  12 # Example query age

# similarity_score = age_similarity_score(query_age, dob_example)
# print(f"Age similarity score: {similarity_score:.2f}")