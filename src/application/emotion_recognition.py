"""
Emotion Recognition Module
--------------------------
FER2013 model with 7→4 class mapping + DSP smoothing.
"""

import cv2
import numpy as np
from collections import deque, Counter
import logging

logger = logging.getLogger(__name__)


class EmotionRecognizer:
    """Recognizes emotions from facial expressions."""
    
    def __init__(self, config):
        """
        Args:
            config: ConfigLoader instance
        """
        # Model path
        self.model_path = config.get_model_path('emotion')
        
        # FER2013 mapping (index → target class)
        self.fer2013_mapping = config.get('emotion.fer2013_mapping', {})
        
        # Sensitivity weights
        self.sensitivity = config.get('emotion.sensitivity', {
            'positive': 1.5,
            'negative_low': 2.5,
            'negative_high': 2.0,
            'neutral': 1.0
        })
        
        # DSP smoothing
        self.dsp_enabled = config.get('emotion.dsp_filter.enabled', True)
        window_size = config.get('emotion.dsp_filter.window_size', 5)
        self.emotion_window = deque(maxlen=window_size)
        
        # Load model and face detector
        self._load_model()
        self._load_face_detector()
        
        logger.info("EmotionRecognizer initialized")
    
    def _load_model(self):
        """Load FER2013 emotion model."""
        from tensorflow import keras
        self.model = keras.models.load_model(str(self.model_path), compile=False)
    
    def _load_face_detector(self):
        """Load Haar cascade face detector."""
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
    
    def detect_face(self, frame: np.ndarray):
        """Detect largest face in frame. Returns (x,y,w,h) or None."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(50, 50))
        
        if len(faces) == 0:
            return None
        return max(faces, key=lambda f: f[2] * f[3])
    
    def _preprocess_face(self, frame: np.ndarray, bbox: tuple) -> np.ndarray:
        """Preprocess face ROI for model input."""
        x, y, w, h = bbox
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        roi = gray[y:y+h, x:x+w]
        roi = cv2.resize(roi, (64, 64))
        roi = roi.astype("float32") / 255.0
        roi = np.expand_dims(roi, axis=0)
        roi = np.expand_dims(roi, axis=-1)
        return roi
    
    def _map_predictions(self, raw_preds: np.ndarray) -> dict:
        """Map 7-class FER2013 to 4-class with sensitivity calibration."""
        scores = {
            'positive': 0.0,
            'negative_low': 0.0,
            'negative_high': 0.0,
            'neutral': 0.0
        }
        
        for idx, target_class in self.fer2013_mapping.items():
            idx = int(idx)
            if target_class is None:  # skip excluded (surprise)
                continue
            scores[target_class] += raw_preds[idx]
        
        # Apply sensitivity calibration
        for emotion in scores:
            scores[emotion] *= self.sensitivity.get(emotion, 1.0)
        
        return scores
    
    def _apply_dsp_smoothing(self, emotion: str) -> str:
        """Apply sliding window majority vote."""
        if not self.dsp_enabled:
            return emotion
        self.emotion_window.append(emotion)
        return Counter(self.emotion_window).most_common(1)[0][0]
    
    def recognize(self, frame: np.ndarray) -> dict | None:
        """
        Recognize emotion from frame.
        
        Returns:
            dict with emotion, emotion_raw, probabilities, face_bbox
            or None if no face detected
        """
        bbox = self.detect_face(frame)
        if bbox is None:
            return None
        
        roi = self._preprocess_face(frame, bbox)
        raw_preds = self.model.predict(roi, verbose=0)[0]
        probabilities = self._map_predictions(raw_preds)
        
        emotion_raw = max(probabilities, key=probabilities.get)
        emotion = self._apply_dsp_smoothing(emotion_raw)
        
        return {
            'emotion': emotion,
            'emotion_raw': emotion_raw,
            'probabilities': probabilities,
            'face_bbox': tuple(bbox)
        }
    
    def reset_smoothing(self):
        """Clear DSP smoothing window."""
        self.emotion_window.clear()