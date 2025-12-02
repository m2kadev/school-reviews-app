"""
file: app.py
Production-ready Flask app to upload a CSV, fetch Google Reviews,
and return a processed CSV file.
"""

import csv
import tempfile
import googlemaps
import pandas as pd
from flask import Flask, request, send_file, render_template, abort
from typing import List, Dict, Any

app = Flask(__name__)

# IMPORTANT: Set your API key as an environment variable on Render.com
# Settings → Environment → Add Environment Variable → GOOGLE_API_KEY
import os
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY environment variable")

gmaps = googlemaps.Client(key=API_KEY)


def get_reviews(school_name: str, school_address: str) -> List[Dict[str, Any]]:
    """Fetch reviews for a school using Google Maps."""
    geocode_result = gmaps.geocode(school_address)

    if not geocode_result:
        return []

    place_id = geocode_result[0]["place_id"]
    place_details = gmaps.place(place_id=place_id)

    return place_details.get("result", {}).get("reviews", [])


@app.route("/")
def upload_page():
    return render_template("upload.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        abort(400, "No file provided")

    file = request.files["file"]

    if file.filename == "":
        abort(400, "Empty file name")

    if not file.filename.endswith(".csv"):
        abort(400, "Invalid file type. Must be CSV")

    # Read CSV into DataFrame
    schools = pd.read_csv(file)
    reviews_output = []

    for _, row in schools.iterrows():
        school_id = row.get("ID", "")
        school_name = row.get("Name", "")
        school_address = row.get("Address", "")

        reviews = get_reviews(school_name, school_address)

        for review in reviews:
            reviews_output.append({
                "ID": school_id,
                "Review": review.get("text", ""),
                "Rating": review.get("rating", ""),
            })

    # Make a temp output file
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    output_path = temp.name

    pd.DataFrame(reviews_output).to_csv(output_path, index=False)
    temp.close()

    return send_file(output_path, as_attachment=True, download_name="reviews_output.csv")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
