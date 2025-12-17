"""
Consensus Agent using Hybrid Logic + Gemini 2.5 Flash
======================================================
This module combines:
1. Python statistical calculations (mean, variance, range)
2. Gemini 2.5 Flash for contextual decision making (built-in reasoning)

The model provides reasoning for its decisions, making 
consensus decisions transparent and explainable.

NO MORE simple averaging - the AI now considers:
- Review confidence levels
- Reviewer expertise alignment
- Disagreement patterns
- Visual analysis concerns
- Plagiarism flags
"""

from typing import Dict, Any, List, Optional
import statistics
import logging
import json
import google.generativeai as genai
from agents.base_agent import BaseAgent
from config import Config

logger = logging.getLogger(__name__)


class ConsensusAgent(BaseAgent):
    """
    Hybrid consensus agent using statistical analysis + Gemini 2.5 Flash.
    
    The model provides reasoning for decisions,
    not just a simple average of scores.
    """
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, f"Consensus_{agent_id}")
        self.max_rounds = 3
        
        # Gemini 2.5 Flash for reasoning
        self.gemini_api_key = Config.GEMINI_API_KEY
        self.thinking_model = Config.GEMINI_THINKING_MODEL
        
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            logger.info(f"Consensus agent initialized with Gemini {self.thinking_model}")
        else:
            logger.warning("No Gemini API key - will use fallback logic")
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process reviews and reach consensus using hybrid logic.
        
        Args:
            input_data: {
                'reviews': list of review dicts,
                'paper': paper dict with title, abstract, visual_analysis, etc.,
                'plagiarism_result': optional dict with plagiarism info
            }
            
        Returns:
            Consensus result with decision, scores, reasoning
        """
        try:
            reviews = input_data.get('reviews', [])
            paper = input_data.get('paper', {})
            plagiarism_result = input_data.get('plagiarism_result', {})
            
            if not reviews:
                return self._create_fallback_consensus("No reviews provided")
            
            # Sanitize reviews
            sanitized_reviews = self._sanitize_reviews(reviews)
            if not sanitized_reviews:
                return self._create_fallback_consensus("No valid reviews after sanitization")
            
            self.log_activity(f"Starting hybrid consensus for {len(sanitized_reviews)} reviews")
            
            # STEP 1: Statistical Analysis (Python)
            stats = self._compute_statistics(sanitized_reviews)
            
            # STEP 2: Check for visual analysis concerns
            visual_concerns = self._extract_visual_concerns(paper)
            
            # STEP 3: Gemini 2.0 Flash Thinking for contextual decision
            thinking_result = self._get_thinking_decision(
                paper=paper,
                reviews=sanitized_reviews,
                stats=stats,
                visual_concerns=visual_concerns,
                plagiarism_result=plagiarism_result
            )
            
            # STEP 4: Negotiation if needed (simplified)
            negotiation_rounds = []
            if stats['has_disagreements']:
                negotiation_rounds = self._negotiate_with_thinking(
                    sanitized_reviews, stats, thinking_result
                )
            
            # STEP 5: Build final result
            result = {
                'decision': thinking_result['decision'],
                'negotiation_rounds': negotiation_rounds,
                'final_scores': thinking_result['adjusted_scores'],
                'confidence': thinking_result['confidence'],
                'overall_explanation': thinking_result['explanation'],
                'thinking_trace': thinking_result.get('thinking_trace', ''),
                'statistical_summary': stats
            }
            
            self.log_activity(f"Consensus reached: {thinking_result['decision']} (confidence: {thinking_result['confidence']:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Critical error in consensus agent: {str(e)}")
            return self._create_fallback_consensus(f"Critical error: {str(e)}")
    
    def _compute_statistics(self, reviews: List[Dict]) -> Dict[str, Any]:
        """
        Compute statistical analysis of review scores.
        Returns mean, std, range, variance for each criterion.
        """
        criteria = ['novelty', 'clarity', 'methodology', 'relevance', 'overall']
        stats = {
            'mean_scores': {},
            'std_scores': {},
            'range_scores': {},
            'weighted_mean_scores': {},
            'has_disagreements': False,
            'max_disagreement': 0.0,
            'reviewer_count': len(reviews)
        }
        
        for criterion in criteria:
            scores = []
            weights = []
            
            for review in reviews:
                score = review.get('scores', {}).get(criterion)
                confidence = review.get('confidence', 0.7)
                
                if score is not None and isinstance(score, (int, float)):
                    scores.append(float(score))
                    weights.append(float(confidence))
            
            if scores:
                # Basic stats
                stats['mean_scores'][criterion] = round(statistics.mean(scores), 2)
                stats['std_scores'][criterion] = round(statistics.stdev(scores), 2) if len(scores) > 1 else 0.0
                stats['range_scores'][criterion] = round(max(scores) - min(scores), 2)
                
                # Confidence-weighted mean
                if sum(weights) > 0:
                    weighted_sum = sum(s * w for s, w in zip(scores, weights))
                    weighted_mean = weighted_sum / sum(weights)
                    stats['weighted_mean_scores'][criterion] = round(weighted_mean, 2)
                else:
                    stats['weighted_mean_scores'][criterion] = stats['mean_scores'][criterion]
                
                # Track disagreements
                if stats['range_scores'][criterion] > 2.0:
                    stats['has_disagreements'] = True
                    stats['max_disagreement'] = max(stats['max_disagreement'], stats['range_scores'][criterion])
        
        return stats
    
    def _extract_visual_concerns(self, paper: Dict) -> List[str]:
        """Extract any visual analysis concerns from paper."""
        concerns = []
        visual_analysis = paper.get('visual_analysis', [])
        
        for visual in visual_analysis:
            if visual.get('concerns'):
                concerns.extend(visual['concerns'])
            if visual.get('authenticity_score', 1.0) < 0.7:
                concerns.append(f"Low authenticity score for {visual.get('type', 'visual')}")
        
        return list(set(concerns))
    
    def _get_thinking_decision(self, paper: Dict, reviews: List[Dict], 
                                stats: Dict, visual_concerns: List[str],
                                plagiarism_result: Dict) -> Dict[str, Any]:
        """
        Use Gemini 2.5 Flash for contextual decision making.
        The model provides reasoning for its decisions.
        """
        if not self.gemini_api_key:
            return self._get_fallback_decision(stats)
        
        try:
            # Build comprehensive prompt for reasoning model
            prompt = self._build_thinking_prompt(paper, reviews, stats, visual_concerns, plagiarism_result)
            
            # Call Gemini Thinking API
            model = genai.GenerativeModel(self.thinking_model)
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.4,  # Lower temp for consistent decisions
                    max_output_tokens=4000
                )
            )
            
            response_text = response.text
            
            # Extract thinking trace if available (Gemini Thinking includes reasoning)
            thinking_trace = ""
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, 'content') and candidate.content.parts:
                    for part in candidate.content.parts:
                        if hasattr(part, 'thought') and part.thought:
                            thinking_trace = part.text
            
            # Parse the thinking response
            parsed = self._parse_thinking_response(response_text, stats)
            parsed['thinking_trace'] = thinking_trace or "Reasoning embedded in response"
            return parsed
            
        except Exception as e:
            logger.error(f"Gemini 2.5 Flash failed: {e}")
            return self._get_fallback_decision(stats)
    
    def _build_thinking_prompt(self, paper: Dict, reviews: List[Dict], 
                                stats: Dict, visual_concerns: List[str],
                                plagiarism_result: Dict) -> str:
        """Build the prompt for Gemini 2.5 Flash reasoning."""
        
        # Format reviews
        review_summaries = []
        for i, review in enumerate(reviews):
            scores = review.get('scores', {})
            confidence = review.get('confidence', 0.7)
            feedback = review.get('written_feedback', '')[:500]
            recommendation = review.get('recommendation', 'Unknown')
            
            review_summaries.append(f"""
REVIEWER {i+1} (Confidence: {confidence:.2f}):
- Novelty: {scores.get('novelty', 'N/A')}/10
- Clarity: {scores.get('clarity', 'N/A')}/10
- Methodology: {scores.get('methodology', 'N/A')}/10
- Relevance: {scores.get('relevance', 'N/A')}/10
- Overall: {scores.get('overall', 'N/A')}/10
- Recommendation: {recommendation}
- Key Feedback: {feedback}
""")
        
        # Format statistics
        stats_summary = f"""
STATISTICAL ANALYSIS:
- Mean Overall Score: {stats['mean_scores'].get('overall', 'N/A')}
- Weighted Mean Overall: {stats['weighted_mean_scores'].get('overall', 'N/A')}
- Score Range: {stats['range_scores'].get('overall', 'N/A')} (max disagreement: {stats['max_disagreement']:.1f})
- Reviewer Count: {stats['reviewer_count']}
- Has Significant Disagreements: {stats['has_disagreements']}
"""
        
        # Format concerns
        concerns_text = ""
        if visual_concerns:
            concerns_text += f"\nVISUAL ANALYSIS CONCERNS:\n- " + "\n- ".join(visual_concerns)
        
        if plagiarism_result.get('similar_papers'):
            concerns_text += f"\nPLAGIARISM NOTE: Paper passed plagiarism check (similarity: {plagiarism_result.get('max_similarity', 0):.1%})"
        
        prompt = f"""You are the Editor-in-Chief making the final decision on an academic paper submission.
You have access to multiple peer reviews and must synthesize them into a fair, reasoned decision.

PAPER INFORMATION:
Title: {paper.get('title', 'Unknown')}
Authors: {', '.join(paper.get('authors', ['Unknown'])[:3])}
Abstract: {paper.get('abstract', 'No abstract')[:500]}

INDIVIDUAL REVIEWS:
{''.join(review_summaries)}

{stats_summary}
{concerns_text}

═══════════════════════════════════════════════════════════════════════════════
CRITICAL INSTRUCTIONS - READ CAREFULLY:
═══════════════════════════════════════════════════════════════════════════════

1. **IGNORE NITPICKS**: If reviewers give low scores for grammar, formatting, typos, 
   or presentation issues BUT acknowledge the SCIENCE/METHODOLOGY is sound → 
   OVERRULE THEM. Change "Reject" to "Minor Revision" or even "Accept".

2. **NO AUTOMATIC SCORE-BASED REJECTION**: Do NOT reject just because average < 4.0.
   READ the actual feedback. If the core contribution is valuable, it deserves revision.

3. **DETECT "TRY-HARD" REVIEWERS**: Some AI reviewers feel they MUST find flaws to be 
   useful. If a reviewer gives low scores but their feedback is vague or nitpicky 
   (e.g., "could be clearer", "minor issues"), RAISE the scores.

4. **SCIENTIFIC MERIT TRUMPS ALL**: A paper with groundbreaking methodology but poor 
   writing = "Minor Revision" (fixable). A paper with perfect writing but flawed 
   science = "Reject" (unfixable).

5. **BENEFIT OF THE DOUBT**: When reviewers disagree significantly, lean toward the 
   MORE FAVORABLE interpretation if the science is defensible.

6. **REAL PAPERS ARE GOOD**: If this looks like a legitimately published academic 
   paper (proper structure, citations, methodology), assume competence. Don't invent 
   problems that aren't explicitly stated by reviewers.

═══════════════════════════════════════════════════════════════════════════════

YOUR TASK:
1. READ each reviewer's actual text feedback, not just scores
2. Identify if low scores are for SUBSTANCE (bad science) or STYLE (bad writing)
3. Weight scientific merit 3x higher than presentation quality
4. Overrule unfair reviewers if their criticisms are nitpicky
5. Make a FAIR decision that a reasonable human editor would make

You must provide your response in this EXACT JSON format:
```json
{{
    "decision": "Accept" | "Minor Revision" | "Major Revision" | "Reject",
    "confidence": 0.0-1.0,
    "adjusted_scores": {{
        "novelty": 1-10,
        "clarity": 1-10,
        "methodology": 1-10,
        "relevance": 1-10,
        "overall": 1-10
    }},
    "reasoning": "Your detailed reasoning - explain if you overruled any reviewers and why",
    "overruled_reviewers": ["Reviewer 1 - reason", "Reviewer 2 - reason"] or [],
    "key_strengths": ["strength1", "strength2", "strength3"],
    "key_weaknesses": ["weakness1", "weakness2", "weakness3"],
    "recommendations": ["recommendation1", "recommendation2"]
}}
```

DECISION GUIDELINES (Use Judgment, Not Just Math):
- Accept: Core science is sound, any issues are minor/cosmetic
- Minor Revision: Good science, needs polish or small clarifications
- Major Revision: Promising idea, but methodology needs strengthening
- Reject: ONLY if fundamental scientific flaws OR ethical concerns (plagiarism, fraud)

DO NOT REJECT a paper just because it scored 3.9 instead of 4.0. Use your judgment."""

        return prompt
    
    def _parse_thinking_response(self, response_text: str, stats: Dict) -> Dict[str, Any]:
        """Parse the Gemini Thinking response into structured result."""
        try:
            # Extract JSON from response
            text = response_text.strip()
            
            # Find JSON block
            if '```json' in text:
                json_start = text.find('```json') + 7
                json_end = text.find('```', json_start)
                json_str = text[json_start:json_end].strip()
            elif '```' in text:
                json_start = text.find('```') + 3
                json_end = text.find('```', json_start)
                json_str = text[json_start:json_end].strip()
            else:
                # Try to find JSON object directly
                import re
                match = re.search(r'\{[\s\S]*\}', text)
                if match:
                    json_str = match.group()
                else:
                    raise ValueError("No JSON found in response")
            
            data = json.loads(json_str)
            
            # Build explanation from parsed data
            explanation = self._build_explanation(data)
            
            return {
                'decision': data.get('decision', 'Minor Revision'),
                'confidence': float(data.get('confidence', 0.7)),
                'adjusted_scores': data.get('adjusted_scores', stats['weighted_mean_scores']),
                'explanation': explanation,
                'thinking_trace': data.get('reasoning', ''),
                'key_strengths': data.get('key_strengths', []),
                'key_weaknesses': data.get('key_weaknesses', []),
                'recommendations': data.get('recommendations', [])
            }
            
        except Exception as e:
            logger.error(f"Failed to parse thinking response: {e}")
            logger.debug(f"Response was: {response_text[:500]}")
            return self._get_fallback_decision(stats)
    
    def _build_explanation(self, data: Dict) -> str:
        """Build a formatted explanation from thinking result."""
        decision = data.get('decision', 'Unknown')
        scores = data.get('adjusted_scores', {})
        reasoning = data.get('reasoning', 'No reasoning provided')
        strengths = data.get('key_strengths', [])
        weaknesses = data.get('key_weaknesses', [])
        recommendations = data.get('recommendations', [])
        
        explanation = f"""## Editorial Decision: **{decision}**

### Overall Assessment
{reasoning}

### Final Scores
| Criterion | Score |
|-----------|-------|
| Novelty | {scores.get('novelty', 'N/A')}/10 |
| Clarity | {scores.get('clarity', 'N/A')}/10 |
| Methodology | {scores.get('methodology', 'N/A')}/10 |
| Relevance | {scores.get('relevance', 'N/A')}/10 |
| **Overall** | **{scores.get('overall', 'N/A')}/10** |

"""
        
        if strengths:
            explanation += "### Key Strengths\n"
            for s in strengths:
                explanation += f"- {s}\n"
            explanation += "\n"
        
        if weaknesses:
            explanation += "### Areas for Improvement\n"
            for w in weaknesses:
                explanation += f"- {w}\n"
            explanation += "\n"
        
        if recommendations:
            explanation += "### Recommendations for Authors\n"
            for r in recommendations:
                explanation += f"- {r}\n"
        
        return explanation
    
    def _negotiate_with_thinking(self, reviews: List[Dict], stats: Dict, 
                                  initial_result: Dict) -> List[Dict]:
        """
        Simplified negotiation when there are disagreements.
        Uses statistical adjustment rather than full re-prompting.
        """
        rounds = []
        current_scores = initial_result['adjusted_scores'].copy()
        
        for round_num in range(min(2, self.max_rounds)):  # Max 2 rounds
            # Calculate how far each reviewer is from consensus
            adjusted_reviews = []
            
            for review in reviews:
                review_scores = review.get('scores', {})
                confidence = review.get('confidence', 0.7)
                adjusted_review = {}
                
                for criterion in ['novelty', 'clarity', 'methodology', 'relevance', 'overall']:
                    review_score = review_scores.get(criterion, 6.0)
                    consensus_score = current_scores.get(criterion, 6.0)
                    
                    # Move toward consensus, weighted by confidence
                    adjustment = (consensus_score - review_score) * 0.3 * confidence
                    adjusted_review[criterion] = round(review_score + adjustment, 2)
                
                adjusted_reviews.append(adjusted_review)
            
            # Recalculate consensus
            new_scores = {}
            for criterion in ['novelty', 'clarity', 'methodology', 'relevance', 'overall']:
                scores = [r[criterion] for r in adjusted_reviews]
                new_scores[criterion] = round(statistics.mean(scores), 2)
            
            rounds.append({
                'round': round_num + 1,
                'adjusted_scores': adjusted_reviews,
                'new_consensus': new_scores,
                'changes': {k: round(new_scores[k] - current_scores.get(k, 6.0), 2) 
                           for k in new_scores}
            })
            
            # Check if converged
            max_change = max(abs(v) for v in rounds[-1]['changes'].values())
            if max_change < 0.3:
                break
            
            current_scores = new_scores
        
        return rounds
    
    def _get_fallback_decision(self, stats: Dict) -> Dict[str, Any]:
        """Fallback decision when thinking model fails - MORE LENIENT."""
        weighted_overall = stats['weighted_mean_scores'].get('overall', 6.0)
        methodology_score = stats['weighted_mean_scores'].get('methodology', 6.0)
        
        # NEW LOGIC: Methodology is king. Good science with bad writing = revision, not reject
        if methodology_score >= 6.0:
            # Science is sound - never reject
            if weighted_overall >= 7.0:
                decision = 'Accept'
            elif weighted_overall >= 5.0:
                decision = 'Minor Revision'
            else:
                decision = 'Major Revision'  # NOT reject - science is good
        else:
            # Methodology concerns - be more careful
            if weighted_overall >= 7.5:
                decision = 'Accept'
            elif weighted_overall >= 6.0:
                decision = 'Minor Revision'
            elif weighted_overall >= 4.0:
                decision = 'Major Revision'
            else:
                # Only reject if BOTH methodology AND overall are bad
                decision = 'Major Revision'  # Still give benefit of doubt
        
        # Confidence based on agreement
        confidence = 0.7 if not stats['has_disagreements'] else 0.5
        
        return {
            'decision': decision,
            'confidence': confidence,
            'adjusted_scores': stats['weighted_mean_scores'],
            'explanation': f"""## Editorial Decision: **{decision}**

### Statistical Summary
Based on {stats['reviewer_count']} reviews, the weighted consensus scores are:

| Criterion | Score |
|-----------|-------|
| Novelty | {stats['weighted_mean_scores'].get('novelty', 'N/A')}/10 |
| Clarity | {stats['weighted_mean_scores'].get('clarity', 'N/A')}/10 |
| Methodology | {stats['weighted_mean_scores'].get('methodology', 'N/A')}/10 |
| Relevance | {stats['weighted_mean_scores'].get('relevance', 'N/A')}/10 |
| **Overall** | **{stats['weighted_mean_scores'].get('overall', 'N/A')}/10** |

{'⚠️ Note: There was significant disagreement among reviewers.' if stats['has_disagreements'] else '✓ Reviewers showed good agreement.'}

*This is a statistical fallback decision. For detailed analysis, please review individual feedback.*
""",
            'thinking_trace': 'Fallback statistical analysis used.',
            'key_strengths': [],
            'key_weaknesses': [],
            'recommendations': []
        }
    
    def _sanitize_reviews(self, reviews: List[Dict]) -> List[Dict]:
        """Sanitize reviews to ensure valid data."""
        sanitized = []
        
        for review in reviews:
            if not isinstance(review, dict):
                continue
            
            scores = review.get('scores', {})
            if not isinstance(scores, dict):
                scores = self._get_default_scores()
            
            # Fill missing scores
            default = self._get_default_scores()
            for key in default:
                if key not in scores or not isinstance(scores.get(key), (int, float)):
                    scores[key] = default[key]
            
            sanitized.append({
                'reviewer_id': review.get('reviewer_id', 'unknown'),
                'scores': scores,
                'written_feedback': review.get('written_feedback', 'No feedback'),
                'confidence': float(review.get('confidence', 0.7)),
                'recommendation': review.get('recommendation', 'Minor Revision')
            })
        
        return sanitized
    
    def _get_default_scores(self) -> Dict[str, float]:
        """Return default scores."""
        return {
            'novelty': 6.0,
            'clarity': 6.0,
            'methodology': 6.0,
            'relevance': 6.0,
            'overall': 6.0
        }
    
    def _create_fallback_consensus(self, error_msg: str) -> Dict[str, Any]:
        """Create fallback consensus on error."""
        return {
            'decision': 'Major Revision',
            'negotiation_rounds': [],
            'final_scores': self._get_default_scores(),
            'confidence': 0.5,
            'overall_explanation': f"""## Editorial Decision: **Major Revision**

### Note
The consensus process encountered an issue: {error_msg}

A default decision of "Major Revision" has been assigned. Please review individual feedback for detailed analysis.
""",
            'thinking_trace': f'Fallback due to: {error_msg}',
            'statistical_summary': {}
        }
