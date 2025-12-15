"""
============================================================================
SmartSnack Monitor - Configuration Loader
============================================================================
Purpose: Load and parse system configuration from YAML file
Author: Winnie (DE4-SIOT Final Project)
Date: 2024-12-02
============================================================================
"""

import yaml
from pathlib import Path
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Load and manage system configuration from YAML file.
    
    Usage:
        config = ConfigLoader()
        model_path = config.get('models.emotion.model_path')
        cooldown_chip = config.get('detection.cooldown.windows.chip')
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize config loader.
        
        Args:
            config_path: Path to config.yaml (default: auto-detect from project root)
        """
        if config_path is None:
            # Auto-detect config path from project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "config.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        
        logger.info(f"Configuration loaded from {self.config_path}")
    
    
    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key_path: Dot-separated key path (e.g., 'models.emotion.model_path')
            default: Default value if key not found
        
        Returns:
            Configuration value
        
        Example:
            >>> config = ConfigLoader()
            >>> config.get('detection.cooldown.windows.chip')
            20
        """
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    
    def get_model_path(self, model_type: str) -> Path:
        """
        Get absolute path to model file.
        
        Args:
            model_type: 'emotion', 'custom_yolo', or 'coco_yolo'
        
        Returns:
            Absolute path to model file
        
        Example:
            >>> config.get_model_path('emotion')
            PosixPath('/path/to/models/emotion/fer2013_mini_XCEPTION.hdf5')
        """
        project_root = Path(__file__).parent.parent.parent
        
        if model_type == 'emotion':
            rel_path = self.get('models.emotion.model_path')
        elif model_type == 'custom_yolo':
            rel_path = self.get('models.food.custom_yolo.model_path')
        elif model_type == 'coco_yolo':
            rel_path = self.get('models.food.coco_yolo.model_path')
        else:
            raise ValueError(f"Unknown model type: {model_type}")
        
        return project_root / rel_path
    
    
    def get_cooldown_window(self, food_type: str) -> int:
        """
        Get cooldown window for a specific food type.
        
        Args:
            food_type: Food name (e.g., 'chip', 'nutella')
        
        Returns:
            Cooldown window in seconds
        
        Example:
            >>> config.get_cooldown_window('chip')
            20
        """
        windows = self.get('detection.cooldown.windows', {})
        return windows.get(food_type.lower(), 30)  # Default: 30 seconds
    
    
    def get_calories(self, food_type: str) -> int:
        """
        Get calorie value for a specific food type.
        
        Args:
            food_type: Food name
        
        Returns:
            Calories per serving
        
        Example:
            >>> config.get_calories('banana')
            90
        """
        calories = self.get('health_classification.calories', {})
        return calories.get(food_type.lower(), 0)
    
    
    def is_healthy(self, food_type: str) -> bool:
        """
        Check if a food is classified as healthy.
        
        Args:
            food_type: Food name
        
        Returns:
            True if healthy, False if unhealthy
        
        Example:
            >>> config.is_healthy('banana')
            True
            >>> config.is_healthy('donut')
            False
        """
        healthy_foods = self.get('health_classification.healthy_foods', [])
        return food_type.lower() in [f.lower() for f in healthy_foods]
    
    
    def get_health_category(self, food_type: str) -> str:
        """
        Get health category for a food type.
        
        Args:
            food_type: Food name
        
        Returns:
            'Healthy' or 'Unhealthy'
        
        Example:
            >>> config.get_health_category('apple')
            'Healthy'
        """
        return 'Healthy' if self.is_healthy(food_type) else 'Unhealthy'
    
    
    def get_ui_color(self, emotion_type: str) -> tuple:
        """
        Get UI color for emotion type (BGR format for OpenCV).
        
        Args:
            emotion_type: 'positive', 'negative_low', 'negative_high', 'neutral'
        
        Returns:
            BGR color tuple
        
        Example:
            >>> config.get_ui_color('positive')
            (185, 250, 202)
        """
        colors = self.get('ui.colors', {})
        color = colors.get(emotion_type, [255, 255, 255])  # Default: white
        return tuple(color)
    
    
    def __repr__(self) -> str:
        return f"ConfigLoader(config_path='{self.config_path}')"


# ============================================================================
# GLOBAL CONFIG INSTANCE (Singleton)
# ============================================================================
_global_config = None

def get_config() -> ConfigLoader:
    """
    Get global configuration instance (singleton pattern).
    
    Returns:
        ConfigLoader instance
    
    Example:
        >>> from src.utils.config_loader import get_config
        >>> config = get_config()
        >>> print(config.get('project.name'))
        'SmartSnack Monitor'
    """
    global _global_config
    if _global_config is None:
        _global_config = ConfigLoader()
    return _global_config


# ============================================================================
# EXAMPLE USAGE
# ============================================================================
if __name__ == "__main__":
    # Load configuration
    config = ConfigLoader()
    
    print("\n=== Configuration Loader Test ===\n")
    
    # Test 1: Basic get
    print(f"Project name: {config.get('project.name')}")
    print(f"Database path: {config.get('database.path')}")
    
    # Test 2: Model paths
    print(f"\nEmotion model: {config.get_model_path('emotion')}")
    print(f"Custom YOLO: {config.get_model_path('custom_yolo')}")
    
    # Test 3: Cooldown windows
    print(f"\nCooldown for chip: {config.get_cooldown_window('chip')}s")
    print(f"Cooldown for nutella: {config.get_cooldown_window('nutella')}s")
    
    # Test 4: Health classification
    print(f"\nIs banana healthy? {config.is_healthy('banana')}")
    print(f"Is donut healthy? {config.is_healthy('donut')}")
    print(f"Banana calories: {config.get_calories('banana')}")
    
    # Test 5: UI colors
    print(f"\nPositive emotion color: {config.get_ui_color('positive')}")
    
    # Test 6: Nested values
    print(f"\nFrame skip (emotion): {config.get('detection.frame.skip_emotion')}")
    print(f"IOU threshold: {config.get('detection.fusion.iou_conflict_threshold')}")
    
    print("\n✅ Configuration loader test completed!")