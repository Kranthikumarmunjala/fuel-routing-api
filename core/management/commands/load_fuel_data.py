# import pandas as pd
# from django.core.management.base import BaseCommand
# from core.models import FuelStation

# class Command(BaseCommand):
#     help = 'Load ALL 8000 records FAST'

#     def handle(self, *args, **kwargs):
#         try:
#             print("Reading CSV...")
#             df = pd.read_csv('fuel-prices-for-be-assessment.csv')
            
#             print("Clearing old data...")
#             FuelStation.objects.all().delete()

#             print("Preparing 8000 records...")
#             stations = [
#                 FuelStation(
#                     opis_id=row['OPIS Truckstop ID'],
#                     name=row['Truckstop Name'],
#                     address=row['Address'],
#                     city=row['City'],
#                     state=row['State'],
#                     rack_id=row['Rack ID'],
#                     retail_price=row['Retail Price'],
#                     latitude=None,
#                     longitude=None
#                 )
#                 for index, row in df.iterrows()
#             ]

#             print("Saving to MySQL...")
#             FuelStation.objects.bulk_create(stations)
#             print("SUCCESS! 8000 records loaded.")

#         except Exception as e:
#             print(f"Error: {e}")







import pandas as pd
from django.core.management.base import BaseCommand
from core.models import FuelStation

class Command(BaseCommand):
    help = 'Load ALL 8000 records FAST and skip duplicates'

    def handle(self, *args, **kwargs):
        file_path = 'fuel-prices-for-be-assessment.csv'
        try:
            print("Reading CSV...")
            df = pd.read_csv(file_path)
            
            print("Clearing old data...")
            FuelStation.objects.all().delete()

            print("Preparing records...")
            stations_to_create = []
            seen_ids = set() # డూప్లికేట్లను కనిపెట్టడానికి

            for index, row in df.iterrows():
                opis_id = row['OPIS Truckstop ID']
                
                # ఒకవేళ ఐడి ఇప్పటికే ఉంటే దానిని స్కిప్ చేస్తుంది
                if opis_id in seen_ids:
                    continue
                seen_ids.add(opis_id)

                station = FuelStation(
                    opis_id=opis_id,
                    name=row['Truckstop Name'],
                    address=row['Address'],
                    city=row['City'],
                    state=row['State'],
                    rack_id=row['Rack ID'],
                    retail_price=row['Retail Price'],
                    latitude=None,
                    longitude=None
                )
                stations_to_create.append(station)

            print("Saving to MySQL (Bulk Insert)...")
            FuelStation.objects.bulk_create(stations_to_create)
            print(f"SUCCESS! {len(stations_to_create)} records loaded.")

        except Exception as e:
            print(f"Error: {e}")