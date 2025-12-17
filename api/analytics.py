'''
PeerNet++ Analytics API
=======================
REST API endpoints for platform analytics and statistics.

Endpoints:
- GET /analytics/overview: Platform-wide statistics
- GET /analytics/papers: Paper submission trends
- GET /analytics/reviews: Review quality metrics
- GET /analytics/reviewers: Reviewer performance stats
- GET /analytics/consensus: Decision distribution

Used by the Advanced Analytics dashboard.
'''

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from models.papers import Paper
from models.reviews import Review
from models.consensus import Consensus
from models.bias_flags import BiasFlag
from utils.logger import get_logger
import statistics

logger = get_logger(__name__)

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/dashboard', methods=['GET'])
def get_dashboard_analytics():
    """Get comprehensive analytics for dashboard."""
    try:
        # Time range filter
        days = int(request.args.get('days', 30))
        start_date = datetime.now() - timedelta(days=days)
        
        # Basic counts
        total_papers = Paper.objects().count()
        
        # Only count consensus records that have valid paper references
        reviewed_papers = 0
        valid_consensus_ids = []
        for consensus in Consensus.objects():
            try:
                if consensus.paper and consensus.paper.id:
                    reviewed_papers += 1
                    valid_consensus_ids.append(consensus.id)
            except Exception:
                # Skip orphaned consensus records
                continue
        
        pending_papers = max(0, total_papers - reviewed_papers)
        
        # Recent activity
        recent_papers = Paper.objects(created_at__gte=start_date).count()
        
        # Only count reviews for papers that still exist
        recent_reviews = 0
        for review in Review.objects(created_at__gte=start_date):
            try:
                if review.paper and review.paper.id:
                    recent_reviews += 1
            except Exception:
                continue
        
        # Review outcomes (only from valid consensus records)
        accepted = 0
        rejected = 0
        revisions = 0
        for consensus in Consensus.objects(id__in=valid_consensus_ids):
            decision = consensus.decision
            if decision == 'Accept':
                accepted += 1
            elif decision == 'Reject':
                rejected += 1
            else:
                revisions += 1
        
        # Average scores (only from valid consensus records)
        avg_scores = {}
        if valid_consensus_ids:
            scores_data = []
            for consensus in Consensus.objects(id__in=valid_consensus_ids):
                if consensus.final_scores:
                    scores_data.append(consensus.final_scores)
            
            if scores_data:
                for key in ['novelty', 'clarity', 'methodology', 'relevance', 'overall']:
                    values = [s.get(key, 0) for s in scores_data if s.get(key) and s.get(key) > 0]
                    avg_scores[key] = round(statistics.mean(values), 2) if values else 0
            else:
                # Default scores if no data
                for key in ['novelty', 'clarity', 'methodology', 'relevance', 'overall']:
                    avg_scores[key] = 0
        else:
            # Default scores if no valid consensus
            for key in ['novelty', 'clarity', 'methodology', 'relevance', 'overall']:
                avg_scores[key] = 0
        
        # Bias detection stats (only for valid papers)
        total_bias_flags = 0
        bias_types = {}
        for flag in BiasFlag.objects():
            try:
                # Check if the flag's paper still exists
                if flag.paper and flag.paper.id:
                    total_bias_flags += 1
                    flag_type = flag.flag_type
                    bias_types[flag_type] = bias_types.get(flag_type, 0) + 1
            except Exception:
                continue
        
        # Review time analysis (in minutes, more realistic for AI reviews)
        review_times = []
        for paper in Paper.objects():
            consensus = Consensus.objects(paper=paper).first()
            if consensus and consensus.created_at and paper.created_at:
                # Calculate time difference in minutes
                time_diff_minutes = (consensus.created_at - paper.created_at).total_seconds() / 60
                # Only include positive times less than 24 hours (1440 minutes)
                if 0 < time_diff_minutes < 1440:
                    review_times.append(time_diff_minutes)
        
        avg_review_time_minutes = round(statistics.mean(review_times), 1) if review_times else 0
        
        return jsonify({
            'summary': {
                'total_papers': total_papers,
                'reviewed_papers': reviewed_papers,
                'pending_papers': pending_papers,
                'completion_rate': round((reviewed_papers / total_papers * 100), 1) if total_papers > 0 else 0
            },
            'recent_activity': {
                'new_papers': recent_papers,
                'new_reviews': recent_reviews,
                'period_days': days
            },
            'outcomes': {
                'accepted': accepted,
                'rejected': rejected,
                'revisions': revisions,
                'acceptance_rate': round((accepted / reviewed_papers * 100), 1) if reviewed_papers > 0 else 0
            },
            'quality_metrics': {
                'average_scores': avg_scores,
                'average_review_time_minutes': avg_review_time_minutes
            },
            'bias_detection': {
                'total_flags': total_bias_flags,
                'flag_types': bias_types
            }
        })
    except Exception as e:
        logger.error(f"Error getting dashboard analytics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@analytics_bp.route('/trends', methods=['GET'])
def get_trends():
    """Get trend analysis over time."""
    try:
        # Get papers by month for the last 12 months
        monthly_data = {}
        for i in range(12):
            month_start = datetime.now().replace(day=1) - timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            month_key = month_start.strftime('%Y-%m')
            
            papers_count = Paper.objects(created_at__gte=month_start, created_at__lt=month_end).count()
            
            # Only count consensus records with valid paper references
            reviews_count = 0
            for consensus in Consensus.objects(created_at__gte=month_start, created_at__lt=month_end):
                try:
                    if consensus.paper and consensus.paper.id:
                        reviews_count += 1
                except Exception:
                    continue
            
            monthly_data[month_key] = {
                'papers': papers_count,
                'reviews': reviews_count
            }
        
        return jsonify({
            'monthly_trends': monthly_data,
            'generated_at': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting trends: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@analytics_bp.route('/performance', methods=['GET'])
def get_performance_metrics():
    """Get detailed performance metrics."""
    try:
        # Reviewer performance (only for reviews with valid papers)
        reviewer_stats = {}
        reviews = Review.objects()
        
        for review in reviews:
            try:
                # Only count reviews for papers that still exist
                if not (review.paper and review.paper.id):
                    continue
                    
                reviewer_id = review.reviewer_id
                if reviewer_id not in reviewer_stats:
                    reviewer_stats[reviewer_id] = {
                        'total_reviews': 0,
                        'avg_scores': {'overall': []},
                        'confidence_levels': []
                    }
                
                reviewer_stats[reviewer_id]['total_reviews'] += 1
                overall_score = review.scores.get('overall', 0) if review.scores else 0
                reviewer_stats[reviewer_id]['avg_scores']['overall'].append(overall_score)
                reviewer_stats[reviewer_id]['confidence_levels'].append(review.confidence or 0.5)
            except Exception:
                continue
        
        # Calculate averages
        for reviewer_id, stats in reviewer_stats.items():
            if stats['avg_scores']['overall']:
                stats['avg_overall_score'] = round(statistics.mean(stats['avg_scores']['overall']), 2)
                stats['avg_confidence'] = round(statistics.mean(stats['confidence_levels']), 2)
            del stats['avg_scores']
            del stats['confidence_levels']
        
        # System performance (in minutes)
        processing_times = []
        for consensus in Consensus.objects():
            try:
                # Safely access the referenced paper and its creation date
                if consensus.created_at and consensus.paper and consensus.paper.created_at:
                    time_diff_minutes = (consensus.created_at - consensus.paper.created_at).total_seconds() / 60
                    # Only include positive times less than 24 hours (1440 minutes)
                    if 0 < time_diff_minutes < 1440:
                        processing_times.append(time_diff_minutes)
            except Exception as e:
                # This will catch the DereferenceError if the paper is deleted
                logger.debug(f"Skipping consensus for analytics due to dereference error: {e}")
                continue
        
        avg_processing_time = statistics.mean(processing_times) if processing_times else 0
        
        # Count only valid reviews
        valid_reviews_count = 0
        for review in Review.objects():
            try:
                if review.paper and review.paper.id:
                    valid_reviews_count += 1
            except Exception:
                continue
        
        return jsonify({
            'reviewer_performance': reviewer_stats,
            'system_performance': {
                'avg_processing_time_minutes': round(avg_processing_time, 1),
                'total_reviews_completed': valid_reviews_count,
                'system_uptime_days': 30,  # Placeholder
                'papers_processed': len(processing_times)
            }
        })
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500