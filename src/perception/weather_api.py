"""
============================================================================
SmartSnack Monitor - Weather API Handler (Enhanced)
============================================================================
"""

import requests
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class WeatherAPIHandler:

    def __init__(self, config):
        weather_config = config.get('weather')
        
        self.api_key = weather_config['api']['api_key']
        self.latitude = weather_config['location']['latitude']
        self.longitude = weather_config['location']['longitude']
        self.base_url = weather_config['api']['base_url']
        self.lux_map = weather_config['lux_estimation']
        
        cache_minutes = weather_config['update_interval_minutes']
        self.cache_duration = timedelta(minutes=cache_minutes)
        
        logger.info(f"WeatherAPIHandler initialized ({self.latitude}, {self.longitude})")
    
    
    def get_weather_data(self, force_refresh: bool = False) -> Optional[Dict[str, Any]]:

        # check cache
        if not force_refresh and self._is_cache_valid():
            logger.debug("Using cached weather data")
            return self.cached_data
        
        # call API
        logger.info("Fetching fresh weather data from OpenWeatherMap...")
        
        try:
            params = {
                'lat': self.latitude,
                'lon': self.longitude,
                'appid': self.api_key,
                'units': 'metric'  # C dgreed
            }
            
            response = requests.get(
                self.base_url,
                params=params,
                timeout=10
            )
            
            if response.status_code != 200:
                logger.error(f"API request failed: {response.status_code}")
                return self._get_fallback_data()
            
            raw_data = response.json()
            weather_data = self._parse_weather_data(raw_data)
            
            # renew cache
            self.cached_data = weather_data
            self.cache_timestamp = datetime.now()
            
            logger.info(
                f"Weather fetched: {weather_data['weather_condition']}, "
                f"{weather_data['temperature']}°C, "
                f"Daylight: {weather_data['daylight_hours']}h"
            )
            
            return weather_data
            
        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return self._get_fallback_data()
    
    
    def _parse_weather_data(self, data: Dict) -> Dict[str, Any]:
        """
        return data from api
        """
        try:
            # Daylight time calculation logic
            sunrise_timestamp = data.get('sys', {}).get('sunrise', 0)
            sunset_timestamp = data.get('sys', {}).get('sunset', 0)
            
            if sunrise_timestamp and sunset_timestamp:
                daylight_seconds = sunset_timestamp - sunrise_timestamp
                daylight_hours = round(daylight_seconds / 3600, 1)
                
                sunrise_time = datetime.fromtimestamp(
                    sunrise_timestamp, 
                    tz=timezone.utc
                ).strftime('%Y-%m-%d %H:%M:%S')
                
                sunset_time = datetime.fromtimestamp(
                    sunset_timestamp, 
                    tz=timezone.utc
                ).strftime('%Y-%m-%d %H:%M:%S')
            else:
                daylight_hours = 8.0
                sunrise_time = None
                sunset_time = None
            
            # get weather
            weather_condition = data['weather'][0]['main']
            description = data['weather'][0]['description']
            
            # estimate_outdoor_lux
            outdoor_lux = self._estimate_outdoor_lux(weather_condition)
            
            
            weather_data = {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'location': 'London, UK',
                'temperature': round(data['main']['temp'], 1),
                'humidity': data['main']['humidity'],
                'weather_condition': weather_condition,
                'description': description,
                'cloud_cover': data['clouds']['all'],
                'outdoor_lux': outdoor_lux,
                'daylight_hours': daylight_hours,
                'sunrise_time': sunrise_time,
                'sunset_time': sunset_time,
            }
            
            return weather_data
            
        except Exception as e:
            logger.error(f"Data parsing error: {e}")
            return self._get_fallback_data()
    
    
    def _estimate_outdoor_lux(self, weather_condition: str) -> float:
        """estimate outdoor lux"""
        base_lux = self.lux_map.get(weather_condition, 20000)
        
        # adjust accoding to time
        current_hour = datetime.now().hour
        
        if 6 <= current_hour < 8 or 18 <= current_hour < 20:
            base_lux *= 0.5  # dawn
        elif 20 <= current_hour or current_hour < 6:
            base_lux *= 0.01  # night
        
        return round(base_lux, 2)
    
    
    def _get_fallback_data(self) -> Dict[str, Any]:
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'location': 'London, UK',
            'temperature': 10.0,
            'humidity': 70,
            'weather_condition': 'Unknown',
            'description': 'data unavailable',
            'cloud_cover': 50,
            'outdoor_lux': 20000,
            'daylight_hours': 8.0,
            'sunrise_time': None,
            'sunset_time': None
        }
    
    
    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if self.cached_data is None or self.cache_timestamp is None:
            return False
        
        age = datetime.now() - self.cache_timestamp
        return age < self.cache_duration
    
    
    def is_daylight(self) -> Optional[bool]:
        """Is it daytime"""
        data = self.get_cached_data() or self.get_weather_data()
        
        if data is None or data['sunrise_time'] is None:
            return None
        
        try:
            now = datetime.now()
            sunrise = datetime.strptime(data['sunrise_time'], '%Y-%m-%d %H:%M:%S')
            sunset = datetime.strptime(data['sunset_time'], '%Y-%m-%d %H:%M:%S')
            
            return sunrise <= now <= sunset
        except:
            return None


# ============================================================================
# Test!
# ============================================================================

if __name__ == "__main__":
    print("\n=== Weather API Handler Test ===\n")
    
    # initial API key
    weather = WeatherAPIHandler(
        api_key="b1fc5dcdd73adc70ee25cba2980efffc",
        latitude=51.5074,
        longitude=-0.1278
    )
    
    print("Fetching weather data...\n")
    data = weather.get_weather_data()
    
    if data:
        print(" Current Weather Data:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        print(f"SAD Risk Score: {weather.get_sad_risk_score(data)}/100")
        
        risk = weather.get_sad_risk_score(data)
        if risk > 60:
            print("High Risk: Insufficient daylight")
        elif risk > 30:
            print("Medium Risk: Moderate weather")
        else:
            print("Low Risk: Good weather")
        
        is_day = weather.is_daylight()
        print(f"Is daylight: {is_day}")
    
    print("Weather API test completed!")