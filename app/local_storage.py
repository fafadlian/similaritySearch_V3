import os
import json
import logging

# Set the base path for local storage
STORAGE_PATH = os.getenv('STORAGE_PATH', 'local_storage')

def upload_to_local_storage(file_name, data, is_json=True):
    try:
        # Create a folder with the name of the file (without extension)
        folder_name = os.path.join(STORAGE_PATH, file_name)
        os.makedirs(folder_name, exist_ok=True)  # Create folder if it doesn't exist
        
        # Define the full path for the file (add .json extension if is_json)
        file_path = os.path.join(folder_name, f"{file_name}.json" if is_json else file_name)
        
        # Save data as JSON or plain text
        with open(file_path, 'w' if is_json else 'wb') as file:
            if is_json:
                json.dump(data, file)
            else:
                file.write(data)
        
        logging.info(f"Uploaded {file_name} to local storage in folder {folder_name}.")
    except Exception as e:
        logging.error(f"Error uploading {file_name} to local storage: {str(e)}")

def upload_to_local_storage_txt(file_name, data):
    upload_to_local_storage(file_name, data, is_json=False)

def fetch_combined_data(task_id):
    try:
        # Construct the full path to the task's JSON file
        folder_path = os.path.join(STORAGE_PATH, f"task_{task_id}")
        file_path = os.path.join(folder_path, f"{task_id}.json")
        
        # Check if the file exists
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
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
