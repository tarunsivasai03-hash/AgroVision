"""
Weather service: OpenWeatherMap integration with a clearly flagged sample fallback.

Uses the free-tier endpoints (current weather + 5 day / 3 hour forecast). The
old One Call 2.5 endpoint has been retired.
"""
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

_API_BASE = "https://api.openweathermap.org/data/2.5"
_COORDS_PATTERN = re.compile(r"^\s*(-?\d{1,2}(?:\.\d+)?)\s*,\s*(-?\d{1,3}(?:\.\d+)?)\s*$")
FORECAST_DAYS = 5

# Simple farm alert thresholds derived from the forecast.
HEAVY_RAIN_MM = 20
HIGH_RAIN_CHANCE = 0.7
HEAT_C = 40
FROST_C = 3
STRONG_WIND_MS = 10


def _download_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "AgroVision/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _location_query(location: str) -> str:
    """Build the query string for a place name or a "lat,lon" pair."""
    match = _COORDS_PATTERN.match(location)
    if match:
        lat, lon = float(match.group(1)), float(match.group(2))
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return f"lat={lat}&lon={lon}"
    return f"q={urllib.parse.quote(location)}"


def _sample_data(location: str) -> dict:
    today = datetime.now(timezone.utc).date()
    conditions = [("Sunny", 20, 32, 0), ("Cloudy", 22, 29, 20), ("Rain", 19, 25, 80),
                  ("Partly Cloudy", 21, 30, 10), ("Sunny", 22, 33, 0)]
    return {
        "location": location,
        "is_sample": True,
        "current": {
            "temperature": 28,
            "feels_like": 30,
            "condition": "Partly Cloudy",
            "humidity": 65,
            "wind_speed": 4.5,
        },
        "forecast": [
            {
                "date": (today + timedelta(days=i)).strftime("%a %d %b"),
                "condition": cond,
                "temp_min": tmin,
                "temp_max": tmax,
                "precipitation": pop,
                "wind_speed": 4.0,
            }
            for i, (cond, tmin, tmax, pop) in enumerate(conditions)
        ],
        "alerts": [],
    }


def _daily_forecast(forecast: dict) -> list:
    """Collapse 3-hourly forecast entries into per-day summaries (local time)."""
    tz = timezone(timedelta(seconds=(forecast.get("city") or {}).get("timezone", 0)))
    days = OrderedDict()
    for entry in forecast.get("list", []):
        local = datetime.fromtimestamp(entry.get("dt", 0), tz)
        day = days.setdefault(local.date(), {"temps": [], "pop": 0.0, "rain": 0.0, "wind": 0.0, "conditions": {}})
        main = entry.get("main", {})
        day["temps"] += [main.get("temp_min", main.get("temp", 0)), main.get("temp_max", main.get("temp", 0))]
        day["pop"] = max(day["pop"], entry.get("pop", 0) or 0)
        day["rain"] += (entry.get("rain") or {}).get("3h", 0) or 0
        day["wind"] = max(day["wind"], (entry.get("wind") or {}).get("speed", 0) or 0)
        desc = ((entry.get("weather") or [{}])[0].get("description") or "").title()
        if desc:
            day["conditions"][desc] = day["conditions"].get(desc, 0) + 1

    result = []
    for date, day in list(days.items())[:FORECAST_DAYS]:
        condition = max(day["conditions"], key=day["conditions"].get) if day["conditions"] else ""
        result.append({
            "date": date.strftime("%a %d %b"),
            "condition": condition,
            "temp_min": round(min(day["temps"])) if day["temps"] else 0,
            "temp_max": round(max(day["temps"])) if day["temps"] else 0,
            "precipitation": int(round(day["pop"] * 100)),
            "rain_mm": round(day["rain"], 1),
            "wind_speed": round(day["wind"], 1),
        })
    return result


def _farm_alerts(days: list) -> list:
    """Derive farmer-relevant alerts from the daily forecast."""
    alerts = []
    for day in days:
        if day["rain_mm"] >= HEAVY_RAIN_MM or day["precipitation"] >= HIGH_RAIN_CHANCE * 100:
            alerts.append({"event": "Heavy Rain", "description":
                           f"{day['date']}: {day['precipitation']}% chance of rain ({day['rain_mm']} mm). "
                           "Delay spraying and fertilizer application; check field drainage."})
        if day["temp_max"] >= HEAT_C:
            alerts.append({"event": "Heat", "description":
                           f"{day['date']}: up to {day['temp_max']}°C. Irrigate early morning or evening and protect young plants."})
        if day["temp_min"] <= FROST_C:
            alerts.append({"event": "Frost", "description":
                           f"{day['date']}: down to {day['temp_min']}°C. Cover sensitive crops and irrigate lightly in the evening."})
        if day["wind_speed"] >= STRONG_WIND_MS:
            alerts.append({"event": "Strong Wind", "description":
                           f"{day['date']}: winds up to {day['wind_speed']} m/s. Avoid spraying; stake tall crops."})
    return alerts


def fetch_openweather(location: str) -> dict:
    """Fetch weather from OpenWeatherMap, or return sample data flagged with is_sample=True."""
    location = (location or "").strip()
    if not location:
        raise ValueError("Weather location is required.")

    api_key = os.environ.get("OPENWEATHER_API_KEY", "").strip()
    if not api_key:
        return _sample_data(location)

    query = _location_query(location)
    try:
        current = _download_json(f"{_API_BASE}/weather?{query}&units=metric&appid={api_key}")
        forecast = _download_json(f"{_API_BASE}/forecast?{query}&units=metric&appid={api_key}")
        days = _daily_forecast(forecast)

        name = current.get("name") or location
        country = (current.get("sys") or {}).get("country", "")
        return {
            "location": f"{name}, {country}".strip(", "),
            "is_sample": False,
            "current": {
                "temperature": round(current.get("main", {}).get("temp", 0)),
                "feels_like": round(current.get("main", {}).get("feels_like", 0)),
                "condition": (current.get("weather") or [{}])[0].get("description", "").title(),
                "humidity": current.get("main", {}).get("humidity", 0),
                "wind_speed": round(current.get("wind", {}).get("speed", 0), 1),
            },
            "forecast": days,
            "alerts": _farm_alerts(days),
        }
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ValueError(f"Could not find a place called \"{location.split(',')[0].strip()}\". Check the spelling or try a nearby town.") from None
        logger.warning(f"Weather API failed ({exc.code}); returning sample data.")
        return _sample_data(location)
    except Exception as exc:
        # Log the reason without the URL, which contains the API key.
        logger.warning(f"Weather API failed ({type(exc).__name__}); returning sample data.")
        return _sample_data(location)
