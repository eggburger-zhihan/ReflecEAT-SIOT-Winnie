from supabase import create_client, Client
import datetime


SUPABASE_URL = "https://xujvkshguilaecrbdniq.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh1anZrc2hndWlsYWVjcmJkbmlxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjUzODM0NDUsImV4cCI6MjA4MDk1OTQ0NX0.kJm6mpP7hxdYvJ4jE7658ROuCSGvYSvaSuAlPxsAPQ8"


class CloudLogger:
    def __init__(self):
        try:
            self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            print("[Cloud] Connected to Supabase!")
            self.connected = True
        except Exception as e:
            print(f"[Cloud] Connection Failed: {e}")
            self.connected = False

    def log_emotion(self, emotion, confidence):
        if not self.connected: return
        data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "emotion_class": emotion,
            "confidence": confidence
        }
        self.supabase.table("emotion_log").insert(data).execute()

    def log_environment(self, lux):
        if not self.connected: return
        data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "lux_value": lux
        }
        self.supabase.table("environment_light_log").insert(data).execute()

    def log_food_event(self, food_type, health, emotion_before):
        if not self.connected: return
        data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "food_type": food_type,
            "health_category": health,
            "detection_source": "YOLOv8",
            "emotion_before": emotion_before
        }
        print(f" [Cloud] Uploading Event: {food_type}")
        self.supabase.table("food_event_log").insert(data).execute()