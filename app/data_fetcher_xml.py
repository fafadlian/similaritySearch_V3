import asyncio
import aiohttp
import xml.etree.ElementTree as ET
import logging
from app.azure_blob_storage import upload_to_blob_storage_XML
from app.token_manager import TokenManager


async def fetch_all_pnr_data_XML(flight_ids, directory, access_token):
    async with aiohttp.ClientSession() as session:
        tasks = []
        combined_data = []

        for flight_id in flight_ids:
            task = asyncio.create_task(fetch_pnr_data_to_azure_XML(session, flight_id, combined_data))
            tasks.append(task)

        await asyncio.gather(*tasks)
        # Combine all the XML data into one XML object or list
        combined_xml = '<root>' + ''.join(combined_data) + '</root>'
        blob_name = f"{directory}/combined_pnr_data.xml"
        upload_to_blob_storage_XML(blob_name, combined_xml.encode('utf-8'))
        logging.info(f"Uploaded combined XML data to Azure Blob Storage as {blob_name}")

async def fetch_pnr_data_to_azure_XML(session, flight_id, combined_data):
    api_url = f'https://tenacity-rmt.eurodyn.com/api/dataset/flight/{flight_id}'
    token_manager = TokenManager()
    headers = {'Authorization': f'Bearer {token_manager.get_token()}'}

    try:
        async with session.get(api_url, headers=headers) as response:
            if response.status == 200:
                data = await response.text()
                combined_data.append(data)
                logging.info(f"Fetched XML data for flight ID {flight_id}")
            elif response.status == 401:
                logging.warning(f"Token expired while fetching flight ID {flight_id}. Re-authenticating...")
                new_token = token_manager._reauthenticate()
                if new_token:
                    # Retry the request with the new token
                    headers = {'Authorization': f'Bearer {new_token}'}
                    async with session.get(api_url, headers=headers) as retry_response:
                        if retry_response.status == 200:
                            data = await retry_response.text()
                            combined_data.append(data)
                            logging.info(f"Fetched XML data for flight ID {flight_id} after re-authentication")
                        else:
                            logging.warning(f"Failed to retrieve XML data for flight ID {flight_id} after re-authentication: {await retry_response.text()}")
                else:
                    logging.error(f"Re-authentication failed for flight ID {flight_id}")
            else:
                logging.warning(f"Failed to retrieve XML data for flight ID {flight_id}: {await response.text()}")
    except Exception as e:
        logging.error(f"Error fetching PNR data for flight ID {flight_id}: {str(e)}")
