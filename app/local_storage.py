import os
import json
import logging

# Set the base path for local storage
STORAGE_PATH = os.getenv('STORAGE_PATH', 'local_storage')

def upload_to_local_storage(file_name, data, is_json=True):
    try:
        file_path = os.path.join(STORAGE_PATH, file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)  # Create directories if they don't exist
        
        # Save data as JSON or plain text
        with open(file_path, 'w' if is_json else 'wb') as file:
            if is_json:
                json.dump(data, file)
            else:
                file.write(data)
        logging.info(f"Uploaded {file_name} to local storage.")
    except Exception as e:
        logging.error(f"Error uploading {file_name} to local storage: {str(e)}")

def upload_to_local_storage_txt(file_name, data):
    upload_to_local_storage(file_name, data, is_json=False)

def fetch_combined_data(file_path):
    try:
        full_path = os.path.join(STORAGE_PATH, file_path)
        if os.path.exists(full_path):
            with open(full_path, 'r') as file:
                raw_data = json.load(file)
                # If raw_data is a stringified JSON, parse it again
                if isinstance(raw_data, str):
                    return json.loads(raw_data)
                return raw_data
        else:
            raise FileNotFoundError(f"The file {file_path} does not exist in local storage.")
    except Exception as e:
        logging.error(f"Error fetching combined data from {file_path}: {str(e)}")


def download_from_local_storage(file_name):
    try:
        file_path = os.path.join(STORAGE_PATH, file_name)
        if os.path.exists(file_path):
            with open(file_path, 'rb') as file:
                return file.read()
        else:
            raise FileNotFoundError(f"The file {file_name} does not exist in local storage.")
    except Exception as e:
        logging.error(f"Error downloading {file_name} from local storage: {str(e)}")

def delete_from_local_storage(file_name):
    try:
        file_path = os.path.join(STORAGE_PATH, file_name)
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info(f"Deleted {file_name} from local storage.")
        else:
            raise FileNotFoundError(f"The file {file_name} does not exist in local storage.")
    except Exception as e:
        logging.error(f"Error deleting {file_name} from local storage: {str(e)}")

def delete_all_files_in_directory(directory):
    try:
        directory_path = os.path.join(STORAGE_PATH, directory)
        if os.path.exists(directory_path):
            for file_name in os.listdir(directory_path):
                file_path = os.path.join(directory_path, file_name)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            logging.info(f"Deleted all files in {directory} from local storage.")
        else:
            logging.info(f"Directory {directory} does not exist in local storage.")
    except Exception as e:
        logging.error(f"Error deleting all files in directory {directory}: {str(e)}")


def list_files_in_directory(directory):
    """
    Lists all files in the given directory.
    Returns a list of file names.
    """
    try:
        return os.listdir(directory)
    except FileNotFoundError as e:
        print(f"Directory not found: {e}")
        return []
