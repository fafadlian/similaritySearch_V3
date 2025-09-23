import requests
import pandas as pd
import warnings
from itertools import combinations
from datetime import datetime


warnings.filterwarnings("ignore", category=UserWarning)

def normalize_dob(dob_str):
    if not dob_str:
        return None
    return dob_str[:10]  # keep only "YYYY-MM-DD"

API_URL = "http://localhost:443/combined_operation"

# --- Base payload ---
base_payload = {
    "arrival_date_from": "2019-02-01",
    "arrival_date_to": "2019-02-28",
    "flight_nbr": "",
    "firstname": "Rebecca",
    "surname": "Bautista",
    "dob": "1990-06-06",
    "iata_o": "ZRH",
    "iata_d": "ATH",
    "city_name": "",
    "address": "el paso, 216 patricia brook williamsfort, dc 98593",
    "sex": "F",
    "nationality": "USA",
    "nameThreshold": 20,
    "ageThreshold": 20,
    "locationThreshold": 20
}

base_minimum_payload = {
    "arrival_date_from": "2019-02-01",
    "arrival_date_to": "2019-02-28",
    "flight_nbr": "",
    "firstname": "Rebecca",
    "surname": "Bautista",
    "dob": "1990-06-06",
    "iata_o": "",
    "iata_d": "",
    "city_name": "",
    "address": "",
    "sex": "F",
    "nationality": "",
    "nameThreshold": 0,
    "ageThreshold": 0,
    "locationThreshold": 0
}

disturbed_payload = {
    "firstname": "Becky",
    "surname": "Baptiste",
    "dob": "1991-07-07",
    "iata_o": "CDG",
    "iata_d": "LHR",
    "sex": "M",
    "nationality": "GBR"
}

# --- Generate test cases ---

test_cases = []

# 1. Complete
test_cases.append(("Complete", base_payload.copy()))

# 2. Null one-by-one
for key in ["firstname", "surname", "dob", "iata_o", "iata_d", "address", "sex", "nationality"]:
    modified = base_payload.copy()
    modified[key] = ""
    test_cases.append((f"Null {key}", modified))

# 3. Modified 1 (address erased + one-by-one field modification)
modified_base = base_payload.copy()
modified_base["address"] = ""

mods = [
    ("Mod1 - Sex changed", {"sex": "F"}),
    ("Mod1 - Nationality removed", {"nationality": ""}),
    ("Mod1 - Firstname changed", {"firstname": "Becky"}),
    ("Mod1 - Firstname changed", {"firstname": "Becca"}),
    ("Mod1 - Firstname changed", {"firstname": "Rebeka"}),
    ("Mod1 - Surname changed", {"surname": "Bautista"}),
    ("Mod1 - Surname changed", {"surname": "Batista"}),
    ("Mod1 - Surname changed", {"surname": "Baptista"}),
    ("Mod1 - DOB changed", {"dob": "1989-01-01"}),
    ("Mod1 - DOB changed", {"dob": "1998-12-14"}),
    ("Mod1 - DOB changed", {"dob": "1980-06-09"}),
    ("Mod1 - IATA_O changed", {"iata_o": "FRA"}),
    ("Mod1 - IATA_D changed", {"iata_d": "CDG"}),
]

for name, mod in mods:
    test_cases.append((name, {**modified_base, **mod}))

# 4. Modified 2 (Sex = M, no nationality, extreme name and dob)
extreme_case = base_payload.copy()
extreme_case["sex"] = "M"
extreme_case["nationality"] = ""
extreme_case["firstname"] = "E"
extreme_case["surname"] = "Horress"
extreme_case["dob"] = "1930-01-01"
test_cases.append(("Mod2 - Extreme changes", extreme_case))

# 5. Modified 3 (Alter everything but extreme)
# modiefied_3_base = disturbed_payload.copy()
# mods_3 = [
#     ("Mod3 - Sex changed", {"sex": "F"}),
#     ("Mod3 - Nationality removed", {"nationality": "DEU"}),
#     ("Mod3 - Firstname changed", {"firstname": "Becky"}),
#     ("Mod3 - Firstname changed", {"firstname": "Becca"}),
#     ("Mod3 - Firstname changed", {"firstname": "Rebeka"}),
#     ("Mod3 - Surname changed", {"surname": "Bautista"}),
#     ("Mod3 - Surname changed", {"surname": "Batista"}),
#     ("Mod3 - Surname changed", {"surname": "Baptista"}),
#     ("Mod3 - DOB changed", {"dob": "1989-01-01"}),
#     ("Mod3 - DOB changed", {"dob": "1988-12-14"}),
#     ("Mod3 - DOB changed", {"dob": "1980-12-13"}),
#     ("Mod3 - IATA_O changed", {"iata_o": "LHR"}),
#     ("Mod3 - IATA_D changed", {"iata_d": "IST"}),
# ]

# for name, mod in mods_3:
#     test_cases.append((name, {**modiefied_3_base, **mod}))

    # --- Generate multi-field disturbance test cases (2, 3, 4 fields) ---
target_fields = ["firstname", "surname", "dob", "iata_o", "iata_d", "sex", "nationality"]
for k in [2, 3, 4]:
    for combo in combinations(target_fields, k):
        mod = base_minimum_payload.copy()
        for field in combo:
            mod[field] = disturbed_payload[field]
        test_name = f"MultiMod - {' + '.join(combo)}"
        test_cases.append((test_name, mod))


# --- Run tests and collect top 5 results ---
rows = []

for test_idx, (test_name, payload) in enumerate(test_cases, 1):
    try:
        response = requests.post(API_URL, json=payload, verify=False)
        res = response.json()
        results = res.get("data", [])[:50]

        if results:
            for rank, result in enumerate(results, 1):
                is_correct_match = (
                    result.get("Firstname") == base_payload["firstname"] and
                    result.get("Surname") == base_payload["surname"] and
                    normalize_dob(result.get("DOB")) == normalize_dob(base_payload["dob"]) and
                    result.get("Sex") == base_payload["sex"] and
                    result.get("Nationality") == base_payload["nationality"]
                )

                rows.append({
                    "Test Case No": test_idx,
                    "Test Case": test_name,
                    "Query Firstname": payload["firstname"],
                    "Query Surname": payload["surname"],
                    "Query DOB": payload["dob"],
                    "Query Sex": payload["sex"],
                    "Query Nationality": payload["nationality"],
                    "Query Address": payload["address"],
                    "Query IATA_O": payload["iata_o"],
                    "Query IATA_D": payload["iata_d"],
                    "Rank": rank,
                    "Is Correct Match": is_correct_match,
                    "Matched Firstname": result.get("Firstname", ""),
                    "Matched Surname": result.get("Surname", ""),
                    "Matched DOB": result.get("DOB", ""),
                    "FAISS Distance": result.get("FAISS Distance", None),
                    "Confidence Level": result.get("Confidence Level", None),
                    "Compound Similarity Score": result.get("Compound Similarity Score", None),
                    "FNSimilarity": result.get("FNSimilarity", None),
                    "SNSimilarity": result.get("SNSimilarity", None),
                    "DOBSimilarity": result.get("DOBSimilarity", None),
                    "AgeSimilarity": result.get("AgeSimilarity", None)
                })
        else:
            rows.append({
                "Test Case No": test_idx,
                "Test Case": test_name,
                "Query Firstname": payload["firstname"],
                "Query Surname": payload["surname"],
                "Query DOB": payload["dob"],
                "Query Sex": payload["sex"],
                "Query Nationality": payload["nationality"],
                "Query Address": payload["address"],
                "Query IATA_O": payload["iata_o"],
                "Query IATA_D": payload["iata_d"],
                "Rank": None,
                "Is Correct Match": False,
                "Matched Firstname": None,
                "Matched Surname": None,
                "Matched DOB": None,
                "FAISS Distance": None,
                "Confidence Level": None,
                "Compound Similarity Score": None,
                "FNSimilarity": None,
                "SNSimilarity": None,
                "DOBSimilarity": None,
                "AgeSimilarity": None
            })

    except Exception as e:
        rows.append({
            "Test Case No": test_idx,
            "Test Case": test_name,
            "Query Firstname": payload["firstname"],
            "Query Surname": payload["surname"],
            "Query DOB": payload["dob"],
            "Query Sex": payload["sex"],
            "Query Nationality": payload["nationality"],
            "Query Address": payload["address"],
            "Query IATA_O": payload["iata_o"],
            "Query IATA_D": payload["iata_d"],
            "Rank": None,
            "Is Correct Match": False,
            "Matched Firstname": "ERROR",
            "Matched Surname": None,
            "Matched DOB": None,
            "FAISS Distance": None,
            "Confidence Level": str(e),
            "Compound Similarity Score": None,
            "FNSimilarity": None,
            "SNSimilarity": None,
            "DOBSimilarity": None,
            "AgeSimilarity": None
        })

# --- Output to CSV ---
df = pd.DataFrame(rows)
df.to_csv("api_similarity_test_results.csv", index=False)
