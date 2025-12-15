# Custom Food Detection Model - YOLOv8n

## Model Overview

**Purpose**: Detect snack consumption for SAD & Emotional Eating research  
**Architecture**: YOLOv8n (nano - optimized for real-time inference)  
**Training Date**: November 2024  
**Dataset Size**: 1,000+ self-collected images  

---

## Performance Summary

### Overall Metrics
- **mAP@0.5**: 96.9% (excellent)
- **mAP@0.5-0.95**: 90.5%
- **Inference Speed**: ~15ms per image (on GPU)

### Per-Class Performance

| Class | Precision | Recall | mAP@0.5 |
|-------|-----------|--------|---------|
| cherry_tomato | 99.5% | 94.1% | 99.5% |
| chip | 98.4% | 93.1% | 98.4% |
| cookie | 97.4% | 78.6% | 97.4% |
| baby_carrot | 95.1% | 76.9% | 95.1% |
| nutella | 94.0% | 80.0% | 94.0% |

---

## 🏗️ Model Architecture

**Base Model**: YOLOv8n  
**Input Size**: 640×640  
**Output**: Bounding boxes + class probabilities  

**Classes (5 custom categories)**:
1. `chip` - Potato chips
2. `nutella` - Nutella jar
3. `cookie` - Cookies
4. `baby_carrot` - Baby carrots
5. `cherry_tomato` - Cherry tomatoes

---

## Usage

### Load Model
```python
from ultralytics import YOLO

# Load trained model
model = YOLO('models/food/best.pt')
```

### Inference
```python
# Single image
results = model('path/to/image.jpg', conf=0.5)

# Process results
for result in results:
    boxes = result.boxes
    for box in boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
        
        class_name = model.names[class_id]
        print(f"Detected: {class_name} ({confidence:.2f})")
```

---

## Files in this Directory
```
food/
├── best.pt                    # Main model for inference
├── training_config.yaml       # Complete training parameters
├── README.md                  # This file
├── weights/
│   └── last.pt               # Last epoch checkpoint
└── training_results/
    ├── results.png           # Training curves (loss, mAP, etc.)
    ├── results.csv           # Raw training data
    ├── confusion_matrix.png  # Confusion matrix (counts)
    ├── confusion_matrix_normalized.png  # Normalized confusion matrix
    ├── labels.jpg            # Label distribution
    └── Box*_curve.png        # Various performance curves
```
