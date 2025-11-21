"""
Detection Service
Main service that orchestrates the detection flow:
1. Fetch data from Etherscan and Rarible APIs
2. Feature engineering
3. Model prediction
4. SHAP explanation
5. LLM explanation
"""
import torch
import numpy as np
import logging
from typing import Dict, Any, Optional, List
from app.services.etherscan_client import get_account_transactions
from app.services.rarible_client import enrich_transactions_with_nft_data, enrich_transaction_with_nft_data
from app.services.feature_engineer import extract_account_level_features, extract_transaction_level_features
from app.services.model_loader import get_model, get_feature_names
from app.services.shap_explainer import SHAPExplainer
from app.services.llm_explainer import LLMExplainer

logger = logging.getLogger(__name__)


class DetectionService:
    def __init__(self):
        logger.info("Initializing DetectionService components...")
        self.model = get_model()
        self.account_feature_names, self.transaction_feature_names = get_feature_names()
        logger.info(f"Loaded {len(self.account_feature_names)} account features, {len(self.transaction_feature_names)} transaction features")
        
        self.shap_explainer = SHAPExplainer(self.model, device="cpu")
        logger.info("SHAP explainer initialized")
        
        try:
            self.llm_explainer = LLMExplainer()
            logger.info("LLM explainer initialized successfully")
        except Exception as e:
            logger.warning(f"LLM explainer not available: {e}")
            self.llm_explainer = None
    
    async def detect_transaction(
        self,
        transaction_data: Dict[str, Any],
        explain: bool = False,
        explain_with_llm: bool = False
    ) -> Dict[str, Any]:
        """
        Detect phishing/scam activity for a single transaction
        
        Args:
            transaction_data: Transaction data with from_address, to_address, value, etc.
            explain: Include SHAP explanations
            explain_with_llm: Include LLM explanations
        
        Returns:
            Detection results for transaction-level only
        """
        # Enrich transaction with NFT data
        enriched_transaction = await enrich_transaction_with_nft_data(transaction_data)
        
        # Extract transaction-level features only
        transaction_features = extract_transaction_level_features([enriched_transaction])
        
        # Make prediction using transaction-level model only
        with torch.no_grad():
            transaction_features_tensor = torch.tensor(transaction_features, dtype=torch.float32).unsqueeze(0)
            transaction_logit = self.model(transaction_features_tensor, task_id='transaction').squeeze()
            transaction_prob = float(torch.sigmoid(transaction_logit).item())
        
        response = {
            "account_address": transaction_data.get("from_address", ""),
            "to_address": transaction_data.get("to_address", ""),
            "account_scam_probability": None,  # Not available for new accounts
            "transaction_scam_probability": transaction_prob,
            "transactions_count": 1,
            "detection_mode": "transaction_only"  # Indicate this is transaction-only detection
        }
        
        # Generate SHAP explanations if requested
        if explain or explain_with_llm:
            transaction_explanation = self.shap_explainer.explain_prediction(
                transaction_features.reshape(1, -1),
                'transaction',
                self.transaction_feature_names,
                apply_sigmoid=True
            )
            
            response["explanations"] = {
                "account": None,  # No account-level explanation
                "transaction": transaction_explanation
            }
            
            # Generate LLM explanations if requested
            if explain_with_llm and self.llm_explainer:
                try:
                    transaction_llm_explanation = await self.llm_explainer.explain_top_features(
                        transaction_prob,
                        "transaction",
                        transaction_explanation["feature_importance"],
                        max_words=100
                    )
                    
                    response["llm_explanations"] = {
                        "account": None,
                        "transaction": transaction_llm_explanation
                    }
                except Exception as e:
                    response["llm_explanations"] = {
                        "account": None,
                        "transaction": f"Failed to generate LLM explanation: {str(e)}"
                    }
        
        return response

    async def detect_account(
        self,
        account_address: str,
        explain: bool = False,
        explain_with_llm: bool = False,
        max_transactions: int = 1000
    ) -> Dict[str, Any]:
        """
        Main detection function for an account address
        
        Flow:
        1. Fetch transactions from Etherscan
        2. Enrich with NFT data from Rarible
        3. Extract features (account-level and transaction-level)
        4. Make predictions
        5. Generate SHAP explanations (if requested)
        6. Generate LLM explanations (if requested)
        """
        # Step 1: Fetch transactions from Etherscan
        transactions = await get_account_transactions(account_address, max_txns=max_transactions)
        
        if not transactions:
            # Return response indicating transaction-only mode should be used
            return {
                "account_address": account_address,
                "account_scam_probability": None,  # Not available
                "transaction_scam_probability": None,  # Need transaction data
                "transactions_count": 0,
                "detection_mode": "no_data",  # Indicate no data available
                "message": "No transactions found for this address. Please provide transaction data for transaction-level detection."
            }
        
        # Step 2: Enrich with NFT data from Rarible
        enriched_transactions = await enrich_transactions_with_nft_data(transactions)
        
        # Step 3: Extract features
        account_features = extract_account_level_features(account_address, enriched_transactions)
        transaction_features = extract_transaction_level_features(enriched_transactions)
        
        # Step 4: Make predictions
        with torch.no_grad():
            account_features_tensor = torch.tensor(account_features, dtype=torch.float32).unsqueeze(0)
            transaction_features_tensor = torch.tensor(transaction_features, dtype=torch.float32).unsqueeze(0)
            
            account_logit = self.model(account_features_tensor, task_id='account').squeeze()
            transaction_logit = self.model(transaction_features_tensor, task_id='transaction').squeeze()
            
            account_prob = float(torch.sigmoid(account_logit).item())
            transaction_prob = float(torch.sigmoid(transaction_logit).item())
        
        # Build response
        response = {
            "account_address": account_address,
            "account_scam_probability": account_prob,
            "transaction_scam_probability": transaction_prob,
            "transactions_count": len(enriched_transactions)
        }
        
        # Step 5: Generate SHAP explanations if requested
        if explain or explain_with_llm:
            account_explanation = self.shap_explainer.explain_prediction(
                account_features.reshape(1, -1),
                'account',
                self.account_feature_names,
                apply_sigmoid=True
            )
            
            transaction_explanation = self.shap_explainer.explain_prediction(
                transaction_features.reshape(1, -1),
                'transaction',
                self.transaction_feature_names,
                apply_sigmoid=True
            )
            
            response["explanations"] = {
                "account": account_explanation,
                "transaction": transaction_explanation
            }
            
            # Step 6: Generate LLM explanations if requested
            if explain_with_llm and self.llm_explainer:
                try:
                    account_llm_explanation = await self.llm_explainer.explain_top_features(
                        account_prob,
                        "account",
                        account_explanation["feature_importance"],
                        max_words=100
                    )
                    
                    transaction_llm_explanation = await self.llm_explainer.explain_top_features(
                        transaction_prob,
                        "transaction",
                        transaction_explanation["feature_importance"],
                        max_words=100
                    )
                    
                    response["llm_explanations"] = {
                        "account": account_llm_explanation,
                        "transaction": transaction_llm_explanation
                    }
                except Exception as e:
                    response["llm_explanations"] = {
                        "error": f"Failed to generate LLM explanations: {str(e)}"
                    }
        
        return response

