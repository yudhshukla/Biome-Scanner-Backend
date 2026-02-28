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
            lng REAL,
            description TEXT
        )
    ''')

    # 3. Check if the table is empty. If it is, let's add our first 5 curated locations!
    cursor.execute('SELECT COUNT(*) FROM places')
    if cursor.fetchone()[0] == 0:
        curated_locations = [
            (36.1069, -115.1765, "Las Vegas Strip, USA (Desert)"),
            (21.2893, -157.8312, "Honolulu, Hawaii (Tropical Jungle)"),
            (61.2181, -149.9003, "Anchorage, Alaska (Snowy Taiga)"),
            (-1.2921, 36.8219, "Nairobi, Kenya (Savanna)"),
            (38.8354, -94.9926, "Kansas Highway, USA (Plains)"),
            (35.6895, 139.6917, "Tokyo, Japan (Cherry Grove/City)"),
            (-33.8688, 151.2093, "Sydney, Australia (Plains/Coast)")
        ]
        # Insert them all into the database
        cursor.executemany('INSERT INTO places (lat, lng, description) VALUES (?, ?, ?)', curated_locations)
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
    cursor.execute('SELECT lat, lng, description FROM places ORDER BY RANDOM() LIMIT 1')
    row = cursor.fetchone()
    conn.close()

    if row:
        # If we found one, package it up and send it to the frontend!
        return jsonify({
            'lat': row[0],
            'lng': row[1],
            'description': row[2]
        })
    else:
        # Fallback just in case the database is empty
        return jsonify({'error': 'No locations found'}), 404
    
if __name__ == '__main__':
    app.run(debug=True, port=3000)