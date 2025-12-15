"""
Light Monitor Thread
--------------------
Records indoor light every 5 minutes (Time-Driven).
"""

import threading
import time
import logging

logger = logging.getLogger(__name__)


class LightThread(threading.Thread):
    """Background thread for periodic light recording."""
    
    def __init__(self, arduino_handler, db_manager, interval_minutes=5):
        """
        Args:
            arduino_handler: ArduinoHandler instance
            db_manager: DatabaseManager instance
            interval_minutes: Recording interval (default: 5)
        """
        super().__init__(daemon=True)
        self.arduino = arduino_handler
        self.db = db_manager
        self.interval = interval_minutes * 60  # Convert to seconds
        self.running = False
    
    def run(self):
        """Main thread loop."""
        self.running = True
        logger.info(f"LightThread started (interval: {self.interval // 60} min)")
        
        while self.running:
            try:
                self._record_light()
            except Exception as e:
                logger.error(f"LightThread error: {e}")
            
            # Sleep in small chunks to allow quick shutdown
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)
        
        logger.info("LightThread stopped")
    
    def _record_light(self):
        """Read light sensor and record to database."""
        lux = self.arduino.read_light()
        
        if lux is None:
            logger.warning("LightThread: Failed to read light sensor")
            return
        
        # Insert to database
        self.db.insert_indoor_light(
            lux_value=lux,
            sensor_type='BH1750'
        )
        
        logger.info(f"LightThread: Recorded {lux:.1f} lux")
    
    def stop(self):
        """Stop the thread."""
        self.running = False