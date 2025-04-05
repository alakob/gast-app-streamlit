"""Model management for AMR Predictor."""

from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime

class ModelInfo(BaseModel):
    """Information about an AMR prediction model."""
    id: str
    name: str
    version: str
    description: str
    created_at: datetime
    updated_at: datetime
    supported_antibiotics: List[str]
    performance_metrics: Dict[str, float]
    requirements: Dict[str, str]

class ModelRegistry:
    """Registry for managing AMR prediction models."""
    
    _models: Dict[str, ModelInfo] = {}
    
    @classmethod
    def register_model(cls, model_info: ModelInfo) -> None:
        """Register a new model."""
        cls._models[model_info.id] = model_info
    
    @classmethod
    def get_model(cls, model_id: str) -> Optional[ModelInfo]:
        """Get model information by ID."""
        return cls._models.get(model_id)
    
    @classmethod
    def list_models(cls) -> List[ModelInfo]:
        """List all registered models."""
        return list(cls._models.values())
    
    @classmethod
    def update_model(cls, model_id: str, updates: Dict) -> Optional[ModelInfo]:
        """Update model information."""
        if model_id not in cls._models:
            return None
        
        model = cls._models[model_id]
        for key, value in updates.items():
            if hasattr(model, key):
                setattr(model, key, value)
        
        model.updated_at = datetime.utcnow()
        return model
    
    @classmethod
    def delete_model(cls, model_id: str) -> bool:
        """Delete a model from the registry."""
        if model_id in cls._models:
            del cls._models[model_id]
            return True
        return False

# Register default models
default_models = [
    ModelInfo(
        id="default",
        name="Default AMR Model",
        version="1.0.0",
        description="Default model for AMR prediction",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        supported_antibiotics=["amoxicillin", "ciprofloxacin", "tetracycline"],
        performance_metrics={
            "accuracy": 0.85,
            "precision": 0.82,
            "recall": 0.88,
            "f1_score": 0.85
        },
        requirements={
            "python": ">=3.8",
            "torch": ">=1.9.0",
            "transformers": ">=4.11.0"
        }
    ),
    ModelInfo(
        id="advanced",
        name="Advanced AMR Model",
        version="1.0.0",
        description="Advanced model with improved accuracy",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        supported_antibiotics=["amoxicillin", "ciprofloxacin", "tetracycline", "gentamicin"],
        performance_metrics={
            "accuracy": 0.90,
            "precision": 0.88,
            "recall": 0.92,
            "f1_score": 0.90
        },
        requirements={
            "python": ">=3.8",
            "torch": ">=1.9.0",
            "transformers": ">=4.11.0",
            "numpy": ">=1.19.0"
        }
    )
]

for model in default_models:
    ModelRegistry.register_model(model) 