import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Blueprint, request, jsonify
from data_collection.paper_intake import PaperIntake
from simulation.review_simulation import ReviewSimulation
from models.papers import Paper
from utils.logger import get_logger
from utils.auth_middleware import get_current_user
from extensions import socketio

logger = get_logger(__name__)

batch_bp = Blueprint('batch', __name__)

@batch_bp.route('', methods=['POST'])
def batch_upload():
    """Batch upload multiple papers."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = request.get_json()
        if not data or 'papers' not in data:
            return jsonify({'error': 'Missing papers data'}), 400

        num_reviewers = data.get('num_reviewers')
        custom_reviewer_ids = data.get('custom_reviewer_ids')

        intake = PaperIntake()
        results = []

        for paper_data in data['papers']:
            try:
                paper = intake.intake_single_paper(
                    paper_data.get('source', 'json'), paper_data.get('data', paper_data),
                    user_id=str(user.id), num_reviewers=num_reviewers, custom_reviewer_ids=custom_reviewer_ids
                )
                if paper:
                    results.append({
                        'paper_id': paper.paper_id,
                        'status': 'success',
                        'title': paper.title
                    })
                    # Emit real-time notification
                    try:
                        socketio.emit('upload_progress', {
                            'paper_id': paper.paper_id,
                            'paper_title': paper.title,
                            'message': f'Paper "{paper.title}" uploaded successfully',
                            'status': 'success'
                        }, room=str(user.id))
                    except Exception as e:
                        logger.debug(f"SocketIO notification failed: {str(e)}")
                else:
                    results.append({
                        'status': 'error',
                        'error': 'Failed to process paper'
                    })
            except Exception as e:
                logger.error(f"Error processing paper: {str(e)}")
                results.append({
                    'status': 'error',
                    'error': str(e)
                })

        successful = len([r for r in results if r['status'] == 'success'])
        return jsonify({
            'message': 'Batch processing completed',
            'results': results,
            'total_processed': len(results),
            'successful': successful,
            'failed': len(results) - successful
        })
    except Exception as e:
        logger.error(f"Error in batch upload: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@batch_bp.route('/review', methods=['POST'])
def batch_review():
    """Batch review multiple papers."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        if 'paper_ids' not in data:
            return jsonify({'error': 'Missing paper_ids'}), 400

        paper_ids = data['paper_ids']
        if not isinstance(paper_ids, list) or len(paper_ids) == 0:
            return jsonify({'error': 'paper_ids must be a non-empty list'}), 400

        results = []
        successful = 0

        for paper_id in paper_ids:
            try:
                # Fetch paper and verify ownership
                paper = Paper.objects(paper_id=paper_id, user_id=str(user.id)).first()
                if not paper:
                    results.append({
                        'paper_id': paper_id,
                        'status': 'error',
                        'error': 'Paper not found or access denied'
                    })
                    continue

                # Check if already reviewed - skip already reviewed papers
                from models.reviews import Review
                review_count = Review.objects(paper=paper).count()
                if review_count > 0:
                    results.append({
                        'paper_id': paper_id,
                        'status': 'skipped',
                        'message': 'Already reviewed',
                        'title': paper.title
                    })
                    continue

                # Emit start notification
                try:
                    socketio.emit('review_progress', {
                        'paper_id': paper_id,
                        'paper_title': paper.title,
                        'message': f'Starting review for "{paper.title}"',
                        'status': 'started'
                    }, room=str(user.id))
                except Exception as e:
                    logger.debug(f"SocketIO notification failed: {str(e)}")

                # Start review simulation
                simulation = ReviewSimulation(paper, user_id=str(user.id))
                reviews = simulation.run_simulation()

                if reviews and len(reviews) > 0:
                    results.append({
                        'paper_id': paper_id,
                        'status': 'success',
                        'title': paper.title,
                        'reviews_count': len(reviews)
                    })
                    successful += 1

                    # Emit completion notification
                    try:
                        socketio.emit('review_progress', {
                            'paper_id': paper_id,
                            'paper_title': paper.title,
                            'message': f'Review completed for "{paper.title}"',
                            'status': 'complete',
                            'reviews_count': len(reviews)
                        }, room=str(user.id))
                    except Exception as e:
                        logger.debug(f"SocketIO notification failed: {str(e)}")
                else:
                    results.append({
                        'paper_id': paper_id,
                        'status': 'error',
                        'error': 'Review generation failed'
                    })

            except Exception as e:
                logger.error(f"Error reviewing paper {paper_id}: {str(e)}")
                results.append({
                    'paper_id': paper_id,
                    'status': 'error',
                    'error': str(e)
                })

        # Emit batch completion notification
        try:
            socketio.emit('batch_progress', {
                'message': f'Batch review completed: {successful}/{len(paper_ids)} papers',
                'status': 'complete',
                'total': len(paper_ids),
                'successful': successful
            }, room=str(user.id))
        except Exception as e:
            logger.debug(f"SocketIO notification failed: {str(e)}")

        return jsonify({
            'success': True,
            'message': 'Batch review completed',
            'results': results,
            'total_processed': len(results),
            'successful': successful,
            'failed': len(results) - successful
        })

    except Exception as e:
        logger.error(f"Error in batch review: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500
