import os
import requests
from flask import Flask, jsonify, request
from flask_cors import CORS  
from dotenv import load_dotenv
import sqlite3

load_dotenv()

app = Flask(__name__)
CORS(app) #This allows GitHub Pages to talk to this server

# We no longer serve HTML or Images here. GitHub Pages does that.

def init_db():
    # 1. Connect to the database (this creates a file named 'locations.db' if it doesn't exist)
    conn = sqlite3.connect('locations.db')
    cursor = conn.cursor()

    # 2. Create the table for our coordinate vault
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL,
            lng REAL
        )
    ''')

    # 3. Check if the table is empty. If it is, let's add our first 5 curated locations!
    cursor.execute('SELECT COUNT(*) FROM places')
    if cursor.fetchone()[0] == 0:
        curated_locations = [
            (24.313860169581474, 120.72260003897149),
            (35.656953, 139.701049),
            (15.37487642320615, 73.84141820396536),
            (16.444841780257196, 81.98312723041202),
            (60.66553215661249, -151.2442154258491),
            (25.893521108388082, -80.13201875671935),
            (-22.82562754593602, -43.28518857420447),
            (25.166021850737096, 55.23289077961821),
            (6.493642556821508, 3.382043892124227),
            (47.194825422589695, 8.732110241707225),
            (39.2967789,174.0634346),
            (69.226387,-51.1038896),
            (45.8326345,6.8651281),
            (78.2244785,15.6099272),
            (-64.8396294,-62.5270017),
            (17.611136,-90.4269349),
            (-1.6959129,29.2547082),
            (55.3398559,124.7577026),
            (-13.8455335,146.5593553),
            (-8.2713522,124.409033),
            (45.0133047,78.3693),
            (46.7495666,19.4740217),
            (70.0169771,29.3159249),
            (-17.8704595,22.9141841),
            (14.4485164,-12.2097686),
            (-1.2157195,-90.4224469),
            (26.9470458,-101.4519393),
            (29.7163099,-91.8758019),
        ]
        # Insert them all into the database
        cursor.executemany('INSERT INTO places (lat, lng) VALUES (?, ?)', curated_locations)
        conn.commit()
        print("Database initialized with curated locations!")

    conn.close()

# Call the function immediately so the database is ready before the app starts
init_db()

@app.route('/api/config')
def get_config():
    return jsonify({
        'mapboxKey': os.getenv('MAPBOX_KEY'),
        'googleKey': os.getenv('GOOGLE_KEY')
    })

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
        
        # We don't need the Referer header trick as much now, but keeping it is fine.
        # Ideally, whitelist your GitHub Pages URL in Mapbox dashboard.
        geo_res = requests.get(geo_url)
        
        features = geo_res.json().get('features', [])
        country = next((f for f in features if f['id'].startswith('country')), None)
        if country:
            geo_data['countryName'] = country.get('text')
            if 'short_code' in country.get('properties', {}):
                geo_data['countryCode'] = country['properties']['short_code'].upper()
        
        region = next((f for f in features if f['id'].startswith('region')), None)
        if region:
            geo_data['regionName'] = region.get('text')

    except Exception as e:
        print(f"Geo API Error: {e}")

    return jsonify({
        'weather': weather_data,
        'geo': geo_data
    })

@app.route('/api/random-drop')
def random_drop():
    # Connect to our database
    conn = sqlite3.connect('locations.db')
    cursor = conn.cursor()

    # Grab ONE completely random location from the vault
    cursor.execute('SELECT lat, lng, FROM places ORDER BY RANDOM() LIMIT 1')
    row = cursor.fetchone()
    conn.close()

    if row:
        # If we found one, package it up and send it to the frontend!
        return jsonify({
            'lat': row[0],
            'lng': row[1],
        })
    else:
        # Fallback just in case the database is empty
        return jsonify({'error': 'No locations found'}), 404
        
if __name__ == '__main__':
    app.run(debug=True, port=3000)