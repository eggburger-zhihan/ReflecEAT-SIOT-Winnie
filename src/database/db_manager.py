"""
Database Manager with Supabase Cloud Sync

"""

import sqlite3
from datetime import datetime
from typing import Optional
from supabase import create_client, Client

class DatabaseManager:
    """Database manager with dual-write to SQLite and Supabase"""
    
    def __init__(self, db_path: str, use_cloud: bool = True):
        """
        Initialize database manager
        
        Args:
            db_path: Path to local SQLite database
            use_cloud: Whether to sync to Supabase (default True)
        """
        self.db_path = db_path
        self.use_cloud = use_cloud
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        
        # Initialize Supabase if cloud sync enabled
        if self.use_cloud:
            self.supabase: Client = create_client(
                "https://xujvkshguilaecrbdniq.supabase.co",
                "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh1anZrc2hndWlsYWVjcmJkbmlxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUzODM0NDUsImV4cCI6MjA4MDk1OTQ0NX0.kJm6mpP7hxdYvJ4jE7658ROuCSGvYSvaSuAlPxsAPQ8"
            )
            print(" Supabase cloud sync enabled")
        else:
            self.supabase = None
            print(" Local-only mode (no cloud sync)")
    
    def _sync_to_cloud(self, table_name: str, data: dict):
        """
        Sync data to Supabase 

        """
        if not self.use_cloud or not self.supabase:
            return
        
        try:
            self.supabase.table(table_name).insert(data).execute()
            print(f" {table_name}: synced to cloud")
        except Exception as e:
            print(f" {table_name}: cloud sync failed - {e}")
            print("   (Data saved to local database)")
    
    # =========================================================================
    # INSERT METHODS
    # =========================================================================
    
    def insert_emotion(self, emotion_class: str, confidence: float, 
                      timestamp: Optional[str] = None):
        """Insert emotion detection result"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # 1. Write to local SQLite
        self.conn.execute("""
            INSERT INTO emotion_log (timestamp, emotion_class, confidence)
            VALUES (?, ?, ?)
        """, (timestamp, emotion_class, confidence))
        self.conn.commit()
        
        # 2. Sync to Supabase
        self._sync_to_cloud('emotion_log', {
            'timestamp': timestamp,
            'emotion_class': emotion_class,
            'confidence': confidence
        })
    
    def insert_light_reading(self, lux_value: float, 
                            timestamp: Optional[str] = None):
        """Insert light sensor reading"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # 1. Write to local SQLite
        self.conn.execute("""
            INSERT INTO environment_light_log (timestamp, lux_value, sensor_type)
            VALUES (?, ?, 'BH1750')
        """, (timestamp, lux_value))
        self.conn.commit()
        
        # 2. Sync to Supabase
        self._sync_to_cloud('environment_light_log', {
            'timestamp': timestamp,
            'lux_value': lux_value,
            'sensor_type': 'BH1750'
        })
    
    def insert_weather(self, weather_condition: str, temperature: float,
                      humidity: float, sunrise_time: str, sunset_time: str,
                      daylight_duration: float, timestamp: Optional[str] = None):
        """Insert weather data"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # 1. Write to local SQLite
        self.conn.execute("""
            INSERT INTO weather_log 
            (timestamp, weather_condition, temperature, humidity, 
             sunrise_time, sunset_time, daylight_duration)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, weather_condition, temperature, humidity,
              sunrise_time, sunset_time, daylight_duration))
        self.conn.commit()
        
        # 2. Sync to Supabase
        self._sync_to_cloud('weather_log', {
            'timestamp': timestamp,
            'weather_condition': weather_condition,
            'temperature': temperature,
            'humidity': humidity,
            'sunrise_time': sunrise_time,
            'sunset_time': sunset_time,
            'daylight_duration': daylight_duration
        })
    
    def insert_food_event(
        self,
        food_type: str,
        health_category: str,
        detection_confidence: float,
        detection_source: str,
        calories: Optional[int] = None,
        emotion_before: Optional[str] = None,
        emotion_after: Optional[str] = None,
        emotion_trend: Optional[str] = None,
        warning_triggered: int = 0,
        timestamp: Optional[str] = None
    ):
        """Insert food detection event"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # 1. Write to local SQLite
        cursor = self.conn.execute("""
            INSERT INTO food_event_log 
            (timestamp, food_type, health_category, calories, 
             detection_confidence, detection_source, emotion_before, 
             emotion_after, emotion_trend, warning_triggered)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, food_type, health_category, calories,
              detection_confidence, detection_source, emotion_before,
              emotion_after, emotion_trend, warning_triggered))
        self.conn.commit()
        row_id = cursor.lastrowid
        
        # 2. Sync to Supabase
        self._sync_to_cloud('food_event_log', {
            'timestamp': timestamp,
            'food_type': food_type,
            'health_category': health_category,
            'calories': calories,
            'detection_confidence': detection_confidence,
            'detection_source': detection_source,
            'emotion_before': emotion_before,
            'emotion_after': emotion_after,
            'emotion_trend': emotion_trend,
            'warning_triggered': warning_triggered
        })
        
        return row_id
    
    # =========================================================================
    # QUERY METHODS 
    # =========================================================================
    
    def get_recent_emotions(self, minutes: int = 30):
        """Get emotions from last N minutes"""
        cursor = self.conn.execute("""
            SELECT timestamp, emotion_class, confidence
            FROM emotion_log
            WHERE datetime(timestamp) >= datetime('now', '-' || ? || ' minutes')
            ORDER BY timestamp DESC
        """, (minutes,))
        return cursor.fetchall()
    
    def get_latest_light(self):
        """Get latest light reading"""
        cursor = self.conn.execute("""
            SELECT lux_value, timestamp
            FROM environment_light_log
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        return cursor.fetchone()
    
    def close(self):
        """Close database connection"""
        self.conn.close()
        print("Database connection closed")


# =========================================================================
# USAGE EXAMPLE
# =========================================================================

if __name__ == '__main__':
    # Initialize with cloud sync enabled
    db = DatabaseManager('data/smartsnack.db', use_cloud=True)
    
    # Insert emotion - will sync to both local and cloud
    db.insert_emotion('positive', 0.85)
    
    # Insert light reading - will sync to both local and cloud
    db.insert_light_reading(1250.5)
    
    # Insert food event - will sync to both local and cloud
    db.insert_food_event(
        food_type='chip',
        health_category='Unhealthy',
        detection_confidence=0.92,
        detection_source='Custom_YOLO',
        calories=15,
        emotion_before='negative_high'
    )
    
    print("All data written to local SQLite and synced to Supabase!")
    
    db.close()
