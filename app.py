"""
file: app.py
Production-ready Flask app to upload a CSV, fetch Google Reviews,
and return a processed CSV file.
"""

import os
import logging
import tempfile
import googlemaps
import pandas as pd
from flask import Flask, request, send_file, render_template, abort

# 1. Setup Logging (This lets you see errors in Render logs)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 2. Setup Google Maps Client
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    # This logs the error before crashing
    logger.error("CRITICAL: Missing GOOGLE_API_KEY environment variable.")
    raise RuntimeError("Missing GOOGLE_API_KEY environment variable")

gmaps = googlemaps.Client(key=API_KEY)


def get_reviews(school_name, school_address):
    """Fetch reviews safely using Google Maps."""
    try:
        logger.info(f"Fetching reviews for: {school_name}")
        geocode_result = gmaps.geocode(school_address)

        if not geocode_result:
            logger.warning(f"No address found for: {school_name}")
            return []

        place_id = geocode_result[0]["place_id"]
        place_details = gmaps.place(place_id=place_id)

        return place_details.get("result", {}).get("reviews", [])
    
    except Exception as e:
        # If Google API fails for one school, log it but don't crash the whole app
        logger.error(f"Google API Error for {school_name}: {e}")
        return []


@app.route("/")
def upload_page():
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        # --- File Validation ---
        if "file" not in request.files:
            return "No file part", 400

        file = request.files["file"]

        if file.filename == "":
            return "No selected file", 400

        if not file.filename.endswith(".csv"):
            return "File must be a .csv", 400

        # --- CSV Reading & Normalization ---
        try:
            schools = pd.read_csv(file)
            
            # CRITICAL FIX: Convert headers to UPPERCASE and remove spaces
            # This makes "Name", "name", and "NAME" all become "NAME"
            schools.columns = schools.columns.str.strip().str.upper()
            
        except Exception as e:
            logger.error(f"CSV Read Error: {e}")
            return f"Error reading CSV file: {str(e)}", 400

        # --- Column Checking ---
        required_cols = ["ID", "NAME", "ADDRESS"]
        if not all(col in schools.columns for col in required_cols):
             missing = [col for col in required_cols if col not in schools.columns]
             return f"CSV missing required columns. Found: {list(schools.columns)}. Missing: {missing}", 400

        # --- Processing Rows ---
        reviews_output = []

        for index, row in schools.iterrows():
            school_name = row.get("NAME", "")
            school_address = row.get("ADDRESS", "")
            school_id = row.get("ID", "")

            # Skip empty rows
            if pd.isna(school_name) or pd.isna(school_address):
                continue

            reviews = get_reviews(str(school_name), str(school_address))

            for review in reviews:
                reviews_output.append({
                    "ID": school_id,
                    "Review": review.get("text", ""),
                    "Rating": review.get("rating", ""),
                })

        # --- Saving Output ---
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
        output_path = temp.name
        
        pd.DataFrame(reviews_output).to_csv(output_path, index=False)
        temp.close()

        logger.info("Processing complete. Sending file to user.")
        return send_file(output_path, as_attachment=True, download_name="reviews_output.csv")

    except Exception as e:
        # Catch-all for any other crashes (500 Errors)
        logger.error(f"CRITICAL SERVER ERROR: {e}", exc_info=True)
        return f"Internal Server Error: {str(e)}", 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)