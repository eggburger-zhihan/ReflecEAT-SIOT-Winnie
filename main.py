"""
SmartSnack Monitor - Main Program
=================================
DE4-SIOT Final Project
Author: Winnie

Four-Layer IoT Architecture:
├─ Layer 1: Perception (Camera + Arduino BH1750 + Weather API)
├─ Layer 2: Application (Emotion Recognition + Food Detection + Health Classification)
├─ Layer 3: Actuation (LED warning + Servo shake/nod)
└─ Layer 4: Presentation (Database logging + Real-time UI)

Research Question:
Does reduced daylight exposure trigger SAD, leading to emotional eating?
"""

import cv2
import time
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Colors for visualization (BGR)
COLORS = {
    'positive': (0, 255, 0),       # Green
    'negative_low': (255, 0, 255), # Purple
    'negative_high': (0, 0, 255),  # Red
    'neutral': (0, 255, 255),      # Yellow
    'healthy': (0, 255, 0),        # Green
    'unhealthy': (0, 0, 255)       # Red
}


def main():
    """Main entry point."""
    
    print("="*60)
    print("SmartSnack Monitor - Starting...")
    print("="*60 + "\n")
    
    # ==================== Load Config ====================
    from src.utils.config_loader import get_config
    config = get_config()
    logger.info("Config loaded")
    
    # ==================== Initialize Database ====================
    from src.database.db_manager import DatabaseManager
    db = DatabaseManager('data/smartsnack.db', use_cloud=True)
    logger.info("Database initialized with cloud sync enabled")
    
    # ==================== Initialize Perception Layer ====================
    from src.perception.camera_handler import CameraHandler
    from src.perception.arduino_handler import ArduinoHandler
    from src.perception.weather_api import WeatherAPIHandler
    
    camera = CameraHandler()
    logger.info("Camera initialized")
    
    arduino = ArduinoHandler()
    if not arduino.is_connected:
        logger.warning("Arduino not connected - actuators disabled")
    
    weather_api = WeatherAPIHandler(config)
    logger.info("Weather API initialized")
    
    # ==================== Initialize Cloud Layer ====================
    #cloud = CloudHandler() 
    cloud = None
    # ==================== Start Background Threads ====================
    # 
    # 
    
    from src.threads import EmotionThread, LightThread, WeatherThread
    
    # 
    # 
    # ==================== Initialize Application Layer ====================
    from src.application.emotion_recognition import EmotionRecognizer
    from src.application.food_detection import FoodDetector
    from src.application.health_classifier import HealthClassifier
    
    emotion_recognizer = EmotionRecognizer(config)
    logger.info("Emotion recognizer initialized")
    
    food_detector = FoodDetector(config)
    logger.info("Food detector initialized")
    
    health_classifier = HealthClassifier(config)
    logger.info("Health classifier initialized")
    
    # ==================== Start Background Threads ====================
    from src.threads import EmotionThread, LightThread, WeatherThread
    
    emotion_thread = EmotionThread(emotion_recognizer, db, camera, 
                                   interval_minutes=2)
    light_thread = LightThread(arduino, db, interval_minutes=5)
    weather_thread = WeatherThread(weather_api, db, interval_minutes=60)
    
    emotion_thread.start()
    light_thread.start()
    weather_thread.start()
    logger.info("Background threads started")
    
    # ==================== Main Loop ====================
    print("-"*60)
    print("System running! Press 'q' to quit.")
    print("-"*60)
    
    # State tracking
    last_unhealthy_warning = 0
    warning_cooldown = 30
    frame_count = 0
    session_start = datetime.now()
    
    # Session stats
    session_stats = {'healthy': 0, 'unhealthy': 0, 'total': 0}
    
    try:
        while True:
            frame = camera.capture_frame()
            if frame is None:
                continue
            
            frame = cv2.flip(frame, 1)  # Mirror
            frame_count += 1
            h, w = frame.shape[:2]
            
            # ==================== Emotion Detection ====================
            emotion_result = emotion_recognizer.recognize(frame)
            current_emotion = emotion_result['emotion'] if emotion_result else 'neutral'
            emotion_probs = emotion_result['probabilities'] if emotion_result else {}
            face_bbox = emotion_result['face_bbox'] if emotion_result else None
            
            # ==================== Food Detection ====================
            detections = food_detector.detect(frame)
            
            for det in detections:
                label = det['label']
                is_new = det['is_new']
                
                if not is_new:
                    continue
                
                info = health_classifier.get_info(label)
                current_hour = datetime.now().hour
                
                # Log food event
                db.insert_food_event(
                    food_type=label,
                    health_category=info['category'].capitalize(),
                    detection_confidence=det['confidence'],
                    detection_source='Fusion',
                    calories=info['calories'],
                    emotion_before=current_emotion,  # Atomic binding
                    warning_triggered=1 if (info['category'] == 'unhealthy' 
                                            and current_hour >= 17) else 0
                )
                
                # Update session stats
                session_stats['total'] += 1
                if info['category'] == 'healthy':
                    session_stats['healthy'] += 1
                else:
                    session_stats['unhealthy'] += 1
                
                logger.info(f"Food detected: {label} ({info['category']})")
                
                # ==================== Actuation Logic ====================
                if arduino.is_connected:
                    if info['category'] == 'unhealthy' and (current_hour >= 19 
                                                            or current_hour < 4):
                        now = time.time()
                        if now - last_unhealthy_warning > warning_cooldown:
                            logger.info("Triggering unhealthy warning!")
                            arduino.warn_unhealthy(led_duration=5)
                            last_unhealthy_warning = now
                    elif info['category'] == 'healthy':
                        logger.info("Encouraging healthy choice!")
                        arduino.encourage_healthy()
            
            # ==================== Draw UI ====================
            # Top status bar
            cv2.rectangle(frame, (0, 0), (w, 70), (0, 0, 0), -1)
            
            # Emotion status
            emotion_color = COLORS.get(current_emotion, (255, 255, 255))
            cv2.putText(frame, f"EMOTION: {current_emotion.upper()}", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, emotion_color, 2)
            
            # Session stats
            stats_text = f"Events: {session_stats['total']} | H:{session_stats['healthy']} U:{session_stats['unhealthy']}"
            cv2.putText(frame, stats_text, (10, 55),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
            # Time
            time_text = datetime.now().strftime("%H:%M:%S")
            cv2.putText(frame, time_text, (w - 100, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
            
            # Draw face box + emotion bars
            if face_bbox:
                x, y, wb, hb = face_bbox
                cv2.rectangle(frame, (x, y), (x + wb, y + hb), emotion_color, 2)
                cv2.putText(frame, current_emotion, (x, y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, emotion_color, 2)
                
                # Emotion probability bars
                if emotion_probs:
                    bar_y = y + hb + 20
                    for emo_name in ['positive', 'neutral', 'negative_low', 'negative_high']:
                        prob = emotion_probs.get(emo_name, 0.0)
                        bar_len = int(min(prob, 2.0) * 50)
                        bar_color = COLORS.get(emo_name, (255, 255, 255))
                        
                        cv2.putText(frame, emo_name[:3], (x, bar_y),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                        cv2.rectangle(frame, (x + 40, bar_y - 8), (x + 40 + bar_len, bar_y), bar_color, -1)
                        bar_y += 18
            
            # Draw food detections
            for det in detections:
                x1, y1, x2, y2 = det['bbox']
                label = det['label']
                conf = det['confidence']
                is_new = det['is_new']
                info = health_classifier.get_info(label)
                
                # Color based on health category
                box_color = COLORS.get(info['category'], (255, 255, 255))
                if not is_new:
                    box_color = (128, 128, 128)  # Gray if in cooldown
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
                
                text = f"{label} ({info['calories']}cal)"
                if not is_new:
                    text += " [CD]"
                cv2.putText(frame, text, (x1, y1 - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, box_color, 2)
            
            # Show frame
            cv2.imshow('SmartSnack Monitor', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    
    finally:
        # ==================== Cleanup ====================
        print("="*60)
        print("Shutting down...")
        print("="*60)
        
        # Stop threads
        emotion_thread.stop()
        light_thread.stop()
        weather_thread.stop()
        
        emotion_thread.join(timeout=2)
        light_thread.join(timeout=2)
        weather_thread.join(timeout=2)
        
        # Release resources
        camera.release()
        arduino.close()
        cv2.destroyAllWindows()
        
        # Print session summary
        duration = (datetime.now() - session_start).seconds
        print(f"Session Summary:")
        print(f"  Duration: {duration}s")
        print(f"  Total Food Events: {session_stats['total']}")
        print(f"  Healthy: {session_stats['healthy']}")
        print(f"  Unhealthy: {session_stats['unhealthy']}")
    


if __name__ == "__main__":
    main()