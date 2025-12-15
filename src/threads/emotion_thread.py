"""
Emotion Monitor Thread
----------------------
Records emotion every 2 minutes (Time-Driven).
"""

import threading
import time
import logging

logger = logging.getLogger(__name__)


class EmotionThread(threading.Thread):
    """Background thread for periodic emotion recording."""
    
    def __init__(self, emotion_recognizer, db_manager, camera_handler, interval_minutes=2):
        """
        Args:
            emotion_recognizer: EmotionRecognizer instance
            db_manager: DatabaseManager instance
            camera_handler: CameraHandler instance
            interval_minutes: Recording interval (default: 2)
        """
        super().__init__(daemon=True)
        self.emotion_recognizer = emotion_recognizer
        self.db = db_manager
        self.camera = camera_handler
        self.interval = interval_minutes * 60  # Convert to seconds
        self.running = False
    
    def run(self):
        """Main thread loop."""
        self.running = True
        logger.info(f"EmotionThread started (interval: {self.interval // 60} min)")
        
        while self.running:
            try:
                self._record_emotion()
            except Exception as e:
                logger.error(f"EmotionThread error: {e}")
            
            # Sleep in small chunks to allow quick shutdown
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)
        
        logger.info("EmotionThread stopped")
    
    def _record_emotion(self):
        """Capture frame and record emotion to database."""
        frame = self.camera.capture_frame()
        if frame is None:
            logger.warning("EmotionThread: Failed to capture frame")
            return
        
        result = self.emotion_recognizer.recognize(frame)
        if result is None:
            logger.debug("EmotionThread: No face detected")
            return
        
        # Get max probability as confidence
        confidence = max(result['probabilities'].values())
        
        # Insert to database
        self.db.insert_emotion(
            emotion_class=result['emotion'],
            confidence=confidence
        )
        
        logger.info(f"EmotionThread: Recorded {result['emotion']} ({confidence:.2f})")
    
    def stop(self):
        """Stop the thread."""
        self.running = False