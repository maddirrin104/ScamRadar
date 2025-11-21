"""
LLM Explainer using Google Gemini API
Provides natural language explanations for model predictions based on SHAP values
"""
import google.generativeai as genai
from typing import Dict, List, Optional
from app.config import settings


class LLMExplainer:
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or settings.gemini_api_key
        if not api_key:
            raise ValueError("Gemini API key not provided")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
        
    def _translate_feature_name(self, name: str) -> str:
        """Translate technical feature names to human-readable descriptions"""
        translations = {
            "avg_gas_price": "average transaction fee",
            "activity_duration_days": "account age in days",
            "std_time_between_txns": "irregularity in transaction timing",
            "total_volume": "total amount transferred",
            "inNeighborNum": "number of unique senders",
            "total_txn": "total number of transactions",
            "in_out_ratio": "ratio of incoming to outgoing transactions",
            "total_value_in": "total amount received",
            "outNeighborNum": "number of unique recipients",
            "avg_gas_used": "average transaction complexity",
            "giftinTxn_ratio": "proportion of token transfers",
            "miningTxnNum": "number of mining transactions",
            "avg_value_out": "average amount sent",
            "turnover_ratio": "frequency of fund movements",
            "out_txn": "number of outgoing transactions",
            "gas_price": "transaction fee",
            "gas_used": "transaction complexity",
            "value": "transaction amount",
            "num_functions": "number of contract interactions",
            "has_suspicious_func": "presence of suspicious functions",
            "nft_num_owners": "number of NFT owners",
            "nft_total_sales": "total NFT sales volume",
            "token_value": "token transfer value",
            "nft_total_volume": "total NFT trading volume",
            "is_mint": "is a new token creation",
            "high_gas": "high transaction fee",
            "nft_average_price": "average NFT price",
            "nft_floor_price": "minimum NFT price",
            "nft_market_cap": "total NFT market value",
            "is_zero_value": "zero-value transaction"
        }
        return translations.get(name, name)
    
    def _format_features_for_prompt(self, features: List[Dict]) -> str:
        """Format feature importance data for the prompt"""
        formatted = []
        for f in features:
            feature_name = self._translate_feature_name(f["feature_name"])
            impact = "increasing risk" if f["shap_value"] > 0 else "decreasing risk"
            formatted.append(f"- {feature_name} (value={f['feature_value']:.2f}): {impact}, importance={abs(f['shap_value']):.4f}")
        return "\n".join(formatted)
    
    async def explain_top_features(self, 
                                   prediction_prob: float,
                                   task_type: str,
                                   top_features: List[Dict],
                                   max_words: int = 100) -> str:
        """
        Generate explanation for top 5 features using Gemini
        
        Args:
            prediction_prob: Model prediction probability (0-1)
            task_type: 'account' or 'transaction'
            top_features: List of top 5 features with shap_value and feature_value
            max_words: Maximum words in explanation (default 100)
        """
        risk_level = "HIGH RISK" if prediction_prob > 0.7 else ("MEDIUM RISK" if prediction_prob > 0.4 else "LOW RISK")
        
        prompt = f"""You are a Web3 security expert. Explain why these features are important for detecting {task_type}-level phishing/scam activities in a short, concise way (under {max_words} words).

PREDICTION: {prediction_prob:.2%} ({risk_level})

TOP 5 IMPORTANT FEATURES:
{self._format_features_for_prompt(top_features)}

Explain:
1. Why the most important feature (first one) is dangerous/suspicious
2. What these features indicate about potential scam activity
3. A brief risk assessment

Keep it concise and focused on practical implications. Maximum {max_words} words."""

        try:
            response = self.model.generate_content(prompt)
            explanation = response.text.strip()
            
            # Truncate if too long
            words = explanation.split()
            if len(words) > max_words:
                explanation = " ".join(words[:max_words]) + "..."
            
            return explanation
        except Exception as e:
            return f"Risk level: {risk_level} ({prediction_prob:.2%}). Top feature: {self._translate_feature_name(top_features[0]['feature_name'])} shows {'high risk' if top_features[0]['shap_value'] > 0 else 'low risk'} pattern. Error generating detailed explanation: {str(e)}"

