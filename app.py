"""
file: app.py
FIXED VERSION: Includes Logging and Error Handling
"""

import os
import csv
import logging # <--- Added logging
import tempfile
import googlemaps
import pandas as pd
from flask import Flask, request, send_file, render_template, abort

# 1. Setup Logging so you can see errors in Render Dashboard
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    logger.error("GOOGLE_API_KEY not set!")
    raise RuntimeError("Missing GOOGLE_API_KEY environment variable")

gmaps = googlemaps.Client(key=API_KEY)

def get_reviews(school_name, school_address):
    """Fetch reviews safely."""
    try:
        # Log what we are doing so we can track progress
        logger.info(f"Fetching: {school_name}...") 
        
        geocode_result = gmaps.geocode(school_address)

        if not geocode_result:
            logger.warning(f"Address not found for: {school_name}")
            return []

        place_id = geocode_result[0]["place_id"]
        place_details = gmaps.place(place_id=place_id)

        return place_details.get("result", {}).get("reviews", [])
    
    except Exception as e:
        # If Google API fails, log it but don't crash the whole app
        logger.error(f"Error fetching {school_name}: {e}")
        return []

@app.route("/")
def upload_page():
    return render_template("upload.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            return "No file part", 400

        file = request.files["file"]

        if file.filename == "":
            return "No selected file", 400

        if not file.filename.endswith(".csv"):
            return "File must be a .csv", 400

        # Read CSV
        try:
            schools = pd.read_csv(file)
            # Normalize headers: strip spaces to avoid "Name " vs "Name" errors
            schools.columns = schools.columns.str.strip()
        except Exception as e:
            logger.error(f"CSV Read Error: {e}")
            return f"Error reading CSV file: {str(e)}", 400

        reviews_output = []
        
        # Check if required columns exist
        required_cols = ["ID", "Name", "Address"]
        if not all(col in schools.columns for col in required_cols):
             return f"CSV missing required columns. Found: {list(schools.columns)}", 400

        # Loop through rows
        for index, row in schools.iterrows():
            school_name = row.get("Name", "")
            school_address = row.get("Address", "")
            school_id = row.get("ID", "")

            # If data is missing in a row, skip it
            if pd.isna(school_name) or pd.isna(school_address):
                continue

            reviews = get_reviews(str(school_name), str(school_address))

            for review in reviews:
                reviews_output.append({
                    "ID": school_id,
                    "Review": review.get("text", ""),
                    "Rating": review.get("rating", ""),
                })

        # Save to temp file
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        output_path = temp.name
        
        # Save output
        pd.DataFrame(reviews_output).to_csv(output_path, index=False)
        temp.close()

        logger.info("Processing complete. Sending file.")
        return send_file(output_path, as_attachment=True, download_name="reviews_output.csv")

    except Exception as e:
        # THIS IS THE KEY: Log the specific error to Render
        logger.error(f"CRITICAL SERVER ERROR: {e}", exc_info=True)
        return f"Internal Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)