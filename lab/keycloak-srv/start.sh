SCRIPT_DIR="$(realpath "$(dirname "$0")")"
# Run the FastAPI app using Uvicorn, specifying the app directory
uvicorn main:app --reload --app-dir "$SCRIPT_DIR"
