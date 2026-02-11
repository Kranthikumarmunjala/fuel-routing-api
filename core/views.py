# core/views.py
import requests
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import FuelStation
from math import radians, cos, sin, asin, sqrt

class FuelRouteView(APIView):
    def post(self, request):
        start_location = request.data.get('start_location')
        finish_location = request.data.get('finish_location')

        if not start_location or not finish_location:
            return Response({"error": "Please provide start_location and finish_location"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. Geocode Start and End using ORS
        try:
            headers = {'Authorization': settings.ORS_API_KEY}
            
            # Geocode Start
            start_geo = requests.get(
                f"https://api.openrouteservice.org/geocode/search?text={start_location}", 
                headers=headers
            ).json()
            start_coords = start_geo['features'][0]['geometry']['coordinates'] # [lon, lat]

            # Geocode End
            end_geo = requests.get(
                f"https://api.openrouteservice.org/geocode/search?text={finish_location}", 
                headers=headers
            ).json()
            end_coords = end_geo['features'][0]['geometry']['coordinates'] # [lon, lat]

            # 2. Get Route from ORS
            body = {"coordinates": [start_coords, end_coords]}
            route_response = requests.post(
                "https://api.openrouteservice.org/v2/directions/driving-car/geojson",
                json=body,
                headers=headers
            ).json()
            
            # Extract Route Data
            feature = route_response['features'][0]
            geometry = feature['geometry'] # The map line
            total_distance_meters = feature['properties']['segments'][0]['distance']
            total_distance_miles = total_distance_meters * 0.000621371

            # 3. Fuel Logic
            MAX_RANGE = 500  # miles
            MPG = 10
            fuel_stops = []
            
            # To simulate driving, we analyze the route coordinates
            coordinates = geometry['coordinates'] # List of [lon, lat]
            current_range = MAX_RANGE
            distance_traveled = 0
            total_fuel_cost = 0

            # We need a helper to measure distance between two coords
            def haversine(lon1, lat1, lon2, lat2):
                # Convert decimal degrees to radians 
                lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                # Haversine formula 
                dlon = lon2 - lon1 
                dlat = lat2 - lat1 
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a)) 
                r = 3956 # Radius of earth in miles
                return c * r

            last_stop_coords = start_coords
            
            # Simple Greedy Algorithm:
            # We assume the route is a list of points. We iterate through them summing distance.
            # If distance > 450 (buffer), we look for a station near that point.
            
            segment_dist = 0
            
            # In a real heavy app, we would process this more precisely. 
            # For this assessment, we sample points along the route.
            
            current_segment_miles = 0
            
            for i in range(1, len(coordinates)):
                prev_pt = coordinates[i-1]
                curr_pt = coordinates[i]
                
                dist_step = haversine(prev_pt[0], prev_pt[1], curr_pt[0], curr_pt[1])
                current_segment_miles += dist_step
                
                # If we are getting close to empty (e.g., 450 miles driven since last fill)
                # OR if we are at the end and need to calculate final cost
                if current_segment_miles >= 450:
                    # Find cheapest gas station within 20 miles of current location
                    search_radius = 20
                    # Filter by a bounding box first for speed (approx 1 degree lat/lon)
                    candidates = FuelStation.objects.filter(
                        latitude__range=(curr_pt[1]-1, curr_pt[1]+1),
                        longitude__range=(curr_pt[0]-1, curr_pt[0]+1)
                    )
                    
                    best_station = None
                    min_price = float('inf')
                    
                    for station in candidates:
                        if station.latitude and station.longitude:
                            d = haversine(curr_pt[0], curr_pt[1], station.longitude, station.latitude)
                            if d <= search_radius:
                                if station.retail_price < min_price:
                                    min_price = station.retail_price
                                    best_station = station
                    
                    if best_station:
                        gallons_needed = current_segment_miles / MPG
                        cost = float(best_station.retail_price) * gallons_needed
                        total_fuel_cost += cost
                        
                        fuel_stops.append({
                            "station": best_station.name,
                            "city": best_station.city,
                            "state": best_station.state,
                            "price_per_gallon": float(best_station.retail_price),
                            "cost_for_leg": round(cost, 2),
                            "coordinates": [best_station.longitude, best_station.latitude]
                        })
                        
                        # Refuel
                        current_segment_miles = 0 # Reset range
                        last_stop_coords = [best_station.longitude, best_station.latitude]
            
            # Calculate final leg cost (if any distance remains)
            if current_segment_miles > 0:
                gallons_needed = current_segment_miles / MPG
                # Assume average price or price of last station for final calculation if no station needed
                # For accuracy, let's just use the national average or the last found price. 
                # Let's simple average the dataset if no stop was found, or use last.
                avg_price = 3.50 # Fallback
                if fuel_stops:
                    avg_price = fuel_stops[-1]['price_per_gallon']
                
                cost = avg_price * gallons_needed
                total_fuel_cost += cost

            response_data = {
                "route_map_geojson": geometry, # Frontend can plot this
                "total_distance_miles": round(total_distance_miles, 2),
                "total_fuel_cost": round(total_fuel_cost, 2),
                "fuel_stops": fuel_stops,
                "note": "Route calculated with 500 mile range limit and 10 MPG."
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)