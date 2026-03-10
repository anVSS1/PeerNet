'''
PeerNet++ Ledger API
====================
REST API endpoints for the immutable audit ledger.

Endpoints:
- GET /ledger/<paper_id>: Get all ledger entries for a paper

The ledger provides an immutable audit trail of all actions:
- Paper submissions
- Review generations
- Consensus decisions
- Plagiarism detections
- Status changes

Each entry is hashed and linked to the previous entry.
'''

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Blueprint, request, jsonify
from models.ledger_blocks import LedgerBlock
from models.papers import Paper
from utils.ledger import LedgerHasher
from utils.logger import get_logger
from utils.auth_middleware import get_current_user

logger = get_logger(__name__)

ledger_bp = Blueprint('ledger', __name__)

@ledger_bp.route('/<paper_id>', methods=['GET'])
def get_ledger(paper_id):
    """Get complete ledger audit trail for a specific paper."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    try:
        paper = Paper.objects(paper_id=paper_id, user_id=str(user.id)).first()
        if not paper:
            return jsonify({'error': 'Paper not found'}), 404

        blocks = LedgerBlock.objects(paper=paper).order_by('timestamp')

        # Run chain verification (auto-repair legacy blocks if needed)
        verification = LedgerHasher.verify_chain(paper)
        if not verification['valid'] and verification['total_blocks'] > 0:
            LedgerHasher.rehash_chain(paper)
            blocks = LedgerBlock.objects(paper=paper).order_by('timestamp')
            verification = LedgerHasher.verify_chain(paper)

        return jsonify({
            'paper_id': paper_id,
            'ledger_blocks': [block.to_dict() for block in blocks],
            'total_blocks': len(blocks),
            'chain_valid': verification['valid'],
            'verification': verification
        })
    except Exception as e:
        logger.error(f"Error getting ledger for paper {paper_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@ledger_bp.route('/<paper_id>/verify', methods=['GET'])
def verify_ledger(paper_id):
    """Verify the blockchain-style ledger integrity for a paper."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    try:
        paper = Paper.objects(paper_id=paper_id, user_id=str(user.id)).first()
        if not paper:
            return jsonify({'error': 'Paper not found'}), 404

        verification = LedgerHasher.verify_chain(paper)
        return jsonify({
            'paper_id': paper_id,
            'chain_valid': verification['valid'],
            'total_blocks': verification['total_blocks'],
            'checked': verification['checked'],
            'errors': verification['errors']
        })
    except Exception as e:
        logger.error(f"Error verifying ledger for paper {paper_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
