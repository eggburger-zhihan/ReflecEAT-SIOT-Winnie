# ReflecEAT - Smart Snack Monitor

**Investigating SAD-Induced Emotional Eating through Closed-Loop IoT Intervention**

Imperial College London | Design Engineering | DESE71003

---

## Overview
ReflecEAT is an IoT system designed to monitor and modulate stress-eating behaviors triggered by Seasonal Affective Disorder (SAD). The system integrates computer vision, emotion recognition, environmental sensing, and real-time physical feedback.

**Key Features:**
- Dual-model food detection (Custom YOLOv8 + COCO pretrained)
- Real-time emotion recognition with temporal smoothing
- Environmental light monitoring (wearable sensor)
- Closed-loop physical feedback (servo actuators)
- Cloud-synced data pipeline (SQLite + Supabase)
- Interactive web dashboard (Streamlit)

---

## Links

**Live Dashboard:** https://refleceat-dashboard-chr55qni6kwgbncegnvsie.streamlit.app

**Demo Video:** https://www.youtube.com/watch?v=EnHUkz9vp2A&feature=youtu.be

**Raw Data:** See `data/` folder (12-day study, 3,456 emotion logs, 237 food events)

---

## System Architecture

```
Perception Layer
├── Camera (YOLOv8 Food Detection + FER2013 Emotion Recognition)
├── BH1750 Light Sensor (Wearable)
└── OpenWeatherMap API

Application Layer
├── Dual-Model Fusion (Custom 5 classes + COCO 3 classes)
├── Conflict Resolution (IoU-based)
├── 5-Frame Emotion Smoothing
└── Per-Food Cooldown System

Database Layer
├── Local SQLite (Fault-Tolerant)
├── Cloud Supabase (Real-time Sync)
└── Streamlit Dashboard

Actuation Layer
├── Arduino Uno + Dual SG90 Servos
├── LED Warning Indicators
└── Serial UART Communication
```

---

## Project Structure

```
SmartSnackMonitor/
├── main.py                      Main execution loop
├── config/
│   ├── config.yaml             System configuration (not uploaded - contains API keys)
│   └── config.yaml.example     Configuration template
├── src/
│   ├── perception/
│   │   ├── camera_handler.py   Camera interface
│   │   └── arduino_handler.py  Arduino serial communication
│   ├── application/
│   │   ├── food_detection.py   YOLOv8 dual-model fusion
│   │   └── emotion_recognition.py  FER2013 with smoothing
│   ├── database/
│   │   ├── db_manager.py       Dual-write SQLite + Supabase
│   │   └── schema.sql          Database schema
│   └── threads/
│       ├── emotion_thread.py   2-min emotion logging
│       ├── light_thread.py     5-min light polling
│       └── weather_thread.py   60-min weather updates
├── data/
│   ├── smartsnack.db           SQLite database (12-day study)
│   ├── emotion_log.csv         3,456 emotion entries
│   ├── food_event_log.csv      237 food events
│   ├── environmental_light_log.csv    Environmental readings
│   └── weather_log.csv         Weather API data
├── arduino/
│   └── smartsnack_monitor.ino  Arduino firmware
├── dashboard_cloud.py          Streamlit dashboard
├── requirements.txt            Python dependencies
└── README.md
```

---

- Python 3.9+
- Arduino IDE
- Webcam
- Arduino Uno + BH1750 sensor + SG90 servos *2 + Red LED

---

## Food Categories

The system recognizes 8 food categories (5 custom + 3 COCO):

| Category | Type | Model |
|----------|------|-------|
| Chip | Unhealthy | Custom YOLOv8 |
| Cookie | Unhealthy | Custom YOLOv8 |
| Nutella | Unhealthy | Custom YOLOv8 |
| Donut | Unhealthy | COCO |
| Cherry Tomato | Healthy | Custom YOLOv8 |
| Baby Carrot | Healthy | Custom YOLOv8 |
| Apple | Healthy | COCO |
| Banana | Healthy | COCO |

---

## Research Findings

12-day longitudinal study (Nov 28 - Dec 09, 2024):

**H2 (Emotion → Food):** Negative emotions strongly correlate with unhealthy snacking  
- Pearson r = +0.66, p = 0.020 (statistically significant)

**H3 (Light → Mood):** High indoor artificial light correlated with higher stress  
- Pearson r = +0.55 (Indoor Day Paradox)

**H1 (Daylight → Mood):** Insufficient data for significance  
- Pearson r = -0.43, p = 0.161 (12-day period too short)

---

## Technical Highlights

**Dual-Model Food Detection**
- Custom YOLOv8-Nano trained on 1,247 images (97.5% mAP@50)
- Semi-supervised bootstrapping pipeline
- Two-tier conflict resolution using IoU thresholding

**Emotion Recognition**
- FER2013 model with 7-to-4 class mapping
- 5-frame consistency buffer (temporal filter)
- Prevents jittery detection from micro-expressions

**Cooldown System**
- Per-food cooldown windows (20s - 5min)
- Prevents re-detection artifacts
- Tracks eating episodes, not hand movements

**Multithreading Architecture**
- Vision: 22 FPS real-time detection
- Sensors: Non-blocking I/O operations
- Parallel data streams

**Fault-Tolerant Storage**
- Dual-write: Local SQLite + Cloud Supabase
- Zero data loss during network outages
- Atomic transactions with async sync

---

## Hardware

**Components:**
- Arduino Uno R3
- 2x SG90 Micro Servos
- BH1750 Digital Light Sensor (I2C)
- LED Indicators
- 3D-Printed PLA Enclosure

**Wiring:**
```
Arduino Uno:
├── Pin 9  → Servo 1 (Pan)
├── Pin 10 → Servo 2 (Tilt)
├── Pin 13 → LED Warning
├── SDA    → BH1750 SDA
├── SCL    → BH1750 SCL
└── 5V/GND → Power Rails
```

---

## Data Access

Raw data from the 12-day study is included in the `data/` folder:

- `smartsnack.db` - Complete SQLite database
- `emotion_log.csv` - 3,456 emotion entries (2-min intervals)
- `food_event_log.csv` - 237 food detection events
- `indoor_light_log.csv` - Environmental light readings (5-min intervals)
- `weather_log.csv` - Weather API data (hourly)

Load in Python:
```python
import pandas as pd

emotions = pd.read_csv('data/emotion_log.csv')
food = pd.read_csv('data/food_event_log.csv')
light = pd.read_csv('data/indoor_light_log.csv')
weather = pd.read_csv('data/weather_log.csv')
```

---

## Dashboard Features

Interactive Streamlit dashboard with:

- Date range selection (view multiple days or single day drill-down)
- Comprehensive timeline (emotion, light, calories over time)
- Hourly emotion flow with food event markers
- Environmental tracking (indoor lux + outdoor weather)
- Auto-generated correlation heatmaps
- Food-emotion insights (which emotions trigger which foods)
- Interactive tooltips on all data points

---

## Contact

Winnie (Zhihan) Wang  
Design Engineering, Imperial College London  
Email: zhihan.wang@imperial.ac.uk

---

## Acknowledgments

Course: DESE71003 - Sensing and Internet of Things  
Institution: Imperial College London

Technologies: Ultralytics YOLOv8, FER2013, Streamlit, Supabase
