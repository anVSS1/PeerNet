import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Blueprint, jsonify
from models.reviews import Review
from models.papers import Paper
from utils.logger import get_logger

logger = get_logger(__name__)

reviews_bp = Blueprint('reviews', __name__)

@reviews_bp.route('/<paper_id>', methods=['GET'])
def get_reviews(paper_id):
    """Get all reviews for a specific paper."""
    try:
        paper = Paper.objects(paper_id=paper_id).first()
        if not paper:
            return jsonify({'error': 'Paper not found'}), 404

        reviews = Review.objects(paper=paper)
        return jsonify({
            'paper_id': paper_id,
            'reviews': [review.to_dict() for review in reviews],
            'count': len(reviews)
        })
    except Exception as e:
        logger.error(f"Error getting reviews for paper {paper_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
