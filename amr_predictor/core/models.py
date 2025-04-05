"""
Model loading and management utilities for AMR Predictor.

This module provides functions for:
- Loading models and tokenizers
- Model configuration handling
- Inference utilities
"""

import os
from typing import Dict, Tuple, List, Optional, Any, Union
import logging
from pathlib import Path
import json
import gc
import time

from .utils import logger, timer, ProgressTracker

# Try to import necessary libraries, providing graceful fallbacks
try:
    import torch
    import transformers
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch/Transformers not available. Model loading functionality will be limited.")

try:
    from peft import PeftModel, PeftConfig
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False
    logger.warning("PEFT not available. Adapter model loading will be limited.")

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    logger.warning("python-dotenv not available. Environment variables may not be loaded properly.")


class ModelManager:
    """
    Manager class for handling model and tokenizer loading and configuration.
    """
    
    # Class constants
    DEFAULT_MODEL_NAME = "alakob/DraGNOME-2.5b-v1"
    CLASS_NAMES = ["Susceptible", "Resistant"]
    
    def __init__(self, model_name: Optional[str] = None, 
                 device: Optional[str] = None,
                 progress_tracker: Optional[ProgressTracker] = None):
        """
        Initialize the model manager.
        
        Args:
            model_name: HuggingFace model name or path to local model
            device: Device to load the model on ('cpu', 'cuda', 'cuda:0', etc.)
            progress_tracker: Optional progress tracker for loading operations
        """
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.device = device or self._get_default_device()
        self.model = None
        self.tokenizer = None
        self.progress_tracker = progress_tracker
        
        # Load environment variables from .env file
        if DOTENV_AVAILABLE:
            # Get the project root directory (where .env is located)
            project_root = Path(__file__).parent.parent.parent
            env_path = project_root / '.env'
            if env_path.exists():
                load_dotenv(env_path)
                logger.debug(f"Loaded environment variables from {env_path}")
            else:
                logger.warning(f"Environment file not found at {env_path}")
        
        # Get HuggingFace token from environment
        self.hf_token = os.getenv("HF_TOKEN")
        if not self.hf_token:
            logger.warning("HF_TOKEN not found in environment variables. Some models may require authentication.")
        else:
            logger.debug("Successfully loaded HuggingFace token from environment")
            
        # Set up HuggingFace token for transformers
        if self.hf_token:
            os.environ["HUGGING_FACE_HUB_TOKEN"] = self.hf_token
            logger.debug("Set HuggingFace token in environment")
            
            # Also set the token for the transformers library
            try:
                import huggingface_hub
                huggingface_hub.login(token=self.hf_token)
                logger.debug("Logged in to HuggingFace Hub")
            except Exception as e:
                logger.warning(f"Failed to login to HuggingFace Hub: {str(e)}")
    
    def _get_default_device(self) -> str:
        """Determine the default device to use based on availability"""
        if not TORCH_AVAILABLE:
            return "cpu"
        
        if torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"
    
    def clear_gpu_memory(self) -> None:
        """Clear GPU memory to prevent out-of-memory errors"""
        if not TORCH_AVAILABLE:
            return
            
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
            logger.debug("GPU memory cleared")
    
    def load(self) -> Tuple[Any, Any]:
        """
        Load the model and tokenizer.
        
        Returns:
            Tuple of (model, tokenizer)
        """
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch and Transformers are required for model loading")
            
        logger.info(f"Loading model from: {self.model_name}")
        
        # Clear GPU memory before loading
        self.clear_gpu_memory()
        
        try:
            # Load configuration
            logger.info(f"Loading model configuration from '{self.model_name}'")
            config = PeftConfig.from_pretrained(
                self.model_name,
                token=self.hf_token,
                trust_remote_code=True
            )
            
            # Load base model
            logger.info(f"Loading base model '{config.base_model_name_or_path}'")
            base_model = AutoModelForSequenceClassification.from_pretrained(
                config.base_model_name_or_path,
                num_labels=len(self.CLASS_NAMES),
                token=self.hf_token,
                trust_remote_code=True
            )
            
            # Load fine-tuned model with PEFT
            logger.info("Applying PEFT adaptations to model")
            self.model = PeftModel.from_pretrained(
                base_model,
                self.model_name,
                token=self.hf_token,
                trust_remote_code=True
            )
            
            # Load tokenizer
            logger.info("Loading tokenizer")
            self.tokenizer = AutoTokenizer.from_pretrained(
                config.base_model_name_or_path,
                token=self.hf_token,
                trust_remote_code=True
            )
            
            # Move model to specified device
            self.model.to(self.device)
            logger.info(f"Model moved to {self.device}")
            
            return self.model, self.tokenizer
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise
    
    def predict(self, sequences: List[str], max_length: int = 1000, 
                batch_size: int = 8) -> List[Dict[str, float]]:
        """
        Run prediction on a list of sequences.
        
        Args:
            sequences: List of sequences to predict
            max_length: Maximum sequence length for tokenization
            batch_size: Batch size for prediction
            
        Returns:
            List of prediction dictionaries with class probabilities
        """
        if not TORCH_AVAILABLE:
            logger.error("Cannot predict: PyTorch/Transformers not available")
            return []
        
        if self.model is None or self.tokenizer is None:
            logger.error("Model and tokenizer must be loaded before prediction")
            return []
        
        results = []
        total_sequences = len(sequences)
        
        try:
            # Set the model to evaluation mode
            self.model.eval()
            
            # Process in batches
            for i in range(0, total_sequences, batch_size):
                batch = sequences[i:i + batch_size]
                batch_size_actual = len(batch)
                
                if self.progress_tracker:
                    progress_percentage = (i / total_sequences) * 100
                    self.progress_tracker.update(
                        status=f"Processing batch {i//batch_size + 1}/{(total_sequences + batch_size - 1)//batch_size}",
                        additional_info={"processed": i, "total": total_sequences}
                    )
                
                # Tokenize the batch
                tokenize_start = time.time()
                inputs = self.tokenizer(
                    batch,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    max_length=max_length
                ).to(self.device)
                tokenize_time = time.time() - tokenize_start
                logger.debug(f"Tokenization completed in {tokenize_time:.2f} seconds")
                
                # Run inference
                inference_start = time.time()
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits = outputs.logits
                    probabilities = torch.nn.functional.softmax(logits, dim=1).cpu().numpy()
                inference_time = time.time() - inference_start
                logger.debug(f"Inference completed in {inference_time:.2f} seconds")
                
                # Convert predictions to the expected format
                for j in range(batch_size_actual):
                    prediction = {
                        self.CLASS_NAMES[c]: float(probabilities[j, c])
                        for c in range(len(self.CLASS_NAMES))
                    }
                    results.append(prediction)
            
            if self.progress_tracker:
                self.progress_tracker.update(
                    status="Prediction complete",
                    additional_info={"processed": total_sequences, "total": total_sequences}
                )
                
            return results
            
        except Exception as e:
            logger.error(f"Error during prediction: {str(e)}")
            if self.progress_tracker:
                self.progress_tracker.set_error(f"Prediction failed: {str(e)}")
            return []
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model.
        
        Returns:
            Dictionary with model information
        """
        info = {
            "model_name": self.model_name,
            "device": self.device,
            "is_loaded": self.model is not None and self.tokenizer is not None,
            "class_names": self.CLASS_NAMES
        }
        
        # Add additional information if available
        if TORCH_AVAILABLE and self.model is not None:
            info.update({
                "model_type": type(self.model).__name__,
                "parameter_count": sum(p.numel() for p in self.model.parameters()),
            })
            
            # Add GPU memory info if applicable
            if torch.cuda.is_available() and self.device.startswith("cuda"):
                gpu_id = 0 if self.device == "cuda" else int(self.device.split(":")[-1])
                if gpu_id < torch.cuda.device_count():
                    info.update({
                        "gpu_name": torch.cuda.get_device_name(gpu_id),
                        "gpu_memory_allocated": torch.cuda.memory_allocated(gpu_id) / (1024 ** 2),  # MB
                        "gpu_memory_reserved": torch.cuda.memory_reserved(gpu_id) / (1024 ** 2)  # MB
                    })
        
        return info
    
    def unload(self) -> None:
        """Unload the model and clear memory"""
        self.model = None
        self.tokenizer = None
        self.clear_gpu_memory()
        logger.info("Model unloaded and memory cleared")


# Standalone functions for backward compatibility

def load_model_and_tokenizer(model_name: str, device: Optional[str] = None) -> Tuple[Any, Any]:
    """
    Load a model and tokenizer. This is a standalone function for backward compatibility.
    
    Args:
        model_name: HuggingFace model name or path to local model
        device: Device to load the model on ('cpu', 'cuda')
        
    Returns:
        Tuple of (model, tokenizer)
    """
    manager = ModelManager(model_name=model_name, device=device)
    return manager.load()

def predict_amr(sequences: List[str], model: Any, tokenizer: Any, 
                device: str, max_length: int = 1000,
                metrics: Optional[Dict[str, float]] = None) -> List[Dict[str, float]]:
    """
    Predict antimicrobial resistance for sequences. This is a standalone function for backward compatibility.
    
    Args:
        sequences: List of sequences to predict
        model: The loaded model
        tokenizer: The loaded tokenizer
        device: Device to run inference on
        max_length: Maximum sequence length for tokenization
        metrics: Optional dictionary to store timing metrics
        
    Returns:
        List of prediction dictionaries with class probabilities
    """
    if not TORCH_AVAILABLE:
        logger.error("Cannot predict: PyTorch/Transformers not available")
        return []
    
    if model is None or tokenizer is None:
        logger.error("Model and tokenizer must be provided")
        return []
    
    # Create a manager with the provided model and tokenizer
    manager = ModelManager(device=device)
    manager.model = model
    manager.tokenizer = tokenizer
    
    # Use the manager's predict method
    with timer("predict_amr", metrics):
        return manager.predict(sequences, max_length=max_length)
