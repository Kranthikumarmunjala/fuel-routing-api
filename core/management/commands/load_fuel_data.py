import pandas as pd
from django.core.management.base import BaseCommand
from core.models import FuelStation
from geopy.geocoders import ArcGIS
import time

class Command(BaseCommand):
    help = 'Load fuel prices from CSV and geocode them safely'

    def handle(self, *args, **kwargs):
        file_path = 'fuel-prices-for-be-assessment.csv'
        
        try:
            # Read the CSV
            df = pd.read_csv(file_path)
            print(f"Found {len(df)} records in CSV.")

            # Switch to ArcGIS (More reliable than Nominatim for this)
            geolocator = ArcGIS(user_agent="fuel_project_student_v2")

            count = 0
            success_count = 0
            
            # CLEAR OLD DATA (Optional: keeps database clean)
            FuelStation.objects.all().delete()
            print("Cleared old data from database.")

            for index, row in df.iterrows():
                # --- DEMO LIMIT ---
                # Remove these 2 lines if you want to wait 3 hours for all 8000 lines
                if count >= 60: 
                    print("Limit reached (60 stations) for Video Demo. Stopping import.")
                    break
                # ------------------

                try:
                    # Create address string
                    full_address = f"{row['Address']}, {row['City']}, {row['State']}, USA"
                    
                    # Try to geocode
                    location = None
                    try:
                        location = geolocator.geocode(full_address, timeout=10)
                    except Exception as geo_error:
                        print(f"   > Could not map: {full_address} (Error: {geo_error})")

                    lat = location.latitude if location else None
                    lng = location.longitude if location else None

                    # Save to DB
                    FuelStation.objects.create(
                        opis_id=row['OPIS Truckstop ID'],
                        name=row['Truckstop Name'],
                        address=row['Address'],
                        city=row['City'],
                        state=row['State'],
                        rack_id=row['Rack ID'],
                        retail_price=row['Retail Price'],
                        latitude=lat,
                        longitude=lng
                    )
                    
                    if lat:
                        success_count += 1
                        print(f"[{count}] Imported: {row['Truckstop Name']} ({lat}, {lng})")
                    else:
                        print(f"[{count}] Imported (No Location): {row['Truckstop Name']}")

                    count += 1
                    
                    # Tiny pause to be nice to the API
                    time.sleep(0.5)

                except Exception as e:
                    print(f"Error on row {index}: {e}")

            print(f"Finished! Successfully imported {count} stations ({success_count} with GPS).")

        except FileNotFoundError:
            print("CSV file not found. Please place 'fuel-prices-for-be-assessment.csv' in the root directory.")