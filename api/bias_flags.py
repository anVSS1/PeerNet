import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Blueprint, request, jsonify
from models.bias_flags import BiasFlag
from models.papers import Paper
from utils.logger import get_logger

logger = get_logger(__name__)

bias_flags_bp = Blueprint('bias_flags', __name__)

@bias_flags_bp.route('/<paper_id>', methods=['GET'])
def get_bias_flags(paper_id):
    """Get bias flags for a specific paper."""
    try:
        paper = Paper.objects(paper_id=paper_id).first()
        if not paper:
            return jsonify({'error': 'Paper not found'}), 404

        flags = BiasFlag.objects(paper=paper)
        return jsonify({
            'paper_id': paper_id,
            'bias_flags': [flag.to_dict() for flag in flags],
            'count': len(flags)
        })
    except Exception as e:
        logger.error(f"Error getting bias flags for paper {paper_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
