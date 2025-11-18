from typing import Dict, Any, List
import statistics
import logging
from agents.base_agent import BaseAgent
from config import Config

logger = logging.getLogger(__name__)

class ConsensusAgent(BaseAgent):
    def __init__(self, agent_id: str):
        super().__init__(agent_id, "Consensus_%s" % agent_id)
        self.max_rounds = 3  # Maximum negotiation rounds

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process reviews and reach consensus.
        input_data should contain 'reviews' key with list of review dicts.
        """
        try:
            reviews = input_data.get('reviews', [])
            paper = input_data.get('paper', {})
            
            if not reviews:
                return self._create_fallback_consensus("No reviews provided")

            # Sanitize reviews to ensure they have valid scores
            sanitized_reviews = self._sanitize_reviews(reviews)
            if not sanitized_reviews:
                return self._create_fallback_consensus("No valid reviews after sanitization")

            self.log_activity("Starting consensus for %d reviews" % len(sanitized_reviews))

            # Extract scores from reviews with error handling
            try:
                all_scores = [review.get('scores', {}) for review in sanitized_reviews]
                all_scores = [scores for scores in all_scores if scores]  # Filter empty scores
                
                if not all_scores:
                    return self._create_fallback_consensus("No valid scores found in reviews")
            except Exception as e:
                logger.error(f"Error extracting scores: {str(e)}")
                return self._create_fallback_consensus(f"Error extracting scores: {str(e)}")

            # Initial consensus attempt with error handling
            try:
                consensus_result = self._calculate_initial_consensus(all_scores)
            except Exception as e:
                logger.error(f"Error calculating initial consensus: {str(e)}")
                consensus_result = self._get_default_consensus()

            # Check for disagreements and negotiate if needed
            negotiation_rounds = []
            try:
                if self._has_disagreements(all_scores, consensus_result):
                    negotiation_rounds = self._negotiate_rounds(all_scores, consensus_result)
            except Exception as e:
                logger.error(f"Error in negotiation: {str(e)}")
                negotiation_rounds = []

            # Final decision with error handling
            try:
                final_decision = self._make_final_decision(consensus_result, negotiation_rounds)
            except Exception as e:
                logger.error(f"Error making final decision: {str(e)}")
                final_decision = self._get_default_decision(consensus_result)

            # Generate overall paper explanation
            try:
                overall_explanation = self._generate_llm_explanation(
                    paper, sanitized_reviews, final_decision
                )
            except Exception as e:
                logger.error(f"LLM explanation failed, using template: {str(e)}")
                overall_explanation = self._generate_template_explanation(
                    paper, sanitized_reviews, final_decision
                )

            result = {
                'decision': final_decision['decision'],
                'negotiation_rounds': negotiation_rounds,
                'final_scores': final_decision['scores'],
                'confidence': final_decision['confidence'],
                'overall_explanation': overall_explanation
            }

            self.log_activity("Consensus reached: %s" % final_decision['decision'])
            return result
            
        except Exception as e:
            logger.error(f"Critical error in consensus agent: {str(e)}")
            return self._create_fallback_consensus(f"Critical error: {str(e)}")

    def _calculate_initial_consensus(self, all_scores: List[Dict]) -> Dict:
        """
        Calculate initial consensus from all review scores.
        """
        criteria = ['novelty', 'clarity', 'methodology', 'relevance', 'overall']

        consensus_scores = {}
        for criterion in criteria:
            scores = [review[criterion] for review in all_scores if criterion in review]
            if scores:
                consensus_scores[criterion] = round(statistics.mean(scores), 2)

        return consensus_scores

    def _has_disagreements(self, all_scores: List[Dict], consensus: Dict, threshold: float = 2.0) -> bool:
        """
        Check if there are significant disagreements among reviewers.
        """
        for criterion in ['novelty', 'clarity', 'methodology', 'relevance', 'overall']:
            scores = [review.get(criterion, 0) for review in all_scores]
            if scores:
                score_range = max(scores) - min(scores)
                if score_range > threshold:
                    return True
        return False

    def _negotiate_rounds(self, all_scores: List[Dict], initial_consensus: Dict) -> List[Dict]:
        """
        Simulate negotiation rounds to resolve disagreements.
        """
        rounds = []
        current_consensus = initial_consensus.copy()

        for round_num in range(self.max_rounds):
            # Simple negotiation: move outlier scores toward consensus
            adjusted_scores = []
            for review in all_scores:
                adjusted_review = {}
                for criterion in ['novelty', 'clarity', 'methodology', 'relevance', 'overall']:
                    review_score = review.get(criterion, 0)
                    consensus_score = current_consensus.get(criterion, 5)

                    # Move 20% toward consensus
                    adjusted_score = review_score + 0.2 * (consensus_score - review_score)
                    adjusted_review[criterion] = round(adjusted_score, 2)

                adjusted_scores.append(adjusted_review)

            # Recalculate consensus
            new_consensus = self._calculate_initial_consensus(adjusted_scores)

            rounds.append({
                'round': round_num + 1,
                'adjusted_scores': adjusted_scores,
                'new_consensus': new_consensus
            })

            current_consensus = new_consensus

            # Check if agreement reached
            if not self._has_disagreements(adjusted_scores, new_consensus, threshold=1.0):
                break

        return rounds

    def _sanitize_reviews(self, reviews: List[Dict]) -> List[Dict]:
        """
        Sanitize reviews to ensure they have valid data.
        """
        sanitized = []
        for review in reviews:
            if not isinstance(review, dict):
                continue
            
            # Ensure scores exist and are valid
            scores = review.get('scores', {})
            if not isinstance(scores, dict):
                scores = self._get_default_scores()
            
            # Fill missing score fields
            default_scores = self._get_default_scores()
            for key in default_scores:
                if key not in scores or not isinstance(scores[key], (int, float)):
                    scores[key] = default_scores[key]
            
            sanitized_review = {
                'reviewer_id': review.get('reviewer_id', 'unknown'),
                'scores': scores,
                'written_feedback': review.get('written_feedback', 'No feedback provided'),
                'confidence': review.get('confidence', 0.5)
            }
            sanitized.append(sanitized_review)
        
        return sanitized
    
    def _get_default_scores(self) -> Dict[str, float]:
        """
        Return default scores.
        """
        return {
            'novelty': 6.0,
            'clarity': 6.0,
            'methodology': 6.0,
            'relevance': 6.0,
            'overall': 6.0
        }
    
    def _get_default_consensus(self) -> Dict[str, float]:
        """
        Return default consensus scores.
        """
        return self._get_default_scores()
    
    def _get_default_decision(self, consensus_scores: Dict) -> Dict:
        """
        Return default decision when decision making fails.
        """
        overall = consensus_scores.get('overall', 6.0)
        return {
            'decision': 'Minor Revision' if overall >= 6.0 else 'Major Revision',
            'scores': consensus_scores,
            'confidence': 0.6
        }
    
    def _generate_template_explanation(self, paper: Dict, reviews: List[Dict], decision: Dict) -> str:
        """
        Generate comprehensive overall explanation of the paper and decision.
        """
        try:
            title = paper.get('title', 'Unknown Title')
            authors = paper.get('authors', [])
            decision_type = decision.get('decision', 'Unknown')
            overall_score = decision.get('scores', {}).get('overall', 0)
            
            # Analyze review themes
            strengths = []
            weaknesses = []
            
            for review in reviews:
                scores = review.get('scores', {})
                feedback = review.get('written_feedback', '')
                
                # Identify strengths (scores >= 7)
                if scores.get('novelty', 0) >= 7:
                    strengths.append('novel contribution')
                if scores.get('clarity', 0) >= 7:
                    strengths.append('clear presentation')
                if scores.get('methodology', 0) >= 7:
                    strengths.append('sound methodology')
                if scores.get('relevance', 0) >= 7:
                    strengths.append('high relevance')
                
                # Identify weaknesses (scores < 6)
                if scores.get('novelty', 0) < 6:
                    weaknesses.append('limited novelty')
                if scores.get('clarity', 0) < 6:
                    weaknesses.append('unclear presentation')
                if scores.get('methodology', 0) < 6:
                    weaknesses.append('methodological concerns')
                if scores.get('relevance', 0) < 6:
                    weaknesses.append('questionable relevance')
            
            # Remove duplicates
            strengths = list(set(strengths))
            weaknesses = list(set(weaknesses))
            
            # Generate detailed explanation with specific recommendations
            if decision_type == 'Accept':
                explanation = f"**ACCEPTED PAPER ANALYSIS**\n\n"
                explanation += f"'{title}' by {', '.join(authors[:3]) if authors else 'the authors'} represents a strong contribution with an overall score of {overall_score}/10.\n\n"
                
                if strengths:
                    explanation += f"**KEY STRENGTHS:**\n• {' \n• '.join(strengths).replace('_', ' ').title()}\n\n"
                
                explanation += "**PUBLICATION READINESS:** This work meets all publication standards and demonstrates sufficient rigor, innovation, and clarity. The research makes a valuable contribution to the academic community and is ready for publication without major revisions."
                
            elif decision_type == 'Reject':
                explanation = f"**REJECTED PAPER ANALYSIS**\n\n"
                explanation += f"'{title}' by {', '.join(authors[:3]) if authors else 'the authors'} does not meet publication standards with a score of {overall_score}/10.\n\n"
                
                if weaknesses:
                    explanation += f"**CRITICAL ISSUES:**\n• {' \n• '.join(weaknesses).replace('_', ' ').title()}\n\n"
                
                explanation += "**RECOMMENDATIONS FOR FUTURE SUBMISSION:**\n"
                explanation += "• Conduct additional experiments to strengthen methodology\n"
                explanation += "• Improve theoretical framework and literature review\n"
                explanation += "• Enhance data analysis and statistical rigor\n"
                explanation += "• Clarify contribution and novelty claims\n"
                explanation += "• Consider collaboration with domain experts"
                
            else:  # Revision needed
                explanation = f"**REVISION REQUIRED ANALYSIS**\n\n"
                explanation += f"'{title}' by {', '.join(authors[:3]) if authors else 'the authors'} shows promise but needs revision (score: {overall_score}/10).\n\n"
                
                if strengths:
                    explanation += f"**EXISTING STRENGTHS:**\n• {' \n• '.join(strengths).replace('_', ' ').title()}\n\n"
                
                if weaknesses:
                    explanation += f"**AREAS FOR IMPROVEMENT:**\n• {' \n• '.join(weaknesses).replace('_', ' ').title()}\n\n"
                
                explanation += "**SPECIFIC REVISION RECOMMENDATIONS:**\n"
                if 'methodological concerns' in weaknesses:
                    explanation += "• Strengthen experimental design with additional controls\n"
                    explanation += "• Provide more detailed statistical analysis\n"
                if 'unclear presentation' in weaknesses:
                    explanation += "• Reorganize paper structure for better flow\n"
                    explanation += "• Improve figure quality and clarity\n"
                if 'limited novelty' in weaknesses:
                    explanation += "• Better articulate unique contributions\n"
                    explanation += "• Expand comparison with existing work\n"
                if 'questionable relevance' in weaknesses:
                    explanation += "• Strengthen discussion of practical implications\n"
                    explanation += "• Add real-world application examples\n"
                
                explanation += "\n**REVISION TIMELINE:** With focused improvements addressing these specific areas, this work has strong potential for acceptance."
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error generating overall explanation: {str(e)}")
            return f"**EVALUATION SUMMARY**\n\nThis paper has been evaluated by our AI review system and received a decision of {decision.get('decision', 'Unknown')} with an overall score of {decision.get('scores', {}).get('overall', 0)}/10.\n\n**NEXT STEPS:** Please refer to individual reviewer feedback for detailed analysis and specific recommendations for improvement."
    
    def _generate_llm_explanation(self, paper: Dict, reviews: List[Dict], decision: Dict) -> str:
        """
        Use Gemini to generate a nuanced, high-level explanation.
        """
        gemini_key = Config.GEMINI_API_KEY
        if not gemini_key:
            logger.warning("GEMINI_API_KEY not set. Falling back to template explanation.")
            return self._generate_template_explanation(paper, reviews, decision)

        import google.generativeai as genai
        genai.configure(api_key=gemini_key)
        model = genai.GenerativeModel(Config.GEMINI_MODEL)

        # Build a summary of all reviews
        review_summaries = []
        for i, review in enumerate(reviews):
            scores = review.get('scores', {})
            feedback_snippet = review.get('written_feedback', '')[:300] # Truncate for brevity
            summary = f"Reviewer {i+1} (Overall: {scores.get('overall')}/10):\n{feedback_snippet}...\n"
            review_summaries.append(summary)

        prompt = f"""
        As an Editor-in-Chief, your task is to write a final meta-review and decision letter for the authors.
        Synthesize the key points from the individual reviews provided below into a single, coherent, and constructive summary.

        **Paper Title:** {paper.get('title', 'N/A')}
        **Final Decision:** {decision.get('decision')}
        **Final Overall Score:** {decision.get('scores', {}).get('overall')}/10

        **Individual Review Summaries:**
        {'---'.join(review_summaries)}

        **Your Task:**
        Write a professional, high-level summary for the author. Do not just repeat the reviews.
        1.  **Start with the final decision** and the overall sentiment.
        2.  **Synthesize the major strengths** that the reviewers consistently identified.
        3.  **Synthesize the most critical weaknesses** or areas for improvement that were common across reviews.
        4.  **Provide actionable, high-level recommendations** for revision based on the weaknesses.
        5.  **Conclude with an encouraging and professional closing statement.**

        **IMPORTANT:** Do NOT include any placeholder text like "[Your Name]" or "[Your Contact Information]". Base your summary *only* on the paper title and the review summaries provided.
        Format the output in clear markdown.
        """

        try:
            response = model.generate_content(prompt)
            if response.text:
                return response.text.strip()
            else:
                logger.warning("Gemini returned an empty response. Falling back to template.")
                return self._generate_template_explanation(paper, reviews, decision)
        except ImportError:
            logger.error("Google Generative AI library not installed. Run: pip install google-generativeai")
            return self._generate_template_explanation(paper, reviews, decision)
        except Exception as e:
            logger.error(f"Error calling Gemini API for consensus explanation: {str(e)}")
            # On API error, use the reliable template-based method
            return self._generate_template_explanation(paper, reviews, decision)


    def _create_fallback_consensus(self, error_msg: str) -> Dict[str, Any]:
        """
        Create fallback consensus when processing fails.
        """
        default_scores = self._get_default_scores()
        return {
            'decision': 'Major Revision',
            'negotiation_rounds': [],
            'final_scores': default_scores,
            'confidence': 0.5,
            'overall_explanation': 'This paper requires revision based on preliminary analysis. Please review individual feedback for specific recommendations.'
        }

    def _make_final_decision(self, initial_consensus: Dict, negotiation_rounds: List[Dict]) -> Dict:
        """
        Make final accept/reject decision based on consensus scores.
        """
        try:
            # Use the final consensus from negotiations if they occurred
            final_scores = negotiation_rounds[-1]['new_consensus'] if negotiation_rounds else initial_consensus

            overall_score = final_scores.get('overall', 5)

            # Decision thresholds (configurable)
            if overall_score >= 7.5:
                decision = 'Accept'
            elif overall_score >= 6.0:
                decision = 'Minor Revision'
            elif overall_score >= 4.0:
                decision = 'Major Revision'
            else:
                decision = 'Reject'

            # Calculate confidence in decision
            try:
                score_values = [
                    final_scores.get('novelty', 5),
                    final_scores.get('clarity', 5),
                    final_scores.get('methodology', 5),
                    final_scores.get('relevance', 5)
                ]
                score_variance = statistics.variance(score_values) if len(score_values) > 1 else 0
                confidence = max(0.5, 1.0 - score_variance / 5.0)
            except Exception:
                confidence = 0.6  # Default confidence

            return {
                'decision': decision,
                'scores': final_scores,
                'confidence': round(confidence, 2)
            }
        except Exception as e:
            logger.error(f"Error in final decision making: {str(e)}")
            return self._get_default_decision(initial_consensus)
