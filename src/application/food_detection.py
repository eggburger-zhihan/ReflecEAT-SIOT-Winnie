"""
Food Detection Module
---------------------
YOLOv8 dual-model fusion with cooldown system.
"""

import time
import logging

logger = logging.getLogger(__name__)


class FoodDetector:
    """Detects food items using dual YOLO model fusion."""
    
    def __init__(self, config):
        """
        Args:
            config: ConfigLoader instance
        """
        self.config = config
        
        # Thresholds
        self.snack_conf_thr = config.get('models.food.custom_yolo.confidence_threshold', 0.5)
        self.coco_conf_thr = config.get('models.food.coco_yolo.confidence_threshold', 0.8)
        self.donut_base_thr = config.get('detection.fusion.donut_base_threshold', 0.5)
        self.iou_thr = config.get('detection.fusion.iou_conflict_threshold', 0.3)
        
        # Weights
        self.model_weights = config.get('detection.fusion.model_weights', {'snack': 1.0, 'coco': 1.0})
        self.class_weights = config.get('detection.fusion.class_weights', {})
        
        # COCO class mapping
        self.coco_wanted = config.get('models.food.coco_yolo.wanted_classes', {})
        
        # Cooldown
        self.cooldown_enabled = config.get('detection.cooldown.enabled', True)
        self.cooldown_windows = config.get('detection.cooldown.windows', {})
        self.last_detections = {}
        
        # Load models
        self._load_models()
        
        logger.info("FoodDetector initialized")
    
    def _load_models(self):
        """Load YOLO models."""
        from ultralytics import YOLO
        self.snack_model = YOLO(str(self.config.get_model_path('custom_yolo')))
        self.coco_model = YOLO(str(self.config.get_model_path('coco_yolo')))
    
    def _box_iou(self, box_a: list, box_b: list) -> float:
        """Calculate IoU between two boxes."""
        x_a = max(box_a[0], box_b[0])
        y_a = max(box_a[1], box_b[1])
        x_b = min(box_a[2], box_b[2])
        y_b = min(box_a[3], box_b[3])
        
        inter = max(0, x_b - x_a) * max(0, y_b - y_a)
        area_a = max(0, box_a[2] - box_a[0]) * max(0, box_a[3] - box_a[1])
        area_b = max(0, box_b[2] - box_b[0]) * max(0, box_b[3] - box_b[1])
        
        return inter / (area_a + area_b - inter + 1e-6)
    
    def _get_candidates(self, frame) -> list:
        """Run both models and collect candidates."""
        candidates = []
        
        # Snack model
        snack_results = self.snack_model.predict(frame, verbose=False)[0]
        for box in snack_results.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            label = snack_results.names[cls]
            
            if label not in self.class_weights or conf < self.snack_conf_thr:
                continue
            
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            score = conf * self.model_weights['snack'] * self.class_weights.get(label, 1.0)
            
            candidates.append({
                'bbox': [x1, y1, x2, y2],
                'label': label,
                'base_conf': conf,
                'model': 'snack',
                'score': score
            })
        
        # COCO model
        coco_results = self.coco_model.predict(frame, verbose=False)[0]
        for box in coco_results.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            
            # Check both int and str keys
            label = self.coco_wanted.get(cls) or self.coco_wanted.get(str(cls))
            if not label:
                continue
            
            if conf < self.coco_conf_thr:
                continue
            if label == 'donut' and conf < self.donut_base_thr:
                continue
            if label not in self.class_weights:
                continue
            
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            score = conf * self.model_weights['coco'] * self.class_weights.get(label, 1.0)
            
            candidates.append({
                'bbox': [x1, y1, x2, y2],
                'label': label,
                'base_conf': conf,
                'model': 'coco',
                'score': score
            })
        
        return candidates
    
    def _resolve_conflicts(self, candidates: list) -> list:
        """Resolve banana/nutella and donut conflicts."""
        keep = [True] * len(candidates)
        
        # Banana vs nutella
        for i in range(len(candidates)):
            if not keep[i] or candidates[i]['label'] not in ('banana', 'nutella'):
                continue
            for j in range(i + 1, len(candidates)):
                if not keep[j]:
                    continue
                if {candidates[i]['label'], candidates[j]['label']} != {'banana', 'nutella'}:
                    continue
                if self._box_iou(candidates[i]['bbox'], candidates[j]['bbox']) < self.iou_thr:
                    continue
                if candidates[i]['score'] >= candidates[j]['score']:
                    keep[j] = False
                else:
                    keep[i] = False
                    break
        
        # Donut vs snack overlaps
        snack_boxes = [c['bbox'] for i, c in enumerate(candidates) if keep[i] and c['model'] == 'snack']
        for i, c in enumerate(candidates):
            if not keep[i] or c['label'] != 'donut':
                continue
            for sb in snack_boxes:
                if self._box_iou(c['bbox'], sb) > self.iou_thr:
                    keep[i] = False
                    break
        
        return [c for i, c in enumerate(candidates) if keep[i]]
    
    def _apply_nms(self, candidates: list) -> list:
        """Apply NMS within same-label detections."""
        ordered = sorted(candidates, key=lambda c: c['score'], reverse=True)
        final = []
        used = [False] * len(ordered)
        
        for i, ci in enumerate(ordered):
            if used[i]:
                continue
            final.append(ci)
            used[i] = True
            for j in range(i + 1, len(ordered)):
                if used[j] or ordered[j]['label'] != ci['label']:
                    continue
                if self._box_iou(ci['bbox'], ordered[j]['bbox']) > 0.5:
                    used[j] = True
        
        return final
    
    def _check_cooldown(self, label: str) -> bool:
        """Check if detection is in cooldown."""
        if not self.cooldown_enabled or label not in self.last_detections:
            return False
        elapsed = time.time() - self.last_detections[label]
        return elapsed < self.cooldown_windows.get(label, 30)
    
    def _update_cooldown(self, label: str):
        self.last_detections[label] = time.time()
    
    def detect(self, frame) -> list:
        """
        Detect food items in frame.
        
        Returns:
            List of dicts with label, confidence, bbox, is_new
        """
        candidates = self._get_candidates(frame)
        candidates = self._resolve_conflicts(candidates)
        detections = self._apply_nms(candidates)
        
        results = []
        for det in detections:
            is_cooling = self._check_cooldown(det['label'])
            if not is_cooling:
                self._update_cooldown(det['label'])
            
            results.append({
                'label': det['label'],
                'confidence': det['base_conf'],
                'bbox': det['bbox'],
                'is_new': not is_cooling
            })
        
        return results
    
    def reset_cooldowns(self):
        self.last_detections.clear()