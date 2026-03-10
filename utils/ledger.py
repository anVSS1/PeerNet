'''
PeerNet++ Ledger Utilities
==========================
Cryptographic hash utilities for the audit ledger.

The ledger uses SHA-256 hashing to create an immutable
chain of all review events, similar to a blockchain.

Each block contains:
- Previous block's hash (chain integrity)
- Timestamp
- Event data (review, consensus, bias flag)
'''

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

class LedgerHasher:
    """
    Utility class for calculating and verifying cryptographic hashes
    for the blockchain-style audit ledger.
    """

    @staticmethod
    def create_block_hash(previous_hash: str, timestamp: datetime, data: Dict[str, Any]) -> str:
        """
        Calculates the SHA-256 hash for a ledger block.

        Timestamps are truncated to millisecond precision to match
        MongoDB's BSON datetime storage.  This guarantees the hash
        computed at creation time is identical to the one recomputed
        after a round-trip through the database.
        """
        # Truncate microseconds → milliseconds (MongoDB precision)
        ts = timestamp.replace(microsecond=(timestamp.microsecond // 1000) * 1000)
        content = json.dumps({
            'previous_hash': previous_hash,
            'timestamp': ts.isoformat(),
            'data': data
        }, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @staticmethod
    def verify_block(block) -> Tuple[bool, str]:
        """
        Verify a single block's hash matches its contents.
        Returns (is_valid, reason).
        """
        expected_hash = LedgerHasher.create_block_hash(
            block.previous_hash, block.timestamp, block.data
        )
        if block.hash != expected_hash:
            return False, f"Hash mismatch: stored={block.hash[:16]}... expected={expected_hash[:16]}..."
        return True, "OK"

    @staticmethod
    def rehash_chain(paper) -> Dict[str, Any]:
        """
        Re-compute hashes for every block in a paper's ledger so the
        chain becomes valid.  Use this once after fixing the timestamp-
        precision bug to repair blocks that were hashed with
        microsecond timestamps before MongoDB truncated them.

        Returns:
            {'repaired': int, 'total': int}
        """
        from models.ledger_blocks import LedgerBlock

        blocks = list(LedgerBlock.objects(paper=paper).order_by('timestamp'))
        genesis_sentinel = '0' * 64
        repaired = 0

        for idx, block in enumerate(blocks):
            # Fix linkage first
            expected_prev = genesis_sentinel if idx == 0 else blocks[idx - 1].hash
            if block.previous_hash != expected_prev:
                block.previous_hash = expected_prev

            # Recompute hash with normalised timestamp
            new_hash = LedgerHasher.create_block_hash(
                block.previous_hash, block.timestamp, block.data
            )
            if block.hash != new_hash:
                block.hash = new_hash
                repaired += 1

            # Bypass the model's save() auto-hash logic by saving directly
            block.save()

        return {'repaired': repaired, 'total': len(blocks)}

    @staticmethod
    def verify_chain(paper) -> Dict[str, Any]:
        """
        Verify the entire ledger chain for a paper.

        Checks:
        1. Each block's hash matches a recompute of its contents.
        2. Each block's previous_hash links to the prior block's hash.
        3. The genesis block's previous_hash is the null sentinel (64 zeros).

        Returns a dict:
            {
                'valid': bool,
                'total_blocks': int,
                'checked': int,
                'errors': [{'block_index': int, 'block_id': str, 'error': str}, ...]
            }
        """
        from models.ledger_blocks import LedgerBlock  # avoid circular import

        blocks = list(LedgerBlock.objects(paper=paper).order_by('timestamp'))
        result: Dict[str, Any] = {
            'valid': True,
            'total_blocks': len(blocks),
            'checked': 0,
            'errors': []
        }

        if not blocks:
            return result  # empty chain is trivially valid

        genesis_sentinel = '0' * 64

        for idx, block in enumerate(blocks):
            block_id = str(block.id)

            # 1. Verify hash integrity
            is_valid, reason = LedgerHasher.verify_block(block)
            if not is_valid:
                result['valid'] = False
                result['errors'].append({'block_index': idx, 'block_id': block_id, 'error': reason})

            # 2. Verify chain linkage
            if idx == 0:
                if block.previous_hash != genesis_sentinel:
                    result['valid'] = False
                    result['errors'].append({
                        'block_index': idx,
                        'block_id': block_id,
                        'error': f"Genesis block previous_hash is not null sentinel"
                    })
            else:
                expected_prev = blocks[idx - 1].hash
                if block.previous_hash != expected_prev:
                    result['valid'] = False
                    result['errors'].append({
                        'block_index': idx,
                        'block_id': block_id,
                        'error': f"Chain break: previous_hash does not match prior block's hash"
                    })

            result['checked'] += 1

        logger.info("Ledger verification for paper %s: valid=%s, blocks=%d, errors=%d",
                    getattr(paper, 'paper_id', '?'), result['valid'], result['total_blocks'], len(result['errors']))
        return result