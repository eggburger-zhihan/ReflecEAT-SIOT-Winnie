"""
============================================================================
SmartSnack Monitor - Camera Handler
============================================================================

Features:
- OpenCV camera initialization and management
- Face detection for emotion recognition
- Frame preprocessing and resizing
- Thread-safe frame capture
- Auto-reconnection on camera failure
============================================================================
"""

import cv2
import numpy as np
from typing import Optional, Tuple, List
import logging
from pathlib import Path
import time

logger = logging.getLogger(__name__)


class CameraHandler:
    
    def __init__(
        self,
        device_id: int = 0,
        resolution: Tuple[int, int] = (1280, 720),
        fps: int = 30,
        cascade_path: Optional[str] = None
    ):
        self.device_id = device_id
        self.resolution = resolution
        self.fps = fps
        
        # Camera state
        self.camera = None
        self.is_opened = False
        
        # Initialize camera
        self._init_camera()
        
        logger.info(f"CameraHandler initialized: device_id={device_id}, resolution={resolution}")
    
    
    def _init_camera(self) -> bool:

        try:
            self.camera = cv2.VideoCapture(self.device_id)
            
            if not self.camera.isOpened():
                logger.error(f"Failed to open camera device {self.device_id}")
                return False
            
            # Set camera properties
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Verify settings
            actual_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = int(self.camera.get(cv2.CAP_PROP_FPS))
            
            logger.info(
                f"Camera opened: {actual_width}x{actual_height} @ {actual_fps}fps"
            )
            
            self.is_opened = True
            return True
            
        except Exception as e:
            logger.error(f"Camera initialization error: {e}")
            return False
    
    
    
    def capture_frame(self) -> Optional[np.ndarray]:

        if not self.is_opened or self.camera is None:
            logger.warning("Camera not opened, attempting to reconnect...")
            if not self._reconnect():
                return None
        
        try:
            ret, frame = self.camera.read()
            
            if not ret or frame is None:
                logger.warning("Failed to capture frame")
                return None
            
            return frame
            
        except Exception as e:
            logger.error(f"Frame capture error: {e}")
            return None

    
    def extract_face_roi(
        self,
        frame: np.ndarray,
        face_bbox: Tuple[int, int, int, int],
        target_size: Optional[Tuple[int, int]] = None,
        grayscale: bool = True
    ) -> Optional[np.ndarray]:

        try:
            x, y, w, h = face_bbox
            
            # Extract ROI
            face_roi = frame[y:y+h, x:x+w]
            
            if face_roi.size == 0:
                return None
            
            # Convert to grayscale if needed
            if grayscale and len(face_roi.shape) == 3:
                face_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            
            # Resize if target size specified
            if target_size is not None:
                face_roi = cv2.resize(face_roi, target_size, interpolation=cv2.INTER_AREA)
            
            return face_roi
            
        except Exception as e:
            logger.error(f"Face ROI extraction error: {e}")
            return None
    
    
    def resize_frame(
        self,
        frame: np.ndarray,
        target_size: Tuple[int, int],
        keep_aspect_ratio: bool = False
    ) -> np.ndarray:

        if keep_aspect_ratio:
            h, w = frame.shape[:2]
            target_w, target_h = target_size
            
            # Calculate scaling factor
            scale = min(target_w / w, target_h / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            # Pad to target size
            top = (target_h - new_h) // 2
            bottom = target_h - new_h - top
            left = (target_w - new_w) // 2
            right = target_w - new_w - left
            
            resized = cv2.copyMakeBorder(
                resized, top, bottom, left, right,
                cv2.BORDER_CONSTANT, value=(0, 0, 0)
            )
            
            return resized
        else:
            return cv2.resize(frame, target_size, interpolation=cv2.INTER_AREA)
    
    
    def preprocess_for_yolo(
        self,
        frame: np.ndarray,
        target_size: int = 640
    ) -> np.ndarray:

        # Resize with aspect ratio maintained
        resized = self.resize_frame(
            frame,
            (target_size, target_size),
            keep_aspect_ratio=True
        )
        
        return resized
    
    
    def _reconnect(self, max_attempts: int = 3) -> bool:

        logger.info("Attempting camera reconnection...")
        
        # Release existing connection
        if self.camera is not None:
            self.camera.release()
        
        # Try to reconnect
        for attempt in range(max_attempts):
            logger.info(f"Reconnection attempt {attempt + 1}/{max_attempts}")
            
            time.sleep(1)  # Wait before retry
            
            if self._init_camera():
                logger.info("Camera reconnection successful")
                return True
        
        logger.error(f"Camera reconnection failed after {max_attempts} attempts")
        return False
    
    
    def release(self):

        if self.camera is not None:
            self.camera.release()
            self.is_opened = False
            logger.info("Camera released")
    
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - auto release."""
        self.release()
    
    
    def __del__(self):
        """Destructor - ensure camera is released."""
        self.release()


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    print("\n=== Camera Handler Test ===\n")
    
    # Initialize camera
    camera = CameraHandler(device_id=0, resolution=(1280, 720))
    
    # Display camera info
    info = camera.get_camera_info()
    print(f" Camera Info:")
    print(f"  - Resolution: {info['width']}x{info['height']}")
    print(f"  - FPS: {info['fps']}")
    print(f"  - Device ID: {info['device_id']}")
    
    print("\nStarting camera feed (press 'q' to quit)...\n")
    
    try:
        frame_count = 0
        
        while True:
            # Capture frame
            frame = camera.capture_frame()
            
            if frame is None:
                print(" Failed to capture frame")
                break
            
            # Detect faces
            faces = camera.detect_faces(frame)
            
            # Draw face boxes
            if faces:
                frame = camera.draw_face_boxes(frame, faces)
                print(f" Frame {frame_count}: Detected {len(faces)} face(s)")
            
            # Draw FPS
            frame = camera.draw_fps(frame)
            
            # Display frame
            cv2.imshow('SmartSnack Monitor - Camera Test', frame)
            
            # Save first frame with face
            if frame_count == 0 and faces:
                camera.save_frame(frame, 'results/detection_samples/camera_test.jpg')
            
            frame_count += 1
            
            # Exit on 'q' key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        print(f"\n Final Stats:")
        print(f"  - Total frames: {camera.frame_count}")
        print(f"  - Average FPS: {camera.current_fps:.2f}")
        
    except KeyboardInterrupt:
        print("\n  Interrupted by user")
    
    finally:
        # Cleanup
        camera.release()
        cv2.destroyAllWindows()
        print("\n Camera handler test completed!")