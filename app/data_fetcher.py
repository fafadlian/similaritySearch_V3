import os
import requests
import json
import shutil
from datetime import datetime
import asyncio
import aiohttp
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

async def reauthenticate(session):
    api_url = 'https://tenacity-rmt.eurodyn.com/api/user/auth/token'
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD")
    data = {'username': username, 'password': password}

    async with session.post(api_url, json=data) as response:
        if response.status == 200:
            tokens = await response.json()
            os.environ["ACCESS_TOKEN"] = tokens["accessToken"]
            os.environ["REFRESH_TOKEN"] = tokens["refreshToken"]
            return tokens["accessToken"]
        else:
            logging.error(f"Failed to re-authenticate: {response.status} - {await response.text()}")
            return None


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

async def fetch_all_pnr_data(flight_ids, directory, access_token):
    async with aiohttp.ClientSession() as session:
        tasks = []
        combined_data = []

        for flight_id in flight_ids:
            task = asyncio.create_task(fetch_pnr_data_from_azure(session, flight_id, access_token, combined_data))
            tasks.append(task)

        await asyncio.gather(*tasks)
        # Combine all the JSON data into one JSON object or list
        combined_json = json.dumps(combined_data)
        blob_name = f"{directory}/combined_pnr_data.json"
        upload_to_blob_storage(blob_name, combined_json.encode('utf-8'))
        logging.info(f"Uploaded combined JSON data to Azure Blob Storage as {blob_name}")

async def fetch_pnr_data_from_azure(session, flight_id, access_token, combined_data):
    api_url = f'https://tenacity-rmt.eurodyn.com/api/dataset/flight/{flight_id}'
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        async with session.get(api_url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                combined_data.append(data)
                logging.info(f"Fetched JSON data for flight ID {flight_id}")
            elif response.status == 401:
                logging.warning(f"Token expired while fetching flight ID {flight_id}. Re-authenticating...")
                new_token = await reauthenticate(session)
                if new_token:
                    # Retry the request with the new token
                    headers = {'Authorization': f'Bearer {new_token}'}
                    async with session.get(api_url, headers=headers) as retry_response:
                        if retry_response.status == 200:
                            data = await retry_response.json()
                            combined_data.append(data)
                            logging.info(f"Fetched JSON data for flight ID {flight_id} after re-authentication")
                        else:
                            logging.warning(f"Failed to retrieve JSON data for flight ID {flight_id} after re-authentication: {await retry_response.text()}")
                else:
                    logging.error(f"Re-authentication failed for flight ID {flight_id}")
            else:
                logging.warning(f"Failed to retrieve JSON data for flight ID {flight_id}: {await response.text()}")
    except Exception as e:
        logging.error(f"Error fetching PNR data for flight ID {flight_id}: {str(e)}")

