-- ============================================================================
-- SmartSnack Monitor - Database Schema
-- ============================================================================
-- Purpose: Four-table architecture for emotion, light, weather, and food logging
-- Drop existing tables if they exist (for clean restart)
DROP TABLE IF EXISTS food_event_log;
DROP TABLE IF EXISTS weather_log;
DROP TABLE IF EXISTS indoor_light_log;
DROP TABLE IF EXISTS emotion_log;

-- ============================================================================
-- TABLE 1: emotion_log
-- ============================================================================
-- Purpose: Record baseline emotional state every 2 minutes
-- Trigger: Time-Driven (Background Thread)
-- Frequency: Every 2 minutes
-- Research Goal: Establish circadian rhythm pattern of emotions
-- ============================================================================

CREATE TABLE emotion_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,                -- ISO 8601 format: '2024-12-02 14:30:00'
    emotion_class TEXT NOT NULL,            -- 'positive', 'negative_low', 'negative_high', 'neutral'
    confidence REAL NOT NULL,               -- Detection confidence (0.0 - 1.0)
    
    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (emotion_class IN ('positive', 'negative_low', 'negative_high', 'neutral')),
    CHECK (confidence >= 0.0 AND confidence <= 1.0)
);

-- Index for fast time-range queries (critical for emotion window lookup)
CREATE INDEX idx_emotion_timestamp ON emotion_log(timestamp);


-- ============================================================================
-- TABLE 2: indoor_light_log
-- ============================================================================
-- Purpose: Record indoor light exposure continuously
-- Trigger: Time-Driven (Background Thread)
-- Frequency: Every 10 minute
-- Research Goal: Compare indoor vs outdoor light exposure
-- ============================================================================

CREATE TABLE indoor_light_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,                -- ISO 8601 format
    lux_value REAL NOT NULL,                -- Light intensity from BH1750/LDR (lux)
    
    -- Metadata
    sensor_type TEXT DEFAULT 'BH1750',      -- 'BH1750' or 'LDR'
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (lux_value >= 0.0)                -- Lux cannot be negative
);

-- Index for time-series analysis
CREATE INDEX idx_indoor_light_timestamp ON indoor_light_log(timestamp);


-- ============================================================================
-- TABLE 3: weather_log
-- ============================================================================
-- Purpose: Record outdoor environmental conditions
-- Trigger: Time-Driven (Background Thread)
-- Frequency: Every 60 minutes
-- Research Goal: Calculate daylight duration and correlate with mood
-- ============================================================================

CREATE TABLE weather_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,                -- ISO 8601 format
    
    -- Weather Data
    outdoor_lux REAL,                       -- Estimated outdoor lux (calculated from condition)
    weather_condition TEXT,                 -- 'Clear', 'Partly Cloudy', 'Cloudy', 'Rainy', 'Snowy'
    temperature REAL,                       -- Temperature in Celsius
    humidity REAL,                          -- Humidity percentage (0-100)
    
    -- Daylight Information
    sunrise_time TEXT,                      -- ISO 8601 format
    sunset_time TEXT,                       -- ISO 8601 format
    daylight_duration REAL,                 -- Duration in hours
    
    -- API Metadata
    api_source TEXT DEFAULT 'OpenWeatherMap', -- Weather API provider
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (humidity >= 0.0 AND humidity <= 100.0),
    CHECK (daylight_duration >= 0.0 AND daylight_duration <= 24.0)
);

-- Index for time-series analysis
CREATE INDEX idx_weather_timestamp ON weather_log(timestamp);


-- ============================================================================
-- TABLE 4: food_event_log
-- ============================================================================
-- Purpose: Record food consumption events (EVENT-DRIVEN)
-- Trigger: Vision detection (YOLO)
-- Frequency: When food is detected (with cooldown)
-- Research Goal: PRIMARY ANALYSIS ANCHOR - correlate food with emotion changes
-- ============================================================================

CREATE TABLE food_event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,                -- ISO 8601 format: when food was detected
    
    -- Food Detection Data
    food_type TEXT NOT NULL,                -- 'Chip', 'Nutella', 'Cookie', 'Baby Carrot', 
                                            -- 'Cherry Tomato', 'Banana', 'Apple', 'Donut'
    health_category TEXT NOT NULL,          -- 'Healthy' or 'Unhealthy'
    calories INTEGER,                       -- Calories per serving (from USDA database)
    
    -- Detection Metadata
    detection_confidence REAL NOT NULL,     -- YOLO confidence score (0.0 - 1.0)
    detection_source TEXT NOT NULL,         -- 'Custom_YOLO' or 'COCO_Pretrained' or 'Fusion'
    
    -- Emotion Context (Post-Hoc Analysis)
    emotion_before TEXT,                    -- Dominant emotion in T-10 to T window
    emotion_after TEXT,                     -- Dominant emotion in T to T+10 window
    emotion_trend TEXT,                     -- 'Improved', 'Worsened', 'Stable', 'Unknown'
    
    -- Actuation Record
    warning_triggered INTEGER DEFAULT 0,    -- 1 if Arduino warning was triggered, 0 otherwise
    
    -- Metadata
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CHECK (health_category IN ('Healthy', 'Unhealthy')),
    CHECK (detection_confidence >= 0.0 AND detection_confidence <= 1.0),
    CHECK (detection_source IN ('Custom_YOLO', 'COCO_Pretrained', 'Fusion')),
    CHECK (warning_triggered IN (0, 1)),
    CHECK (emotion_trend IN ('Improved', 'Worsened', 'Stable', 'Unknown', NULL))
);

-- Index for time-range queries and food type analysis
CREATE INDEX idx_food_event_timestamp ON food_event_log(timestamp);
CREATE INDEX idx_food_event_type ON food_event_log(food_type);
CREATE INDEX idx_food_event_health ON food_event_log(health_category);


-- ============================================================================
-- VIEWS FOR ANALYSIS
-- ============================================================================

-- View 1: Get emotion trends around food events
CREATE VIEW IF NOT EXISTS emotion_food_correlation AS
SELECT 
    f.id AS event_id,
    f.timestamp AS event_time,
    f.food_type,
    f.health_category,
    f.emotion_before,
    f.emotion_after,
    f.emotion_trend,
    f.calories
FROM food_event_log f
ORDER BY f.timestamp DESC;


-- View 2: Daily emotion summary
CREATE VIEW IF NOT EXISTS daily_emotion_summary AS
SELECT 
    DATE(timestamp) AS date,
    emotion_class,
    COUNT(*) AS occurrence_count,
    AVG(confidence) AS avg_confidence
FROM emotion_log
GROUP BY DATE(timestamp), emotion_class
ORDER BY date DESC, occurrence_count DESC;


-- View 3: Light exposure comparison
CREATE VIEW IF NOT EXISTS light_exposure_comparison AS
SELECT 
    DATE(i.timestamp) AS date,
    AVG(i.lux_value) AS avg_indoor_lux,
    AVG(w.outdoor_lux) AS avg_outdoor_lux,
    AVG(w.daylight_duration) AS avg_daylight_hours
FROM indoor_light_log i
LEFT JOIN weather_log w ON DATE(i.timestamp) = DATE(w.timestamp)
GROUP BY DATE(i.timestamp)
ORDER BY date DESC;


-- View 4: Unhealthy snacking frequency by emotion
CREATE VIEW IF NOT EXISTS unhealthy_snacking_by_emotion AS
SELECT 
    f.emotion_before,
    COUNT(*) AS snack_count,
    AVG(f.calories) AS avg_calories
FROM food_event_log f
WHERE f.health_category = 'Unhealthy'
AND f.emotion_before IS NOT NULL
GROUP BY f.emotion_before
ORDER BY snack_count DESC;