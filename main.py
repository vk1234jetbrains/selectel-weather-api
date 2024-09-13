from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from aiohttp import ClientSession
from datetime import datetime
from collections import defaultdict, Counter
import uvicorn


app = FastAPI(root_path='/api')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TOKEN = '463178dba05d65c36df783b61bbc6280'
BASE_FORECAST_URL = f'https://api.openweathermap.org/data/2.5/forecast?appid={TOKEN}&units=metric&lang=ru&'
BASE_WEATHER_URL = f'https://api.openweathermap.org/data/2.5/weather?appid={TOKEN}&units=metric&lang=ru&'
BASE_GEOCODER_URL = f'https://api.openweathermap.org/geo/1.0/direct?appid={TOKEN}&lang=ru&'

session = ClientSession()


def group_weather_data_by_day(data):
    grouped_data = defaultdict(list)
    for entry in data['list']:
        date = datetime.utcfromtimestamp(entry['dt']).strftime('%Y-%m-%d')
        grouped_data[date].append(entry)

    return dict(grouped_data)


def get_grouped_weather_conditions(data):
    grouped_data = group_weather_data_by_day(data)
    data = []

    for date, entries in grouped_data.items():
        max_temp = max(entry['main']['temp_max'] for entry in entries)
        min_temp = min(entry['main']['temp_min'] for entry in entries)
        humidity = max(entry['main']['humidity'] for entry in entries)
        pressure = max(entry['main']['pressure'] for entry in entries)
        weather_statuses = [(entry['weather'][0]['description'], entry['weather'][0]['icon']) for entry in entries]
        most_common_status = Counter(weather_statuses).most_common(1)[0][0]
        data.append({
            'date': date,
            'max_temp': max_temp,
            'min_temp': min_temp,
            'humidity': humidity,
            'pressure': pressure,
            'status': most_common_status[0],
            'icon': most_common_status[1].replace('n', 'd'),
        })

    return data[1:]


@app.get("/getCity")
async def getCity(city: str, limit: int = 5):
    async with session.get(BASE_GEOCODER_URL + f'q={city}&limit={limit}') as r:
        data = await r.json()
    if data:
        return [{
            "name": i['local_names']['ru'] if 'ru' in i.get('local_names', {}) else i['name'],
            "state": i.get('state', i.get('country', '')),
            "lat": i['lat'],
            "lon": i['lon']
        } for i in data]
    else:
        raise HTTPException(404)


@app.get("/getWeather")
async def getWeather(lat: float, lon: float):
    async with session.get(BASE_FORECAST_URL + f'lat={lat}&lon={lon}') as r:
        data = await r.json()
    forecast = get_grouped_weather_conditions(data)

    async with session.get(BASE_WEATHER_URL + f'lat={lat}&lon={lon}') as r:
        data = await r.json()

    current = {
        'status': data['weather'][0]['description'].capitalize(),
        'icon': data['weather'][0]['icon'].replace('n', 'd'),
        'temp': data['main']['temp'],
        'feels_like': data['main']['feels_like'],
        'humidity': data['main']['humidity'],
        'pressure': data['main']['pressure'],
        'wind_speed': data['wind']['speed'],
        'wind_deg': data['wind']['deg']
    }

    return {
        'forecast': forecast,
        'current': current,
        'lat': data['coord']['lat'],
        'lon': data['coord']['lon'],
        'location': data['name']
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5973,
        log_level="debug"
    )
