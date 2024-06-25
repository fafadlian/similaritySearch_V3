import os
import requests
import json
import shutil
from datetime import datetime
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.azure_blob_storage import upload_to_blob_storage
from app.token_manager import TokenManager
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

import time

    
def check_response(api_url, headers, params):
    response = requests.get(api_url, headers=headers, params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
    return response.status_code



async def fetch_page(session, api_url, headers, params, page):
    try:
        token_manager = TokenManager()
        headers['Authorization'] = f'Bearer {token_manager.get_token()}'
        async with session.get(f"{api_url}/page/{page}", headers=headers, params=params) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 401:
                logging.warning(f"Token expired on page {page}. Re-authenticating...")
                new_token = token_manager._reauthenticate()
                if new_token:
                    headers['Authorization'] = f'Bearer {new_token}'
                    return await fetch_page(session, api_url, headers, params, page)  # Retry after refreshing the token
                else:
                    logging.error("Token refresh failed")
                    return None
            else:
                logging.error(f"Error fetching page {page}: {await response.text()}")
                return None
    except Exception as e:
        logging.error(f"Exception on page {page}: {str(e)}")
        return None

async def fetch_initial_page(api_url, headers, params):
    async with aiohttp.ClientSession() as session:
        token_manager = TokenManager()
        headers['Authorization'] = f'Bearer {token_manager.get_token()}'
        initial_response = await session.get(f"{api_url}/page/0", headers=headers, params=params)
        if initial_response.status != 200:
            logging.error(f"Failed to fetch initial page: {await initial_response.text()}")
            if initial_response.status == 401:
                new_token = token_manager._reauthenticate()
                if new_token:
                    headers['Authorization'] = f'Bearer {new_token}'
                    initial_response = await session.get(f"{api_url}/page/0", headers=headers, params=params)
                    if initial_response.status != 200:
                        logging.error(f"Failed to fetch initial page after re-authentication: {await initial_response.text()}")
                        return None
                    else:
                        return await initial_response.json()
            return None
        return await initial_response.json()

async def fetch_all_pages(api_url, access_token, params):
    headers = {'Authorization': f'Bearer {access_token}'}

    # Get the total number of pages
    initial_data = await fetch_initial_page(api_url, headers, params)
    if initial_data is None:
        logging.error("Failed to fetch initial data even after re-authentication.")
        return None, 0

    total_pages = initial_data.get('totalPages', 1)
    logging.info(f"Total pages: {total_pages}")

    # Fetch all pages asynchronously
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_page(session, api_url, headers, params, page) for page in range(total_pages)]
        all_data = await asyncio.gather(*tasks)

    # Filter out None results (in case of failed fetches)
    all_data = [data for data in all_data if data is not None]
    combined_data = []
    for page_data in all_data:
        if 'listContent' in page_data:
            combined_data.extend(page_data['listContent'])  # Extract 'listContent' data

    return combined_data if combined_data else None, total_pages


async def fetch_all_pnr_data(flight_ids, directory, access_token):
    async with aiohttp.ClientSession() as session:
        tasks = []
        combined_data = []

        for flight_id in flight_ids:
            task = asyncio.create_task(fetch_pnr_data_to_azure(session, flight_id, combined_data))
            tasks.append(task)

        await asyncio.gather(*tasks)
        # Combine all the JSON data into one JSON object or list
        combined_json = json.dumps(combined_data)
        blob_name = f"{directory}/combined_pnr_data.json"
        upload_to_blob_storage(blob_name, combined_json.encode('utf-8'))
        logging.info(f"Uploaded combined JSON data to Azure Blob Storage as {blob_name}")

async def fetch_pnr_data_to_azure(session, flight_id, combined_data):
    api_url = f'https://tenacity-rmt.eurodyn.com/api/dataset/flight/{flight_id}'
    token_manager = TokenManager()
    headers = {'Authorization': f'Bearer {token_manager.get_token()}'}
    
    try:
        async with session.get(api_url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                combined_data.append(data)
                logging.info(f"Fetched JSON data for flight ID {flight_id}")
            elif response.status == 401:
                logging.warning(f"Token expired while fetching flight ID {flight_id}. Re-authenticating...")
                new_token = token_manager._reauthenticate()
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
