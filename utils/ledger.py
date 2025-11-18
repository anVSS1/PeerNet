import hashlib
import json
from datetime import datetime
from typing import Any, Dict

class LedgerHasher:
    """
    Utility class for calculating cryptographic hashes for ledger blocks.
    """

    @staticmethod
    def create_block_hash(previous_hash: str, timestamp: datetime, data: Dict[str, Any]) -> str:
        """
        Calculates the SHA-256 hash for a ledger block.
        """
        content = json.dumps({
            'previous_hash': previous_hash,
            'timestamp': timestamp.isoformat(), # Use ISO format for consistent string representation
            'data': data
        }, sort_keys=True, ensure_ascii=False) # sort_keys for consistent hash, ensure_ascii for non-ASCII chars
        return hashlib.sha256(content.encode('utf-8')).hexdigest()