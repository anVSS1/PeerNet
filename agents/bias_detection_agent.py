from typing import Dict, Any, List
import statistics
import logging
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class BiasDetectionAgent(BaseAgent):
    def __init__(self, agent_id: str):
        super().__init__(agent_id, "BiasDetector_%s" % agent_id)

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect potential biases in reviews.
        input_data should contain 'reviews' and 'paper' keys.
        """
        try:
            reviews = input_data.get('reviews', [])
            paper = input_data.get('paper', {})

            if not reviews:
                return {'bias_flags': [], 'total_flags': 0}

            # Sanitize reviews to ensure they have valid data
            sanitized_reviews = self._sanitize_reviews_for_bias(reviews)
            if not sanitized_reviews:
                return {'bias_flags': [], 'total_flags': 0}

            self.log_activity("Analyzing %d reviews for bias" % len(sanitized_reviews))

            bias_flags = []

            # Check for scoring outliers with error handling
            try:
                outlier_flags = self._detect_scoring_outliers(sanitized_reviews)
                bias_flags.extend(outlier_flags)
            except Exception as e:
                logger.error(f"Error detecting scoring outliers: {str(e)}")

            # Check for topic/affiliation bias with error handling
            try:
                topic_flags = self._detect_topic_bias(sanitized_reviews, paper)
                bias_flags.extend(topic_flags)
            except Exception as e:
                logger.error(f"Error detecting topic bias: {str(e)}")

            # Check for temporal bias with error handling
            try:
                temporal_flags = self._detect_temporal_bias(sanitized_reviews, paper)
                bias_flags.extend(temporal_flags)
            except Exception as e:
                logger.error(f"Error detecting temporal bias: {str(e)}")

            result = {
                'bias_flags': bias_flags,
                'total_flags': len(bias_flags)
            }

            self.log_activity("Detected %d potential bias flags" % len(bias_flags))
            return result
            
        except Exception as e:
            logger.error(f"Critical error in bias detection: {str(e)}")
            return {'bias_flags': [], 'total_flags': 0}

    def _sanitize_reviews_for_bias(self, reviews: List[Dict]) -> List[Dict]:
        """
        Sanitize reviews for bias detection.
        """
        sanitized = []
        for review in reviews:
            if not isinstance(review, dict):
                continue
            
            scores = review.get('scores', {})
            if not isinstance(scores, dict):
                continue
            
            # Ensure all required score fields exist
            required_fields = ['novelty', 'clarity', 'methodology', 'relevance', 'overall']
            valid_scores = {}
            for field in required_fields:
                score = scores.get(field)
                if isinstance(score, (int, float)) and 0 <= score <= 10:
                    valid_scores[field] = float(score)
                else:
                    valid_scores[field] = 6.0  # Default score
            
            sanitized_review = {
                'scores': valid_scores,
                'reviewer_id': review.get('reviewer_id', 'unknown')
            }
            sanitized.append(sanitized_review)
        
        return sanitized

    def _detect_scoring_outliers(self, reviews: List[Dict]) -> List[Dict]:
        """
        Detect reviews with outlier scores.
        """
        flags = []
        criteria = ['novelty', 'clarity', 'methodology', 'relevance', 'overall']

        try:
            for criterion in criteria:
                scores = []
                for review in reviews:
                    score = review.get('scores', {}).get(criterion)
                    if isinstance(score, (int, float)):
                        scores.append(float(score))

                if len(scores) < 3:
                    continue  # Need at least 3 scores for meaningful outlier detection

                try:
                    mean_score = statistics.mean(scores)
                    stdev_score = statistics.stdev(scores) if len(scores) > 1 else 0

                    for i, score in enumerate(scores):
                        if stdev_score > 0:
                            z_score = abs(score - mean_score) / stdev_score
                            if z_score > 2.0:  # More than 2 standard deviations
                                flags.append({
                                    'flag_type': 'scoring_outlier',
                                    'evidence': {
                                        'criterion': criterion,
                                        'reviewer_index': i,
                                        'score': score,
                                        'mean_score': round(mean_score, 2),
                                        'z_score': round(z_score, 2)
                                    },
                                    'confidence': min(0.9, z_score / 3.0)  # Higher z-score = higher confidence
                                })
                except Exception as e:
                    logger.error(f"Error calculating statistics for {criterion}: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error in outlier detection: {str(e)}")

        return flags

    def _detect_topic_bias(self, reviews: List[Dict], paper: Dict) -> List[Dict]:
        """
        Detect potential topic/affiliation bias.
        This is simplified - in practice would need reviewer expertise data.
        """
        flags = []

        try:
            # Safely get paper keywords
            paper_keywords = paper.get('keywords', []) if isinstance(paper, dict) else []
            if not isinstance(paper_keywords, list):
                paper_keywords = []
            
            sensitive_topics = ['controversial', 'political', 'ethical', 'bias']
            keywords_text = ' '.join(str(kw).lower() for kw in paper_keywords)

            if any(topic in keywords_text for topic in sensitive_topics):
                scores = []
                for review in reviews:
                    score = review.get('scores', {}).get('overall')
                    if isinstance(score, (int, float)):
                        scores.append(float(score))
                
                if len(scores) >= 3:
                    try:
                        score_range = max(scores) - min(scores)
                        if score_range > 3.0:  # Large disagreement on sensitive topic
                            flags.append({
                                'flag_type': 'topic_bias',
                                'evidence': {
                                    'paper_keywords': paper_keywords[:5],  # Limit keywords
                                    'score_range': round(score_range, 2),
                                    'min_score': min(scores),
                                    'max_score': max(scores)
                                },
                                'confidence': 0.7
                            })
                    except Exception as e:
                        logger.error(f"Error calculating score range: {str(e)}")
        except Exception as e:
            logger.error(f"Error in topic bias detection: {str(e)}")

        return flags

    def _detect_temporal_bias(self, reviews: List[Dict], paper: Dict) -> List[Dict]:
        """
        Detect potential temporal bias (e.g., recency bias).
        """
        flags = []

        try:
            paper_year = paper.get('year') if isinstance(paper, dict) else None
            if not paper_year:
                return flags

            try:
                paper_year = int(str(paper_year))
                current_year = 2024  # Would be dynamic in real implementation

                # Flag if paper is very recent and scores are unusually high/low
                if current_year - paper_year <= 1:  # Published this year or last
                    scores = []
                    for review in reviews:
                        score = review.get('scores', {}).get('novelty')
                        if isinstance(score, (int, float)):
                            scores.append(float(score))
                    
                    if scores:
                        try:
                            avg_novelty = statistics.mean(scores)
                            if avg_novelty > 8.0:  # Very high novelty for recent paper
                                flags.append({
                                    'flag_type': 'temporal_bias',
                                    'evidence': {
                                        'paper_year': paper_year,
                                        'avg_novelty_score': round(avg_novelty, 2),
                                        'reason': 'High novelty score for very recent publication'
                                    },
                                    'confidence': 0.6
                                })
                        except Exception as e:
                            logger.error(f"Error calculating average novelty: {str(e)}")

            except (ValueError, TypeError) as e:
                logger.error(f"Invalid year data: {str(e)}")
        except Exception as e:
            logger.error(f"Error in temporal bias detection: {str(e)}")

        return flags
