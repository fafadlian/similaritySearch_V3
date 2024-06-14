import math
from fuzzywuzzy import fuzz
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import jaccard_score
import numpy as np
import pandas as pd


def haversine(lon1, lat1, lon2, lat2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # convert decimal degrees to radians 
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers. Use 3956 for miles. Determines return value units.
    return c * r

def location_similarity_score(lon1, lat1, lon2, lat2, max_distance):
    """
    Calculate the similarity score based on the distance between two locations.
    
    Args:
    lon1, lat1, lon2, lat2 (float): Longitude and latitude of the two locations.
    max_distance (float): Maximum distance for normalization.
    
    Returns:
    pd.Series: Similarity score and exponential score.
    """
    if lon1 is None or lat1 is None or lon2 is None or lat2 is None:
        return pd.Series([np.nan, np.nan])
    
    try:
        distance = haversine(float(lon1), float(lat1), float(lon2), float(lat2))
    except (ValueError, TypeError):
        return pd.Series([np.nan, np.nan])

    similarity_score = max(0, (max_distance - distance) / max_distance)
    exp_score = math.exp(-distance / max_distance)
    
    return pd.Series([similarity_score, exp_score])

def address_str_similarity_score(string1, string2):
    if string1 is None or string2 is None:
        return pd.Series([np.nan, np.nan])
    
    if pd.isnull(string1) or pd.isnull(string2):
        return pd.Series([np.nan, np.nan])

    # Preprocess the strings
    string1 = string1.lower()
    string2 = string2.lower()

    # Check for empty strings after preprocessing
    if not string1.strip() or not string2.strip():
        return pd.Series([np.nan, np.nan])

    # FuzzyWuzzy similarity
    str_similarity = fuzz.ratio(string1, string2)
    
    # Vectorize the input strings for n-gram analysis
    vectorizer2 = CountVectorizer(analyzer='char', ngram_range=(3, 3))
    try:
        X = vectorizer2.fit_transform([string1, string2]).toarray()
        
        # Calculate Jaccard similarity based on the n-gram presence/absence
        intersection = np.logical_and(X[0], X[1]).sum()
        union = np.logical_or(X[0], X[1]).sum()
        jcd_score = intersection / union if union != 0 else 0
    except ValueError as e:
        if str(e) == "empty vocabulary; perhaps the documents only contain stop words":
            jcd_score = np.nan
        else:
            raise

    return pd.Series([str_similarity, jcd_score])

def location_matching(location1, location2):
    if isinstance(location1, pd.Series):
        return np.nan
    if isinstance(location2, pd.Series):
        return np.nan
    if pd.isnull(location1) or pd.isnull(location2):
        return np.nan
    return 1 if location1 == location2 else 0
