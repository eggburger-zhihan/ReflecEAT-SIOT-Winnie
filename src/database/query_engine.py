"""
============================================================================
SmartSnack Monitor - Query Engine
============================================================================
============================================================================
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from collections import Counter
import logging

from .db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class QueryEngine:
    """
    Advanced query engine for time-window analysis.
    
    Core functionality:
    - Emotion window queries (before/after food events)
    - Emotion trend analysis
    - Statistical aggregations
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize query engine with database manager.
        
        Args:
            db_manager: DatabaseManager instance
        """
        self.db = db_manager
        logger.info("QueryEngine initialized")
    
    
    # ========================================================================
    # EMOTION WINDOW QUERIES (Core Analytical Function)
    # ========================================================================
    
    def query_emotion_window(
        self,
        event_timestamp: str,
        window_minutes_before: int = 10,
        window_minutes_after: int = 10
    ) -> Dict[str, Any]:
 
        # Parse timestamp
        event_time = datetime.strptime(event_timestamp, '%Y-%m-%d %H:%M:%S')
        
        # Calculate time windows
        before_start = event_time - timedelta(minutes=window_minutes_before)
        before_end = event_time
        after_start = event_time
        after_end = event_time + timedelta(minutes=window_minutes_after)
        
        # Format as strings
        before_start_str = before_start.strftime('%Y-%m-%d %H:%M:%S')
        before_end_str = before_end.strftime('%Y-%m-%d %H:%M:%S')
        after_start_str = after_start.strftime('%Y-%m-%d %H:%M:%S')
        after_end_str = after_end.strftime('%Y-%m-%d %H:%M:%S')
        
        # Query emotions BEFORE the event
        emotions_before_records = self.db.get_emotions_in_time_window(
            before_start_str,
            before_end_str
        )
        
        # Query emotions AFTER the event
        emotions_after_records = self.db.get_emotions_in_time_window(
            after_start_str,
            after_end_str
        )
        
        # Extract emotion classes and confidences
        emotions_before = [r['emotion_class'] for r in emotions_before_records]
        emotions_after = [r['emotion_class'] for r in emotions_after_records]
        
        confidences_before = [r['confidence'] for r in emotions_before_records]
        confidences_after = [r['confidence'] for r in emotions_after_records]
        
        # Compute dominant emotions
        dominant_before = self._get_dominant_emotion(emotions_before)
        dominant_after = self._get_dominant_emotion(emotions_after)
        
        # Calculate average confidences
        avg_confidence_before = (
            sum(confidences_before) / len(confidences_before)
            if confidences_before else 0.0
        )
        avg_confidence_after = (
            sum(confidences_after) / len(confidences_after)
            if confidences_after else 0.0
        )
        
        # Analyze emotion trend
        trend = self._analyze_emotion_trend(dominant_before, dominant_after)
        
        logger.info(
            f"Emotion window query: {dominant_before} → {dominant_after} ({trend}) "
            f"at {event_timestamp}"
        )
        
        return {
            'event_time': event_timestamp,
            'emotions_before': emotions_before,
            'emotions_after': emotions_after,
            'dominant_before': dominant_before,
            'dominant_after': dominant_after,
            'trend': trend,
            'confidence_before': round(avg_confidence_before, 3),
            'confidence_after': round(avg_confidence_after, 3),
            'window_before': (before_start_str, before_end_str),
            'window_after': (after_start_str, after_end_str),
            'count_before': len(emotions_before),
            'count_after': len(emotions_after)
        }
    
    
    def _get_dominant_emotion(self, emotions: List[str]) -> Optional[str]:

        if not emotions:
            return None
        
        # Count occurrences
        emotion_counts = Counter(emotions)
        
        # Return most common
        dominant_emotion, count = emotion_counts.most_common(1)[0]
        
        return dominant_emotion
    
    
    def _analyze_emotion_trend(
        self,
        emotion_before: Optional[str],
        emotion_after: Optional[str]
    ) -> str:

        # Handle missing data
        if emotion_before is None or emotion_after is None:
            return 'Unknown'
        
        # No change
        if emotion_before == emotion_after:
            return 'Stable'
        
        # Define emotion hierarchy (higher = more positive)
        emotion_hierarchy = {
            'positive': 4,       # Most positive
            'neutral': 3,
            'negative_low': 2,   # sad
            'negative_high': 1   # Most negative (anxious/angry/fear)
        }
        
        score_before = emotion_hierarchy.get(emotion_before, 0)
        score_after = emotion_hierarchy.get(emotion_after, 0)
        
        if score_after > score_before:
            return 'Improved'
        elif score_after < score_before:
            return 'Worsened'
        else:
            return 'Stable'
    
    
    # ========================================================================
    # POST-HOC ANALYSIS (Update food events with emotion context)
    # ========================================================================
    
    def analyze_and_update_food_event(
        self,
        event_id: int,
        window_minutes: int = 10
    ) -> bool:

        # Get the food event
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp
                FROM food_event_log
                WHERE id = ?
            """, (event_id,))
            
            event = cursor.fetchone()
        
        if not event:
            logger.error(f"Food event {event_id} not found")
            return False
        
        event_timestamp = event['timestamp']
        
        # Query emotion window
        emotion_analysis = self.query_emotion_window(
            event_timestamp,
            window_minutes_before=window_minutes,
            window_minutes_after=window_minutes
        )
        
        # Update food event with emotion context
        success = self.db.update_food_event_emotions(
            event_id=event_id,
            emotion_before=emotion_analysis['dominant_before'] or 'Unknown',
            emotion_after=emotion_analysis['dominant_after'] or 'Unknown',
            emotion_trend=emotion_analysis['trend']
        )
        
        if success:
            logger.info(
                f"Updated food event {event_id}: "
                f"{emotion_analysis['dominant_before']} → "
                f"{emotion_analysis['dominant_after']} ({emotion_analysis['trend']})"
            )
        
        return success
    
    
    def batch_analyze_food_events(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> int:
 
        # Build query
        query = "SELECT id FROM food_event_log WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND DATE(timestamp) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(timestamp) <= ?"
            params.append(end_date)
        
        query += " ORDER BY timestamp ASC"
        
        # Get all food event IDs
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            event_ids = [row['id'] for row in cursor.fetchall()]
        
        # Analyze each event
        success_count = 0
        for event_id in event_ids:
            if self.analyze_and_update_food_event(event_id):
                success_count += 1
        
        logger.info(f"Batch analysis complete: {success_count}/{len(event_ids)} events")
        return success_count
    
    
    # ========================================================================
    # STATISTICAL QUERIES
    # ========================================================================
    
    def get_emotion_distribution(
        self,
        start_time: str,
        end_time: str
    ) -> Dict[str, int]:
        """
        Get emotion distribution in a time range.
 
        """
        emotions = self.db.get_emotions_in_time_window(start_time, end_time)
        
        emotion_counts = Counter([e['emotion_class'] for e in emotions])
        
        # Ensure all 4 emotions are represented
        return {
            'Happy': emotion_counts.get('Happy', 0),
            'Neutral': emotion_counts.get('Neutral', 0),
            'Sad': emotion_counts.get('Sad', 0),
            'Anxious': emotion_counts.get('Anxious', 0)
        }
    
    
    def get_average_emotion_score(
        self,
        start_time: str,
        end_time: str
    ) -> float:
        """
        Calculate average emotion score in a time range.
        
        Emotion Scores:
        - Happy: 4
        - Neutral: 3
        - Sad: 2
        - Anxious: 1
        """
        emotions = self.db.get_emotions_in_time_window(start_time, end_time)
        
        if not emotions:
            return 0.0
        
        emotion_scores = {
            'Happy': 4,
            'Neutral': 3,
            'Sad': 2,
            'Anxious': 1
        }
        
        scores = [emotion_scores[e['emotion_class']] for e in emotions]
        avg_score = sum(scores) / len(scores)
        
        return round(avg_score, 2)
    
    
    # ========================================================================
    # CORRELATION ANALYSIS
    # ========================================================================
    
    def get_food_emotion_correlation_matrix(self) -> Dict[str, Dict[str, int]]:

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT emotion_before, food_type, COUNT(*) as count
                FROM food_event_log
                WHERE emotion_before IS NOT NULL
                GROUP BY emotion_before, food_type
            """)
            
            rows = cursor.fetchall()
        
        # Build matrix
        matrix = {}
        for row in rows:
            emotion = row['emotion_before']
            food = row['food_type']
            count = row['count']
            
            if emotion not in matrix:
                matrix[emotion] = {}
            
            matrix[emotion][food] = count
        
        return matrix
    
    
    def get_emotion_improvement_rate_by_food(self) -> Dict[str, Dict[str, Any]]:

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT food_type, emotion_trend, COUNT(*) as count
                FROM food_event_log
                WHERE emotion_trend IS NOT NULL
                GROUP BY food_type, emotion_trend
            """)
            
            rows = cursor.fetchall()
        
        # Build statistics
        stats = {}
        for row in rows:
            food = row['food_type']
            trend = row['emotion_trend']
            count = row['count']
            
            if food not in stats:
                stats[food] = {
                    'improved': 0,
                    'worsened': 0,
                    'stable': 0
                }
            
            stats[food][trend.lower()] = count
        
        # Calculate improvement rates
        for food, counts in stats.items():
            total = counts['improved'] + counts['worsened'] + counts['stable']
            if total > 0:
                counts['rate'] = round(counts['improved'] / total, 3)
            else:
                counts['rate'] = 0.0
        
        return stats
    
    
    # ========================================================================
    # TIME-SERIES ANALYSIS
    # ========================================================================
    
    def get_hourly_emotion_pattern(
        self,
        date: str
    ) -> Dict[int, Dict[str, int]]:

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                    emotion_class,
                    COUNT(*) as count
                FROM emotion_log
                WHERE DATE(timestamp) = ?
                GROUP BY hour, emotion_class
                ORDER BY hour
            """, (date,))
            
            rows = cursor.fetchall()
        
        # Build hourly pattern
        pattern = {hour: {'positive': 0, 'neutral': 0, 'negative_low': 0, 'negative_high': 0} 
                   for hour in range(24)}
        
        for row in rows:
            hour = row['hour']
            emotion = row['emotion_class']
            count = row['count']
            pattern[hour][emotion] = count
        
        return pattern
    
    
    def get_snacking_frequency_by_hour(self) -> Dict[int, int]:

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    CAST(strftime('%H', timestamp) AS INTEGER) as hour,
                    COUNT(*) as count
                FROM food_event_log
                GROUP BY hour
                ORDER BY hour
            """)
            
            rows = cursor.fetchall()
        
        frequency = {hour: 0 for hour in range(24)}
        for row in rows:
            frequency[row['hour']] = row['count']
        
        return frequency
    
    
    # ========================================================================
    # LIGHT EXPOSURE ANALYSIS
    # ========================================================================
    
    def get_light_emotion_correlation(
        self,
        date: str
    ) -> List[Dict[str, Any]]:

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    CAST(strftime('%H', l.timestamp) AS INTEGER) as hour,
                    AVG(l.lux_value) as avg_lux,
                    e.emotion_class,
                    COUNT(e.id) as emotion_count
                FROM indoor_light_log l
                LEFT JOIN emotion_log e 
                    ON CAST(strftime('%H', l.timestamp) AS INTEGER) = 
                       CAST(strftime('%H', e.timestamp) AS INTEGER)
                    AND DATE(l.timestamp) = DATE(e.timestamp)
                WHERE DATE(l.timestamp) = ?
                GROUP BY hour, e.emotion_class
                ORDER BY hour, emotion_count DESC
            """, (date,))
            
            rows = cursor.fetchall()
        
        # Process results
        results = []
        current_hour = None
        hour_data = None
        
        for row in rows:
            hour = row['hour']
            
            if hour != current_hour:
                if hour_data:
                    results.append(hour_data)
                
                hour_data = {
                    'hour': hour,
                    'avg_lux': round(row['avg_lux'], 2) if row['avg_lux'] else 0,
                    'dominant_emotion': row['emotion_class'],
                    'emotion_count': row['emotion_count']
                }
                current_hour = hour
        
        if hour_data:
            results.append(hour_data)
        
        return results


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Initialize
    db = DatabaseManager()
    engine = QueryEngine(db)
    
    print("=== Testing Query Engine ===")
    
    # Test 1: Insert sample data
    print("Inserting sample data...")
    
    # Insert emotions over 20 minutes
    base_time = datetime.now()
    for i in range(10):
        timestamp = (base_time - timedelta(minutes=10-i)).strftime('%Y-%m-%d %H:%M:%S')
        emotion = 'Anxious' if i < 5 else 'Neutral'
        db.insert_emotion(emotion, 0.85, timestamp)
    
    # Insert food event at base_time
    event_timestamp = base_time.strftime('%Y-%m-%d %H:%M:%S')
    event_id = db.insert_food_event(
        food_type='Nutella',
        health_category='Unhealthy',
        detection_confidence=0.92,
        detection_source='Custom_YOLO',
        calories=200,
        timestamp=event_timestamp
    )
    
    print(f"Inserted food event ID: {event_id}")
    
    # Test 2: Query emotion window
    print("Querying emotion window...")
    result = engine.query_emotion_window(event_timestamp)
    
    print(f"  Event time: {result['event_time']}")
    print(f"  Emotions before: {result['emotions_before']}")
    print(f"  Emotions after: {result['emotions_after']}")
    print(f"  Dominant before: {result['dominant_before']}")
    print(f"  Dominant after: {result['dominant_after']}")
    print(f"  Trend: {result['trend']}")
    
    # Test 3: Update food event with emotion context
    print("Performing post-hoc analysis...")
    success = engine.analyze_and_update_food_event(event_id)
    print(f"Update successful: {success}")
    
    # Test 4: Get emotion distribution
    print("Getting emotion distribution...")
    start = (base_time - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    end = (base_time + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    distribution = engine.get_emotion_distribution(start, end)
    print(f"Distribution: {distribution}")
    
    print("All query engine tests passed!")