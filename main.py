# file: main.py

import csv
import googlemaps
from typing import List, Dict, Any


API_KEY = "AIzaSyChg2NPOgWeUw2ztIg9M_z59baKgJWTY7A"  # Replace with your actual key
gmaps = googlemaps.Client(key=API_KEY)


def get_reviews(school_name: str, school_address: str) -> List[Dict[str, Any]]:
    """Fetch reviews for a school using Google Maps Places API."""
    geocode_result = gmaps.geocode(school_address)

    if not geocode_result:
        print(f"No results found for {school_name} at {school_address}")
        return []

    place_id = geocode_result[0]["place_id"]
    place_details = gmaps.place(place_id=place_id)

    return place_details.get("result", {}).get("reviews", [])


def read_schools_and_get_reviews(csv_file: str) -> List[Dict[str, Any]]:
    """Read schools from CSV and return each review with its school ID."""
    reviews_output: List[Dict[str, Any]] = []

    with open(csv_file, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            school_id = row["ID"]
            school_name = row["Name"]
            school_address = row["Address"]

            print(f"Fetching reviews for {school_name}...")

            reviews = get_reviews(school_name, school_address)

            for review in reviews:
                reviews_output.append({
                    "ID": school_id,
                    "Review": review.get("text", ""),
                    "Rating": review.get("rating", "")
                })

    return reviews_output


def main() -> None:
    """Main execution point."""
    csv_file = "schools.csv"

    reviews = read_schools_and_get_reviews(csv_file)

    print("\nOutput Reviews:")
    for review in reviews:
        print(
            f"ID: {review['ID']} - Review: {review['Review']} "
            f"(Rating: {review['Rating']})"
        )


if __name__ == "__main__":
    main()
