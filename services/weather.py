"""
Weather service: OpenWeatherMap integration with mock fallback.
"""
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

logger = logging.getLogger(__name__)


def _download_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "AgroVision/1.0"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_openweather(location: str) -> dict:
    """Fetch weather data from OpenWeatherMap or return mock data."""
    api_key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    if not location:
        raise ValueError("Weather location is required.")

    mock_data = {
        "location": f"{location} (Mock)",
        "current": {
            "temperature": 28,
            "feels_like": 30,
            "condition": "Partly Cloudy",
            "humidity": 65,
            "wind_speed": 4.5,
        },
        "forecast": [
            {"date": "Mon 01 Jan", "condition": "Sunny", "temp_min": 20, "temp_max": 32, "precipitation": 0, "wind_speed": 3.0},
            {"date": "Tue 02 Jan", "condition": "Cloudy", "temp_min": 22, "temp_max": 29, "precipitation": 20, "wind_speed": 5.0},
            {"date": "Wed 03 Jan", "condition": "Rain", "temp_min": 19, "temp_max": 25, "precipitation": 80, "wind_speed": 6.5},
        ],
        "alerts": []
    }

    if not api_key:
        return mock_data

    encoded_location = urllib.parse.quote(location)
    try:
        weather_url = (
            f"https://api.openweathermap.org/data/2.5/weather?q={encoded_location}"
            f"&units=metric&appid={api_key}"
        )
        current = _download_json(weather_url)

        coord = current.get("coord", {})
        lat = coord.get("lat")
        lon = coord.get("lon")
        if lat is None or lon is None:
            raise ValueError("Could not determine coordinates for the weather location.")

        onecall_url = (
            f"https://api.openweathermap.org/data/2.5/onecall?lat={lat}&lon={lon}"
            f"&exclude=minutely,hourly&units=metric&appid={api_key}"
        )
        forecast = _download_json(onecall_url)

        alerts = forecast.get("alerts", [])
        daily = forecast.get("daily", [])
        forecast_items = []
        for day in daily[:3]:
            date = datetime.utcfromtimestamp(day.get("dt", 0)).strftime("%a %d %b")
            weather_desc = day.get("weather", [{}])[0].get("description", "").title()
            forecast_items.append({
                "date": date,
                "condition": weather_desc,
                "temp_min": round(day.get("temp", {}).get("min", 0)),
                "temp_max": round(day.get("temp", {}).get("max", 0)),
                "precipitation": int(day.get("pop", 0) * 100),
                "wind_speed": round(day.get("wind_speed", 0), 1),
            })

        return {
            "location": f"{current.get('name', location)}, {current.get('sys', {}).get('country', '')}".strip(", "),
            "current": {
                "temperature": round(current.get("main", {}).get("temp", 0)),
                "feels_like": round(current.get("main", {}).get("feels_like", 0)),
                "condition": current.get("weather", [{}])[0].get("description", "").title(),
                "humidity": current.get("main", {}).get("humidity", 0),
                "wind_speed": round(current.get("wind", {}).get("speed", 0), 1),
            },
            "forecast": forecast_items,
            "alerts": alerts,
        }
    except Exception as exc:
        logger.warning(f"Weather API failed: {exc}. Using mock data.")
        return mock_data
