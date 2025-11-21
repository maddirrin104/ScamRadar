"""
Model Loader
Loads MTL_MLP model at startup
"""
import os
import torch
import json
from typing import Dict, Any, Tuple, List
from app.services.model import MTL_MLP
from app.config import settings

# Global model instance
_model_instance = None
_account_feature_names = None
_transaction_feature_names = None

def load_model() -> Tuple[MTL_MLP, List[str], List[str]]:
    """
    Load model and feature names at startup
    Returns: (model, account_feature_names, transaction_feature_names)
    """
    global _model_instance, _account_feature_names, _transaction_feature_names
    
    if _model_instance is not None:
        return _model_instance, _account_feature_names, _transaction_feature_names
    
    # Define paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    MODEL_DIR = os.path.join(BASE_DIR, settings.model_dir)
    FEATURES_DIR = os.path.join(BASE_DIR, settings.features_dir)
    
    # Load model
    MODEL_PATH = os.path.join(MODEL_DIR, 'MTL_MLP_best.pth')
    
    if not os.path.exists(MODEL_PATH):
        # Try relative path from backend folder
        MODEL_PATH = os.path.join(os.path.dirname(BASE_DIR), 'models', 'MTL_MLP_best.pth')
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
    
    # Initialize model with correct architecture
    model = MTL_MLP(
        input_dim=15,
        shared_dim=128,
        head_hidden_dim=64
    )
    
    # Load model weights robustly
    ckpt = torch.load(MODEL_PATH, map_location=torch.device('cpu'))
    # support checkpoints that wrap state dict
    if isinstance(ckpt, dict):
        if 'state_dict' in ckpt:
            state = ckpt['state_dict']
        elif 'model_state_dict' in ckpt:
            state = ckpt['model_state_dict']
        else:
            state = ckpt
    else:
        state = ckpt
    
    # strip module prefix if present
    new_state = {}
    for k, v in state.items():
        new_k = k.replace('module.', '') if k.startswith('module.') else k
        new_state[new_k] = v
    
    model.load_state_dict(new_state)
    model.eval()
    
    # Load feature lists
    account_features_path = os.path.join(FEATURES_DIR, "AccountLevel_top15_features.json")
    transaction_features_path = os.path.join(FEATURES_DIR, "TransactionLevel_top15_features.json")
    
    # Try alternative paths
    if not os.path.exists(account_features_path):
        account_features_path = os.path.join(os.path.dirname(BASE_DIR), 'features', 'AccountLevel_top15_features.json')
    if not os.path.exists(transaction_features_path):
        transaction_features_path = os.path.join(os.path.dirname(BASE_DIR), 'features', 'TransactionLevel_top15_features.json')
    
    if not os.path.exists(account_features_path) or not os.path.exists(transaction_features_path):
        raise FileNotFoundError(f"Feature importance files not found: {account_features_path}, {transaction_features_path}")
    
    with open(account_features_path, "r") as f:
        ACCOUNT_FEATURES = json.load(f)
    
    with open(transaction_features_path, "r") as f:
        TRANSACTION_FEATURES = json.load(f)
    
    def _feature_name_list(feature_json):
        # Accept either list of strings or list of dicts with 'feature' key
        if not feature_json:
            return []
        if isinstance(feature_json[0], str):
            return feature_json
        elif isinstance(feature_json[0], dict) and 'feature' in feature_json[0]:
            return [f['feature'] for f in feature_json]
        else:
            # fallback: convert items to str
            return [str(f) for f in feature_json]
    
    ACCOUNT_FEATURE_NAMES = _feature_name_list(ACCOUNT_FEATURES)
    TRANSACTION_FEATURE_NAMES = _feature_name_list(TRANSACTION_FEATURES)
    
    _model_instance = model
    _account_feature_names = ACCOUNT_FEATURE_NAMES
    _transaction_feature_names = TRANSACTION_FEATURE_NAMES
    
    return model, ACCOUNT_FEATURE_NAMES, TRANSACTION_FEATURE_NAMES

def get_model() -> MTL_MLP:
    """Get the loaded model instance"""
    if _model_instance is None:
        load_model()
    return _model_instance

def get_feature_names() -> Tuple[List[str], List[str]]:
    """Get feature names"""
    if _account_feature_names is None or _transaction_feature_names is None:
        load_model()
    return _account_feature_names, _transaction_feature_names

