import os
import requests
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Serve the HTML file
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# Endpoint 1: Send Mapbox Key to frontend
@app.route('/api/config')
def get_config():
    return jsonify({'mapboxKey': os.getenv('MAPBOX_KEY')})

# Endpoint 2: The Master Scan
@app.route('/api/scan')
def scan():
    lat = request.args.get('lat')
    lng = request.args.get('lng')

    if not lat or not lng:
        return jsonify({'error': 'Missing coordinates'}), 400

    weather_data = None
    geo_data = {'countryCode': None, 'countryName': None, 'regionName': None}

    # 1. Fetch Weather
    try:
        weather_key = os.getenv('WEATHER_KEY')
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&units=metric&appid={weather_key}"
        weather_res = requests.get(weather_url)
        if weather_res.status_code == 200:
            weather_data = weather_res.json()
    except Exception as e:
        print(f"Weather API Error: {e}")

    # 2. Fetch Geocoding
    try:
        mapbox_key = os.getenv('MAPBOX_KEY')
        geo_url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lng},{lat}.json?types=country,region&access_token={mapbox_key}"
        
        # --- NEW CODE: Send the 'Referer' header ---
        headers = {"Referer": "https://minecraft-biome-scanner.onrender.com/"} 
        geo_res = requests.get(geo_url, headers=headers)
        # -------------------------------------------
        features = geo_res.json().get('features', [])
        # Extract Country
        country = next((f for f in features if f['id'].startswith('country')), None)
        if country:
            geo_data['countryName'] = country.get('text')
            if 'short_code' in country.get('properties', {}):
                geo_data['countryCode'] = country['properties']['short_code'].upper()
        
        # Extract Region
        region = next((f for f in features if f['id'].startswith('region')), None)
        if region:
            geo_data['regionName'] = region.get('text')

    except Exception as e:
        print(f"Geo API Error: {e}")

    # Return combined data
    return jsonify({
        'weather': weather_data,
        'geo': geo_data
    })


# --- ADD THIS NEW ROUTE ---
@app.route('/images/<path:filename>')
def serve_images(filename):
    return send_from_directory('static/images', filename)
# --------------------------

if __name__ == '__main__':
    app.run(debug=True, port=3000)