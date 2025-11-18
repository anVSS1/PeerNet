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
        reviewed_papers = Consensus.objects().count()
        pending_papers = total_papers - reviewed_papers
        
        # Recent activity
        recent_papers = Paper.objects(created_at__gte=start_date).count()
        recent_reviews = Review.objects(created_at__gte=start_date).count()
        
        # Review outcomes
        decisions = Consensus.objects()
        accepted = decisions.filter(decision='Accept').count()
        rejected = decisions.filter(decision='Reject').count()
        revisions = decisions.count() - accepted - rejected
        
        # Average scores
        all_consensus = list(Consensus.objects())
        avg_scores = {}
        if all_consensus:
            scores_data = [c.final_scores for c in all_consensus if c.final_scores]
            if scores_data:
                for key in ['novelty', 'clarity', 'methodology', 'relevance', 'overall']:
                    values = [s.get(key, 0) for s in scores_data if s.get(key)]
                    avg_scores[key] = round(statistics.mean(values), 2) if values else 0
        
        # Bias detection stats
        total_bias_flags = BiasFlag.objects().count()
        bias_types = {}
        for flag in BiasFlag.objects():
            flag_type = flag.flag_type
            bias_types[flag_type] = bias_types.get(flag_type, 0) + 1
        
        # Review time analysis
        review_times = []
        for paper in Paper.objects():
            consensus = Consensus.objects(paper=paper).first()
            if consensus and paper.created_at:
                time_diff = (consensus.created_at - paper.created_at).total_seconds() / 3600
                review_times.append(time_diff)
        
        avg_review_time = round(statistics.mean(review_times), 2) if review_times else 0
        
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
                'average_review_time_hours': avg_review_time
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
            reviews_count = Consensus.objects(created_at__gte=month_start, created_at__lt=month_end).count()
            
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
        # Reviewer performance (simulated since we don't track individual reviewers)
        reviewer_stats = {}
        reviews = Review.objects()
        
        for review in reviews:
            reviewer_id = review.reviewer_id
            if reviewer_id not in reviewer_stats:
                reviewer_stats[reviewer_id] = {
                    'total_reviews': 0,
                    'avg_scores': {'overall': []},
                    'confidence_levels': []
                }
            
            reviewer_stats[reviewer_id]['total_reviews'] += 1
            reviewer_stats[reviewer_id]['avg_scores']['overall'].append(review.scores.get('overall', 0))
            reviewer_stats[reviewer_id]['confidence_levels'].append(review.confidence or 0.5)
        
        # Calculate averages
        for reviewer_id, stats in reviewer_stats.items():
            if stats['avg_scores']['overall']:
                stats['avg_overall_score'] = round(statistics.mean(stats['avg_scores']['overall']), 2)
                stats['avg_confidence'] = round(statistics.mean(stats['confidence_levels']), 2)
            del stats['avg_scores']
            del stats['confidence_levels']
        
        # System performance
        processing_times = []
        for consensus in Consensus.objects():
            try:
                # Safely access the referenced paper and its creation date
                if consensus.created_at and consensus.paper and consensus.paper.created_at:
                    time_diff_hours = (consensus.created_at - consensus.paper.created_at).total_seconds() / 3600
                    if time_diff_hours >= 0: # Ensure no negative times
                        processing_times.append(time_diff_hours)
            except Exception as e:
                # This will catch the DereferenceError if the paper is deleted
                logger.debug(f"Skipping consensus for analytics due to dereference error: {e}")
                continue
        
        avg_processing_time = statistics.mean(processing_times) if processing_times else 0
        
        return jsonify({
            'reviewer_performance': reviewer_stats,
            'system_performance': {
                'avg_processing_time_hours': round(avg_processing_time, 2),
                'total_reviews_completed': Review.objects().count(),
                'system_uptime_days': 30,  # Placeholder
                'papers_processed': len(processing_times)
            }
        })
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500