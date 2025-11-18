import requests
import random
from typing import Dict, Any, List
import logging
from agents.base_agent import BaseAgent
from config import Config

logger = logging.getLogger(__name__)

class ReviewerAgent(BaseAgent):
    def __init__(self, agent_id: str, expertise: List[str] = None, review_bias: str = 'balanced', personality_traits: Dict[str, float] = None):
        super().__init__(agent_id, f"Reviewer_{agent_id}")
        self.expertise = expertise or ['general']
        self.review_bias = review_bias
        self.personality_traits = personality_traits or {}
        self.hf_api_key = Config.HF_API_KEY
        self.hf_url = Config.HF_INFERENCE_URL

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a paper and generate review scores and feedback.
        input_data should contain 'paper' key with paper data.
        """
        try:
            paper = input_data.get('paper')
            if not paper:
                return self._create_fallback_review("No paper data provided")

            # Ensure paper has required fields with safe defaults
            paper = self._sanitize_paper_data(paper)
            
            self.log_activity("Starting review of paper: %s" % paper.get('title', 'Unknown'))

            # Generate scores with error handling
            try:
                scores = self._generate_scores(paper)
            except Exception as e:
                logger.error(f"Error generating scores: {str(e)}")
                scores = self._get_default_scores()

            # Generate written feedback with fallback
            try:
                written_feedback = self._generate_written_feedback(paper, scores)
            except Exception as e:
                logger.error(f"Error generating feedback: {str(e)}")
                written_feedback = self._generate_template_feedback(scores)

            # Calculate confidence with fallback
            try:
                confidence = self._calculate_confidence(paper, scores)
            except Exception as e:
                logger.error(f"Error calculating confidence: {str(e)}")
                confidence = 0.7  # Default confidence

            result = {
                'reviewer_id': self.agent_id,
                'scores': scores,
                'written_feedback': written_feedback,
                'confidence': confidence,
                'logs': f"Review completed by {self.name}"
            }

            self.log_activity("Review completed with overall score: %.2f" % scores.get('overall', 0))
            return result
            
        except Exception as e:
            logger.error(f"Critical error in reviewer {self.agent_id}: {str(e)}")
            return self._create_fallback_review(f"Critical error: {str(e)}")

    def _generate_scores(self, paper: Dict) -> Dict[str, float]:
        """
        Generate review scores based on paper content and reviewer expertise.
        """
        base_score = 7.0
        text_length = len(paper.get('abstract', '') + paper.get('full_text', ''))
        length_factor = min(text_length / 1000, 1.5)
        
        # Base variation
        variation = random.uniform(-0.8, 0.8)
        
        # Apply reviewer bias based on expertise
        bias_adjustments = self._get_bias_adjustments()
        
        novelty = min(max(base_score + variation + bias_adjustments['novelty'], 1), 10)
        clarity = min(max(base_score + variation + bias_adjustments['clarity'], 1), 10)
        methodology = min(max(base_score + variation + bias_adjustments['methodology'], 1), 10)
        relevance = min(max(base_score + variation + bias_adjustments['relevance'], 1), 10)

        overall = (novelty + clarity + methodology + relevance) / 4

        return {
            'novelty': round(novelty, 1),
            'clarity': round(clarity, 1),
            'methodology': round(methodology, 1),
            'relevance': round(relevance, 1),
            'overall': round(overall, 2)
        }
    
    def _get_bias_adjustments(self) -> Dict[str, float]:
        """Get scoring adjustments based on reviewer bias and personality traits."""
        adjustments = {'novelty': 0, 'clarity': 0, 'methodology': 0, 'relevance': 0}
        
        # Apply personality-based adjustments if available
        if self.personality_traits:
            # Strictness affects overall scores (negative adjustment)
            strictness = self.personality_traits.get('strictness', 0.5)
            strictness_adjustment = (strictness - 0.5) * -2.0  # Range: -1.0 to +1.0
            
            # Innovation bias affects novelty
            innovation_bias = self.personality_traits.get('innovation_bias', 0.5)
            adjustments['novelty'] = (innovation_bias - 0.5) * 2.0  # Range: -1.0 to +1.0
            
            # Writing standards affect clarity
            writing_standards = self.personality_traits.get('writing_standards', 0.5)
            adjustments['clarity'] = (writing_standards - 0.5) * 2.0
            
            # Methodology rigor affects methodology
            methodology_rigor = self.personality_traits.get('methodology_rigor', 0.5)
            adjustments['methodology'] = (methodology_rigor - 0.5) * 2.0
            
            # Detail focus affects all scores slightly
            detail_focus = self.personality_traits.get('detail_focus', 0.5)
            detail_adjustment = (detail_focus - 0.5) * -1.0  # More detail focus = stricter
            
            # Optimism affects all scores positively
            optimism = self.personality_traits.get('optimism', 0.5)
            optimism_adjustment = (optimism - 0.5) * 2.0  # Range: -1.0 to +1.0
            
            # Apply global adjustments
            for key in adjustments:
                adjustments[key] += strictness_adjustment + detail_adjustment + optimism_adjustment
        else:
            # Use default bias-based adjustments
            if self.review_bias == 'strict_methodology':
                adjustments['methodology'] = 1.0
                adjustments['novelty'] = -0.5
            elif self.review_bias == 'novelty_focused':
                adjustments['novelty'] = 1.2
                adjustments['methodology'] = -0.3
            elif self.review_bias == 'clarity_focused':
                adjustments['clarity'] = 1.0
                adjustments['relevance'] = 0.5
            elif self.review_bias == 'theory_heavy':
                adjustments['methodology'] = 0.8
                adjustments['relevance'] = 0.6
                adjustments['clarity'] = -0.2
            elif self.review_bias == 'application_focused':
                adjustments['relevance'] = 1.0
                adjustments['novelty'] = 0.3
                adjustments['methodology'] = -0.2
        
        return adjustments

    def _generate_written_feedback(self, paper: Dict, scores: Dict) -> str:
        """
        Generate written feedback using Gemini API.
        """
        gemini_key = Config.GEMINI_API_KEY
        if not gemini_key:
            return self._generate_template_feedback(scores)

        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel(Config.GEMINI_MODEL)
            
            prompt = self._build_prompt(paper, scores)
            response = model.generate_content(prompt)
            
            if response.text:
                return response.text.strip()
            else:
                return self._generate_template_feedback(scores)

        except ImportError:
            logger.error("Google Generative AI library not installed. Run: pip install google-generativeai")
            return self._generate_template_feedback(scores)
        except Exception as e:
            logger.error("Error calling Gemini API: %s", str(e))
            return self._generate_template_feedback(scores)

    def _build_prompt(self, paper: Dict, scores: Dict) -> str:
        """
        Build the prompt for the LLM based on reviewer expertise.
        """
        title = paper.get('title') or 'Unknown Title'
        abstract = paper.get('abstract') or 'No abstract available'
        if len(abstract) > 500:
            abstract = abstract[:500] + '...'
        
        # Customize prompt based on expertise
        expertise_focus = self._get_expertise_focus()
        expertise_list = ', '.join(self.expertise) if self.expertise else 'general academic review'
        
        prompt = f"""Act as an academic peer reviewer with expertise in {expertise_list}. 
        You tend to focus on {expertise_focus}. Write a concise, professional review in markdown format.

        **Paper Title:** {title}
        **Abstract:** {abstract}

        **Your Scores:**
        - Novelty: {scores['novelty']}/10
        - Clarity: {scores['clarity']}/10  
        - Methodology: {scores['methodology']}/10
        - Relevance: {scores['relevance']}/10
        - Overall: {scores['overall']}/10

        **Review:**

        **1. Summary:**
        Briefly summarize the paper's contribution.

        **2. Strengths:**
        - [List 2-3 key strengths]

        **3. Weaknesses:**
        - [List 2-3 key weaknesses]

        **4. Recommendation:**
        [State your recommendation: Accept, Minor Revision, Major Revision, Reject]
        """

        return prompt
    
    def _get_expertise_focus(self) -> str:
        """Get the focus area based on review bias."""
        focus_map = {
            'strict_methodology': 'rigorous experimental design and statistical validity',
            'novelty_focused': 'innovation and original contributions',
            'clarity_focused': 'clear communication and presentation quality',
            'theory_heavy': 'theoretical foundations and conceptual rigor',
            'application_focused': 'practical applications and real-world impact',
            'balanced': 'overall quality and contribution'
        }
        return focus_map.get(self.review_bias, 'overall quality')

    def _generate_template_feedback(self, scores: Dict) -> str:
        """
        Fallback template-based feedback reflecting reviewer expertise with detailed recommendations.
        """
        expertise_list = ', '.join(self.expertise) if self.expertise else 'general academic review'
        feedback = f"As a reviewer with expertise in {expertise_list}, I provide the following assessment:\n\n"
        
        # Detailed feedback based on scores
        novelty_score = scores.get('novelty', 5)
        clarity_score = scores.get('clarity', 5)
        methodology_score = scores.get('methodology', 5)
        relevance_score = scores.get('relevance', 5)
        overall_score = scores.get('overall', 5)
        
        # Novelty Assessment
        feedback += "**NOVELTY & CONTRIBUTION:**\n"
        if novelty_score >= 8:
            feedback += "• Excellent originality and significant contribution to the field\n"
            feedback += "• Novel approach that advances current understanding\n"
        elif novelty_score >= 6:
            feedback += "• Adequate novelty with some original elements\n"
            feedback += "• Contribution is meaningful but incremental\n"
        else:
            feedback += "• Limited novelty - appears to be incremental work\n"
            feedback += "• NEEDS: Clearer articulation of novel contributions\n"
            feedback += "• SUGGESTION: Compare more thoroughly with existing work\n"
        
        # Methodology Assessment
        feedback += "\n**METHODOLOGY & RIGOR:**\n"
        if methodology_score >= 8:
            feedback += "• Robust experimental design with appropriate controls\n"
            feedback += "• Sound statistical analysis and validation\n"
        elif methodology_score >= 6:
            feedback += "• Generally sound methodology with minor concerns\n"
            feedback += "• Adequate experimental setup\n"
        else:
            feedback += "• Significant methodological concerns identified\n"
            feedback += "• NEEDS: Stronger experimental design\n"
            feedback += "• SUGGESTION: Add control groups and validation studies\n"
            feedback += "• RECOMMENDATION: Improve statistical analysis approach\n"
        
        # Clarity Assessment
        feedback += "\n**PRESENTATION & CLARITY:**\n"
        if clarity_score >= 8:
            feedback += "• Exceptionally well-written and clearly presented\n"
            feedback += "• Logical flow and excellent organization\n"
        elif clarity_score >= 6:
            feedback += "• Generally clear presentation with good structure\n"
            feedback += "• Minor improvements needed in organization\n"
        else:
            feedback += "• Presentation needs significant improvement\n"
            feedback += "• NEEDS: Better organization and clearer writing\n"
            feedback += "• SUGGESTION: Restructure sections for better flow\n"
            feedback += "• RECOMMENDATION: Improve figures and tables clarity\n"
        
        # Relevance Assessment
        feedback += "\n**RELEVANCE & IMPACT:**\n"
        if relevance_score >= 8:
            feedback += "• Highly relevant with clear practical implications\n"
            feedback += "• Strong potential for real-world impact\n"
        elif relevance_score >= 6:
            feedback += "• Good relevance to the field\n"
            feedback += "• Adequate discussion of implications\n"
        else:
            feedback += "• Limited relevance or unclear applications\n"
            feedback += "• NEEDS: Better justification of practical importance\n"
            feedback += "• SUGGESTION: Expand discussion of real-world applications\n"
        
        # Overall Recommendation
        feedback += "\n**OVERALL RECOMMENDATION:**\n"
        if overall_score >= 7.5:
            feedback += f"• ACCEPT - Strong paper with overall score {overall_score}/10\n"
            feedback += "• Meets publication standards across all criteria\n"
        elif overall_score >= 6.0:
            feedback += f"• MINOR REVISION - Good work needing refinement (score: {overall_score}/10)\n"
            feedback += "• Address the specific suggestions above\n"
            feedback += "• Paper has potential with targeted improvements\n"
        else:
            feedback += f"• MAJOR REVISION/REJECT - Significant issues (score: {overall_score}/10)\n"
            feedback += "• Multiple fundamental concerns need addressing\n"
            feedback += "• Consider substantial restructuring and additional work\n"
        
        return feedback

    def _sanitize_paper_data(self, paper: Dict) -> Dict:
        """
        Ensure paper data has all required fields with safe defaults.
        """
        sanitized = {
            'title': paper.get('title') or 'Unknown Title',
            'abstract': paper.get('abstract') or 'No abstract available',
            'authors': paper.get('authors') or ['Unknown Author'],
            'year': paper.get('year') or 'Unknown',
            'doi': paper.get('doi') or '',
            'full_text': paper.get('full_text') or '',
            'keywords': paper.get('keywords') or [],
            'source': paper.get('source') or 'unknown'
        }
        return sanitized
    
    def _get_default_scores(self) -> Dict[str, float]:
        """
        Return default scores when scoring fails.
        """
        return {
            'novelty': 6.0,
            'clarity': 6.0,
            'methodology': 6.0,
            'relevance': 6.0,
            'overall': 6.0
        }
    
    def _create_fallback_review(self, error_msg: str) -> Dict[str, Any]:
        """
        Create a fallback review when processing fails.
        """
        scores = self._get_default_scores()
        return {
            'reviewer_id': self.agent_id,
            'scores': scores,
            'written_feedback': f'Review could not be completed due to technical issues. {error_msg}. Default assessment provided.',
            'confidence': 0.5,
            'logs': f'Fallback review generated by {self.name} due to error: {error_msg}'
        }

    def _calculate_confidence(self, paper: Dict, scores: Dict) -> float:
        """
        Calculate confidence in the review.
        """
        try:
            # Simple confidence calculation based on score consistency
            score_values = [scores.get(k, 6.0) for k in ['novelty', 'clarity', 'methodology', 'relevance']]
            overall = scores.get('overall', 6.0)
            variance = sum((x - overall) ** 2 for x in score_values) / len(score_values)
            confidence = max(0.5, 1.0 - variance / 10.0)  # Higher variance = lower confidence
            return round(confidence, 2)
        except Exception:
            return 0.7  # Default confidence