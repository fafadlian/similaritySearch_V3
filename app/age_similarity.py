from datetime import datetime
import pandas as pd
import numpy as np
import logging

def calculate_age(dob):
    """Calculate age from DOB, handling invalid inputs."""
    if not dob:
        return np.nan

    try:
        dob = datetime.strptime(dob, "%Y-%m-%d")
    except ValueError:
        logging.info("Invalid DOB format")
        return np.nan  # Invalid date format

    today = datetime.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    return age if age >= 0 else 0  # Ensure non-negative age

def age_similarity_score(query_dob, dob):
    """Calculate a normalized similarity score for age, safely handling division by zero."""
    if not query_dob or not dob:
        logging.info("Missing DOB for age similarity calculation")
        return 0
    
    query_age = calculate_age(query_dob)
    actual_age = calculate_age(dob)

    if np.isnan(query_age) or np.isnan(actual_age) or query_age == 0 or actual_age == 0:
        logging.info("Invalid DOB for age similarity calculation")
        return 0  # Invalid ages result in 0 similarity

    age_difference = abs(query_age - actual_age)

    # ✅ If the ages are identical, return max similarity
    if age_difference == 0:
        # logging.info("Identical ages for age similarity calculation")
        return 100

    max_age = max(actual_age, query_age)
    min_age = min(actual_age, query_age)

    # ✅ Prevent division by zero (if min_age is zero, return lowest similarity)
    if min_age == 0:
        logging.info("Zero age for age similarity calculation")
        return 0  

    log_age_diff = np.log(max_age / min_age)

    # ✅ Scale log_age_diff to a 0-100 score
    score = max(0, 100 - (log_age_diff * 100))

    # logging.info(f"Age similarity score: {score:.2f}")
    return score

# Example Usage
# dob_example = datetime(2000, 1, 1)  # Example DOB
# query_age =  12 # Example query age

# similarity_score = age_similarity_score(query_age, dob_example)
# print(f"Age similarity score: {similarity_score:.2f}")