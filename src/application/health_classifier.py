"""
Health Classifier Module
------------------------
Classifies detected food items as healthy/unhealthy and provides calorie data.
"""


class HealthClassifier:
    """Classifies food items and provides nutritional info."""
    
    def __init__(self, config):
        """
        Args:
            config: ConfigLoader instance
        """
        healthy_list = config.get('health_classification.healthy_foods', [])
        unhealthy_list = config.get('health_classification.unhealthy_foods', [])
        
        self.healthy_foods = set(healthy_list)
        self.unhealthy_foods = set(unhealthy_list)
        self.calories = config.get('health_classification.calories', {})
    
    def classify(self, label: str) -> str:
        """Classify food as 'healthy', 'unhealthy', or 'unknown'."""
        if label in self.healthy_foods:
            return 'healthy'
        elif label in self.unhealthy_foods:
            return 'unhealthy'
        return 'unknown'
    
    def get_calories(self, label: str) -> int:
        """Get calorie count for a food item."""
        return self.calories.get(label, 0)
    
    def get_info(self, label: str) -> dict:
        """Get full info: label, category, calories."""
        return {
            'label': label,
            'category': self.classify(label),
            'calories': self.get_calories(label)
        }
    
    def is_healthy(self, label: str) -> bool:
        return label in self.healthy_foods
    
    def is_unhealthy(self, label: str) -> bool:
        return label in self.unhealthy_foods