import os
import requests
import json
import shutil
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.azure_blob_storage import upload_to_blob_storage, delete_from_blob_storage, download_from_blob_storage, delete_all_files_in_directory
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

load_dotenv('environment.env')

def delete_all_files_in_directory(directory):
    if os.path.exists(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")

def recreate_directory(directory):
    if os.path.exists(directory):
        shutil.rmtree(directory)
    os.makedirs(directory)

def authenticate():
    api_url = 'https://tenacity-rmt.eurodyn.com/api/user/auth/token'
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")

    # headers = {
    #     'Content-Type': 'application/json',
    # }
    data = {
        'username': username,
        'password': password
    }
    response = requests.post(api_url, json=data)
    
    if response.status_code == 200:
        tokens = response.json()
        os.environ["ACCESS_TOKEN"] = tokens["accessToken"]
        os.environ["REFRESH_TOKEN"] = tokens["refreshToken"]
        return True
    else:
        print(f"Failed to authenticate: {response.status_code} - {response.text}")
        logging.error(f"Failed to authenticate: {response.status_code} - {response.text}")
        return False
    
def check_response(api_url, headers, params):
    response = requests.get(api_url, headers=headers, params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
    return response.status_code

def fetch_pnr_data(api_url, access_token, params):
    headers = {'Authorization': f'Bearer {access_token}'}
    all_data = []
    page = 0
    total_pages = 1  # Initialize with 1 to enter the loop

    try:
        while page < total_pages:
            response = requests.get(f"{api_url}/page/{page}", headers=headers, params=params)
            print(f"Status Code: {response.status_code} for page {page}")
            if response.status_code == 200:
                page_data = response.json()
                if 'listContent' in page_data:
                    all_data.extend(page_data['listContent'])  # Extract 'listContent' data
                if page == 0:  # Get total pages from the first response
                    total_pages = page_data.get('totalPages', 1)
                    print(f"Total pages: {total_pages}")
                page += 1
            elif response.status_code == 401:
                # Handle token expiration
                print(f"Error fetching page {page}: {response.text}")
                logging.warning(f"Token expired. Refreshing token...")
                if authenticate():
                # Retry fetching data with new token
                    access_token = os.getenv("ACCESS_TOKEN")
                    headers['Authorization'] = f'Bearer {access_token}'
                    continue  # Retry the current page after refreshing the token
                else:
                    logging.error("Token refresh failed")
                    break  # Exit loop if token refresh failed
            else:
                print(f"Error fetching page {page}: {response.text}")
                break  # Exit the loop on error

        return all_data if all_data else None, total_pages

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as err:
        print(f"Other error occurred: {err}")
    return None, 0
    


# def save_xml_data_for_flight_id(flight_id, directory):
#     api_url = 'https://tenacity-rmt.eurodyn.com/api/pnr-notification/xml/by-id'
#     access_token = os.getenv("ACCESS_TOKEN")
#     headers = {'Authorization': f'Bearer {access_token}'}
#     params = {'id': flight_id}
    
#     try:
#         response = requests.get(api_url, headers=headers, params=params)
#         logging.info(f"response code: {response.status_code}")
        
#         if response.status_code == 200:
#             # if not os.path.exists(directory):
#             #     os.makedirs(directory)
#             #     logging.info(f"Directory {directory} created.")
                
#             file_path = os.path.join(directory, f'flight_id_{flight_id}.xml')
#             blob_name = f"{directory}/flight_id_{flight_id}.xml"
#             logging.info(f"response content: {response.content}")
#             # with open(file_path, 'wb') as file:
#             #     file.write(response.content)
            
#             logging.info(f"Saved XML data for flight ID {flight_id} to {file_path}")

#             upload_to_blob_storage(blob_name, response.content)
                
#             logging.info(f"Uploaded XML data for flight ID {flight_id} to Azure Blob Storage as {blob_name}")
#         else:
#             logging.warning(f"Failed to retrieve XML data for flight ID {flight_id}: {response.text}")
    
#     except Exception as e:
#         logging.error(f"Error processing task {directory}: {str(e)}")

def save_json_data_for_flight_id(flight_id, directory):
    api_url = f'https://tenacity-rmt.eurodyn.com/api/dataset/flight/{flight_id}'
    access_token = os.getenv("ACCESS_TOKEN")
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        response = requests.get(api_url, headers=headers)
        logging.info(f"response code: {response.status_code}")
        
        if response.status_code == 200:
            file_path = os.path.join(directory, f'flight_id_{flight_id}.json')
            blob_name = f"{directory}/flight_id_{flight_id}.json"
            logging.info(f"response content: {response.content}")
            
            logging.info(f"Saved JSON data for flight ID {flight_id} to {file_path}")

            upload_to_blob_storage(blob_name, response.content)
                
            logging.info(f"Uploaded JSON data for flight ID {flight_id} to Azure Blob Storage as {blob_name}")
        else:
            logging.warning(f"Failed to retrieve JSON data for flight ID {flight_id}: {response.text}")
    
    except Exception as e:
        logging.error(f"Error processing task {directory}: {str(e)}")
