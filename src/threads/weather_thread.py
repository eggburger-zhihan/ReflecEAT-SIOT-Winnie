"""
Weather Monitor Thread
----------------------
Records weather every 60 minutes (Time-Driven).
"""

import threading
import time
import logging

logger = logging.getLogger(__name__)


class WeatherThread(threading.Thread):
    """Background thread for periodic weather recording."""
    
    def __init__(self, weather_api, db_manager, interval_minutes=60):
        """
        Args:
            weather_api: WeatherAPIHandler instance
            db_manager: DatabaseManager instance
            interval_minutes: Recording interval (default: 60)
        """
        super().__init__(daemon=True)
        self.weather_api = weather_api
        self.db = db_manager
        self.interval = interval_minutes * 60  # Convert to seconds
        self.running = False
    
    def run(self):
        """Main thread loop."""
        self.running = True
        logger.info(f"WeatherThread started (interval: {self.interval // 60} min)")
        
        # Record immediately on start
        self._record_weather()
        
        while self.running:
            # Sleep in small chunks to allow quick shutdown
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)
            
            if self.running:
                try:
                    self._record_weather()
                except Exception as e:
                    logger.error(f"WeatherThread error: {e}")
        
        logger.info("WeatherThread stopped")
    
    def _record_weather(self):
        """Fetch weather data and record to database."""
        data = self.weather_api.get_weather_data(force_refresh=True)
        
        if data is None:
            logger.warning("WeatherThread: Failed to fetch weather")
            return
        
        # Insert to database
        self.db.insert_weather(
            weather_condition=data.get('weather_condition'),
            temperature=data.get('temperature'),
            humidity=data.get('humidity'),
            daylight_duration=data.get('daylight_hours'),
            sunrise_time=data.get('sunrise_time'),
            sunset_time=data.get('sunset_time')
        )
        
        logger.info(f"WeatherThread: Recorded {data['weather_condition']}, {data['temperature']}°C")
    
    def stop(self):
        """Stop the thread."""
        self.running = False