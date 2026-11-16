import json
import os
import threading

class JSONUtils:
    _lock = threading.Lock()

    @staticmethod
    def save_json_to_file(payload, file_path):
        try:
            with JSONUtils._lock:
                # Ensure the directory exists
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                # Open the file in write mode ('w') and save the JSON payload
                with open(file_path, 'w') as json_file:
                    json.dump(payload, json_file, indent=4)

                print(f"JSON data successfully saved to {file_path}")
        except Exception as e:
            print(f"Failed to save JSON: {str(e)}")

    @staticmethod
    def delete_json_file(file_path):
        try:
            with JSONUtils._lock:
                # Check if the file exists
                if os.path.exists(file_path):
                    # Delete the file
                    os.remove(file_path)
                    print(f"File {file_path} successfully deleted.")
                else:
                    print(f"File {file_path} does not exist.")
        except Exception as e:
            print(f"Failed to delete the file: {str(e)}")

    @staticmethod
    def load_json_from_file(file_path):
        try:
            with JSONUtils._lock:
                # Open the file in read mode ('r') and load the JSON data
                with open(file_path, 'r') as json_file:
                    payload = json.load(json_file)

                print(f"JSON data successfully loaded from {file_path}")
                return payload
        except FileNotFoundError:
            print(f"File {file_path} not found.")
            return []
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {file_path}: {str(e)}")
            return None
        except Exception as e:
            print(f"Failed to load JSON: {str(e)}")
            return None
        
    @staticmethod
    def print_pretty_json(json_data):
        parsed_json_data = json.loads(json_data)
        pretty_json_data = json.dumps(parsed_json_data, indent=4)
        print(pretty_json_data)
    
    @staticmethod
    def print_pretty_obj(obj):
        pretty_json_data = json.dumps(obj, indent=4)
        print(pretty_json_data)


def print_red(str):
    print(f"\033[91m{str}\033[0m")

def print_exception(e):    
    print_red("ERROR INFORMATION:")
    
    # Print the exception's type and standard message, which always exist
    print(f"- Type: {type(e).__name__}")
    print(f"- Message: {e}")

    # Safely get HTTP attributes using getattr(object, attribute_name, default_value)
    status = getattr(e, 'status', 'N/A')
    reason = getattr(e, 'reason', 'N/A')
    body = getattr(e, 'body', None)  # Default to None if 'body' doesn't exist

    print(f"- HTTP status: {status}")
    print(f"- Reason: {reason}")
    print("- Body: -->>>")

    try:
        if body is not None:
            JSONUtils.print_pretty_json(body)
        else:
            print("(No body attribute or body is None)")
    except Exception as body_print_error:
        # Added this in case JSONUtils fails (e.g., body isn't JSON)
        print(f"(Could not print body details: {body_print_error})")
        print(f"Raw body: {body}") # Try to print the raw body as a fallback

    print("<<<--")
    print_red("-------------")
