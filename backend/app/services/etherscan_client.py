"""
Etherscan API Client
Fetches transaction data from Etherscan API
"""
import itertools
import httpx
from typing import Optional, Dict, Any, List
from app.config import settings

_cycle = itertools.cycle(settings.etherscan_keys or [settings.etherscan_api_key])

async def etherscan_get(module: str, action: str, chainid: Optional[int] = None, **params) -> Dict[str, Any]:
    """Send GET request to Etherscan API v2
    
    Args:
        module: API module name
        action: API action name
        chainid: Chain ID (defaults to settings.etherscan_chainid, 1 for Ethereum mainnet, required for v2 API)
        **params: Additional parameters
    """
    if chainid is None:
        chainid = settings.etherscan_chainid
    key = next(_cycle) if settings.etherscan_keys else settings.etherscan_api_key
    q = {"module": module, "action": action, "apikey": key, "chainid": chainid, **params}
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get("https://api.etherscan.io/v2/api", params=q)
        r.raise_for_status()
        return r.json()

async def get_transaction_list(address: str, startblock: int = 0, endblock: int = 99999999, 
                              page: int = 1, offset: int = 100, sort: str = "desc", chainid: Optional[int] = None) -> Dict[str, Any]:
    """Get list of transactions for an address
    
    Args:
        address: Ethereum address
        startblock: Start block number
        endblock: End block number
        page: Page number
        offset: Number of transactions per page
        sort: Sort order (asc/desc)
        chainid: Chain ID (1 for Ethereum mainnet)
    """
    return await etherscan_get(
        "account",
        "txlist",
        chainid=chainid,
        address=address,
        startblock=startblock,
        endblock=endblock,
        page=page,
        offset=offset,
        sort=sort
    )

async def get_transaction_by_hash(tx_hash: str, chainid: Optional[int] = None) -> Dict[str, Any]:
    """Get transaction details by hash
    
    Args:
        tx_hash: Transaction hash
        chainid: Chain ID (1 for Ethereum mainnet)
    """
    result = await etherscan_get("proxy", "eth_getTransactionByHash", chainid=chainid, txhash=tx_hash)
    return result.get("result", {})

async def get_transaction_receipt(tx_hash: str, chainid: Optional[int] = None) -> Dict[str, Any]:
    """Get transaction receipt by hash
    
    Args:
        tx_hash: Transaction hash
        chainid: Chain ID (1 for Ethereum mainnet)
    """
    result = await etherscan_get("proxy", "eth_getTransactionReceipt", chainid=chainid, txhash=tx_hash)
    return result.get("result", {})

async def get_block_by_number(block_number: str, chainid: Optional[int] = None) -> Dict[str, Any]:
    """Get block details by number
    
    Args:
        block_number: Block number (hex string or "latest")
        chainid: Chain ID (1 for Ethereum mainnet)
    """
    result = await etherscan_get("proxy", "eth_getBlockByNumber", chainid=chainid, tag=block_number, boolean="false")
    return result.get("result", {})

def _hex_to_int(x: Optional[str]) -> int:
    """Convert hex string to int"""
    if not x:
        return 0
    try:
        return int(x, 16) if isinstance(x, str) and x.startswith("0x") else int(x)
    except Exception:
        return 0

# Function signature mapping (common NFT functions)
SIG_MAP = {
    "0x095ea7b3": "approve",
    "0xa22cb465": "setApprovalForAll",
    "0x23b872dd": "transferFrom",
    "0x42842e0e": "safeTransferFrom",
    "0xb88d4fde": "safeTransferFrom",
    "0xf242432a": "safeBatchTransferFrom",
    "0x8fcbaf0c": "permit",
}

def decode_function_name(input_data: Optional[str]) -> List[str]:
    """Decode function name from input data"""
    if not input_data or len(input_data) < 10:
        return []
    sel = input_data[:10].lower()
    name = SIG_MAP.get(sel)
    return [name] if name else []

async def get_account_transactions(address: str, max_txns: int = 1000, chainid: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Get all transactions for an account address and format them for model input
    
    Args:
        address: Ethereum address
        max_txns: Maximum number of transactions to fetch
        chainid: Chain ID (1 for Ethereum mainnet)
    """
    all_transactions = []
    page = 1
    offset = 100
    
    while len(all_transactions) < max_txns:
        result = await get_transaction_list(address, page=page, offset=offset, chainid=chainid)
        
        if result.get("status") != "1":
            break
            
        txns = result.get("result", [])
        if not txns or not isinstance(txns, list):
            break
            
        for txn in txns:
            if len(all_transactions) >= max_txns:
                break
                
            # Format transaction
            formatted_txn = {
                "from_address": (txn.get("from") or "").lower(),
                "to_address": (txn.get("to") or "").lower(),
                "value": _hex_to_int(txn.get("value")),
                "gasPrice": _hex_to_int(txn.get("gasPrice")),
                "gasUsed": _hex_to_int(txn.get("gasUsed", "0")),
                "timestamp": int(txn.get("timeStamp", 0)),
                "function_call": decode_function_name(txn.get("input")),
                "transaction_hash": txn.get("hash", ""),
                "blockNumber": _hex_to_int(txn.get("blockNumber")),
                "contract_address": (txn.get("to") or "").lower(),
                "token_value": 0,  # Will be enriched by Rarible API
                "token_decimal": 0,
                "nft_floor_price": 0,
                "nft_average_price": 0,
                "nft_total_volume": 0,
                "nft_total_sales": 0,
                "nft_num_owners": 0,
                "nft_market_cap": 0,
                "nft_7day_volume": 0,
                "nft_7day_sales": 0,
                "nft_7day_avg_price": 0,
                "tx_type": "erc721" if txn.get("input", "0x") != "0x" else "normal",
            }
            all_transactions.append(formatted_txn)
        
        if len(txns) < offset:
            break
            
        page += 1
    
    return all_transactions[:max_txns]

