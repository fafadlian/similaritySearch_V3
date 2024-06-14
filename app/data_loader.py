import json
import os

def load_json_data(folder_name):
    data = []
    for filename in os.listdir(folder_name):
        if filename.endswith('.json'):
            with open(os.path.join(folder_name, filename), 'r') as file:
                data.extend(json.load(file))
    return data

# folder_name = 'jsonData'
# pnr_data = load_json_data(folder_name)