"""
Reviewer Agent using DSPy + Groq Llama 3.1 8B
==============================================
This module uses DSPy to create optimized reviewer agents:
1. No more manual f-string prompts
2. DSPy compiles the best prompt for personality traits
3. Strictness slider actually works via DSPy optimization
4. Uses Groq Llama 3.1 8B for fast, lightweight review generation (560 tps)

DSPy Signatures define WHAT we want, not HOW to prompt.
The framework optimizes prompts automatically.
"""

import dspy
from typing import Dict, Any, List, Optional
import logging
import json
import google.generativeai as genai
from agents.base_agent import BaseAgent
from config import Config

logger = logging.getLogger(__name__)


# ============================================
# DSPy SIGNATURES - Define the review structure
# ============================================

class PaperReviewSignature(dspy.Signature):
    """
    Signature for academic paper review generation.
    DSPy will optimize prompts based on this structure.
    
    CRITICAL SCORING PHILOSOPHY (Anti-Nitpick Rules):
    - A solid paper with good methodology deserves 8-9/10, NOT 6-7 because of minor issues
    - Writing style issues (grammar, formatting) should NEVER drop a score below 7/10
    - If the science is sound, the paper passes. Period.
    - Do NOT invent flaws that don't exist just to seem thorough
    - Score what you SEE, not what you WISH was there
    - Default assumption: The paper is GOOD unless proven otherwise
    
    SCORING CALIBRATION:
    - 9-10: Excellent work, publishable as-is or minor typo fixes
    - 7-8: Good solid work, needs minor revisions (clarifications, small additions)
    - 5-6: Acceptable but needs major revisions (methodology gaps, unclear claims)
    - 3-4: Serious problems (flawed methodology, unsupported claims)
    - 1-2: Fundamentally broken (fabricated data, completely wrong approach)
    
    Most papers should score 6-8. Scores below 5 require SPECIFIC, SERIOUS issues.
    """
    # Inputs
    paper_title: str = dspy.InputField(desc="The title of the academic paper")
    paper_abstract: str = dspy.InputField(desc="The abstract of the paper")
    paper_content: str = dspy.InputField(desc="Key content from the paper (intro, methods, results)")
    visual_descriptions: str = dspy.InputField(desc="Descriptions of figures, charts, and diagrams")
    
    reviewer_expertise: str = dspy.InputField(desc="Expertise areas: methodology, novelty, clarity, theory, application")
    strictness_level: float = dspy.InputField(desc="How strict (0.0=lenient, 1.0=harsh) - NOTE: Even at 1.0, good papers score 7+")
    detail_focus: float = dspy.InputField(desc="Attention to details (0.0=big picture, 1.0=meticulous) - Focus on IMPORTANT details, not nitpicks")
    innovation_bias: float = dspy.InputField(desc="Preference for novel work (0.0=conservative, 1.0=loves innovation)")
    writing_standards: float = dspy.InputField(desc="Writing expectations (0.0=relaxed, 1.0=perfectionist) - Grammar issues alone should NOT cause rejection")
    methodology_rigor: float = dspy.InputField(desc="Methodology expectations (0.0=flexible, 1.0=rigorous) - This is the MOST important criterion")
    optimism: float = dspy.InputField(desc="General disposition (0.0=pessimistic, 1.0=encouraging)")
    
    # Outputs - With anti-nitpick calibration
    novelty_score: float = dspy.OutputField(desc="Score 1-10 for novelty. Incremental improvements are fine (7+). Only <5 if truly derivative.")
    clarity_score: float = dspy.OutputField(desc="Score 1-10 for clarity. If you understood the paper, it's at least 6. Grammar issues = 7 minimum.")
    methodology_score: float = dspy.OutputField(desc="Score 1-10 for methodology. THIS IS KEY. Sound methodology = 7+. Only <5 if fundamentally flawed.")
    relevance_score: float = dspy.OutputField(desc="Score 1-10 for relevance. If it fits the field, it's at least 6. Niche topics deserve 7+.")
    overall_score: float = dspy.OutputField(desc="Overall score 1-10. Should track methodology_score. If methodology is 7+, overall is 7+.")
    
    summary: str = dspy.OutputField(desc="2-3 sentence summary of the paper's contribution - focus on WHAT they achieved")
    strengths: str = dspy.OutputField(desc="3-5 key strengths - be GENEROUS in recognizing good work")
    weaknesses: str = dspy.OutputField(desc="2-4 REAL weaknesses - must be specific and fixable. Do NOT list nitpicks.")
    detailed_feedback: str = dspy.OutputField(desc="Constructive feedback to help authors IMPROVE, not to justify rejection")
    recommendation: str = dspy.OutputField(desc="Accept (8+), Minor Revision (6-8), Major Revision (4-6), or Reject (<4 with SERIOUS flaws only)")


class VisualAnalysisSignature(dspy.Signature):
    """
    Signature for analyzing figures and detecting fake/stolen visuals.
    """
    figure_description: str = dspy.InputField(desc="Description of the figure from Gemini Vision")
    paper_context: str = dspy.InputField(desc="Brief context of what the paper claims")
    
    authenticity_score: float = dspy.OutputField(desc="Score 0-1 for how authentic the visual appears")
    concerns: str = dspy.OutputField(desc="Any concerns about the visual's legitimacy")
    recommendation: str = dspy.OutputField(desc="Keep, Flag for Review, or Reject")


# ============================================
# DSPy MODULES - The actual review logic
# ============================================

class AcademicReviewer(dspy.Module):
    """
    DSPy Module that generates academic reviews.
    The prompts are optimized by DSPy, not manually written.
    """
    
    def __init__(self):
        super().__init__()
        self.review_generator = dspy.ChainOfThought(PaperReviewSignature)
    
    def forward(self, paper_title, paper_abstract, paper_content, visual_descriptions,
                reviewer_expertise, strictness_level, detail_focus, innovation_bias,
                writing_standards, methodology_rigor, optimism):
        """Generate a review using DSPy-optimized prompts."""
        
        result = self.review_generator(
            paper_title=paper_title,
            paper_abstract=paper_abstract,
            paper_content=paper_content,
            visual_descriptions=visual_descriptions,
            reviewer_expertise=reviewer_expertise,
            strictness_level=strictness_level,
            detail_focus=detail_focus,
            innovation_bias=innovation_bias,
            writing_standards=writing_standards,
            methodology_rigor=methodology_rigor,
            optimism=optimism
        )
        
        return result


# ============================================
# MAIN REVIEWER AGENT CLASS
# ============================================

class ReviewerAgent(BaseAgent):
    """
    DSPy-powered reviewer agent using Groq Llama 3.1 8B.
    Personality traits are now properly compiled into effective prompts.
    """
    
    def __init__(self, agent_id: str, expertise: List[str] = None, 
                 review_bias: str = 'balanced', personality_traits: Dict[str, float] = None):
        super().__init__(agent_id, f"Reviewer_{agent_id}")
        
        self.expertise = expertise or ['general']
        self.review_bias = review_bias
        self.personality_traits = personality_traits or self._get_default_traits()
        
        # Initialize DSPy with Groq Llama 3.1 8B
        self._setup_dspy()
        
        # Create the DSPy reviewer module
        self.reviewer_module = AcademicReviewer()
        
        self.log_activity(f"Initialized with DSPy + Groq {Config.GROQ_MODEL}")
    
    def _setup_dspy(self):
        """Configure DSPy to use Groq Llama 3.1 8B (560 tps)."""
        try:
            # Configure Groq for DSPy (OpenAI-compatible API)
            lm = dspy.LM(
                model=f"groq/{Config.GROQ_MODEL}",
                api_key=Config.GROQ_API_KEY,
                temperature=0.7,
                max_tokens=4000
            )
            dspy.configure(lm=lm)
            logger.info(f"DSPy configured with Groq {Config.GROQ_MODEL}")
        except Exception as e:
            logger.error(f"Failed to configure DSPy with Groq: {str(e)}")
            # Fallback will use direct API
    
    def _get_default_traits(self) -> Dict[str, float]:
        """Get default personality traits (balanced reviewer)."""
        return {
            'strictness': 0.5,
            'detail_focus': 0.5,
            'innovation_bias': 0.5,
            'writing_standards': 0.5,
            'methodology_rigor': 0.5,
            'optimism': 0.5
        }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a paper and generate review using DSPy.
        
        Args:
            input_data: {'paper': paper_dict with title, abstract, full_text, visual_analysis}
            
        Returns:
            Review dict with scores, feedback, confidence
        """
        try:
            paper = input_data.get('paper')
            if not paper:
                return self._create_fallback_review("No paper data provided")
            
            paper = self._sanitize_paper_data(paper)
            self.log_activity(f"Starting DSPy review of: {paper.get('title', 'Unknown')[:50]}...")
            
            # Prepare visual descriptions
            visual_desc = self._format_visual_descriptions(paper.get('visual_analysis', []))
            
            # Prepare content (abstract + intro + methods)
            content = self._prepare_content(paper)
            
            # Call DSPy module
            try:
                result = self.reviewer_module(
                    paper_title=paper['title'],
                    paper_abstract=paper['abstract'],
                    paper_content=content,
                    visual_descriptions=visual_desc,
                    reviewer_expertise=', '.join(self.expertise),
                    strictness_level=self.personality_traits.get('strictness', 0.5),
                    detail_focus=self.personality_traits.get('detail_focus', 0.5),
                    innovation_bias=self.personality_traits.get('innovation_bias', 0.5),
                    writing_standards=self.personality_traits.get('writing_standards', 0.5),
                    methodology_rigor=self.personality_traits.get('methodology_rigor', 0.5),
                    optimism=self.personality_traits.get('optimism', 0.5)
                )
                
                # Parse DSPy result
                scores = self._extract_scores(result)
                feedback = self._format_feedback(result)
                confidence = self._calculate_confidence(scores)
                
            except Exception as e:
                logger.warning(f"DSPy call failed, using fallback: {str(e)}")
                return self._generate_fallback_review(paper)
            
            review = {
                'reviewer_id': self.agent_id,
                'scores': scores,
                'written_feedback': feedback,
                'confidence': confidence,
                'recommendation': getattr(result, 'recommendation', 'Minor Revision'),
                'logs': f"DSPy review completed by {self.name}"
            }
            
            self.log_activity(f"Review completed - Overall: {scores.get('overall', 0):.1f}/10")
            return review
            
        except Exception as e:
            logger.error(f"Critical error in reviewer {self.agent_id}: {str(e)}")
            return self._create_fallback_review(f"Critical error: {str(e)}")
    
    def _format_visual_descriptions(self, visual_analysis: List[Dict]) -> str:
        """Format visual analysis from Gemini Vision into text."""
        if not visual_analysis:
            return "No figures or diagrams described."
        
        descriptions = []
        for i, visual in enumerate(visual_analysis[:5]):  # Limit to 5
            desc = f"Figure {i+1}: {visual.get('type', 'unknown')} - {visual.get('description', 'No description')}"
            if visual.get('concerns'):
                desc += f" [CONCERNS: {', '.join(visual['concerns'])}]"
            descriptions.append(desc)
        
        return '\n'.join(descriptions)
    
    def _prepare_content(self, paper: Dict) -> str:
        """Prepare paper content for review (limited to key sections)."""
        sections = paper.get('sections', {})
        parts = []
        
        # Introduction
        if sections.get('introduction'):
            parts.append(f"INTRODUCTION:\n{sections['introduction'][:1500]}")
        
        # Methods
        if sections.get('methods') or sections.get('methodology'):
            methods = sections.get('methods') or sections.get('methodology')
            parts.append(f"METHODS:\n{methods[:1500]}")
        
        # Results
        if sections.get('results'):
            parts.append(f"RESULTS:\n{sections['results'][:1500]}")
        
        # Conclusion
        if sections.get('conclusion'):
            parts.append(f"CONCLUSION:\n{sections['conclusion'][:1000]}")
        
        # Fallback to full text if no sections
        if not parts and paper.get('full_text'):
            parts.append(paper['full_text'][:5000])
        
        return '\n\n'.join(parts) if parts else "Content not available"
    
    def _extract_scores(self, result) -> Dict[str, float]:
        """Extract numerical scores from DSPy result."""
        try:
            scores = {
                'novelty': self._safe_float(getattr(result, 'novelty_score', 6.0)),
                'clarity': self._safe_float(getattr(result, 'clarity_score', 6.0)),
                'methodology': self._safe_float(getattr(result, 'methodology_score', 6.0)),
                'relevance': self._safe_float(getattr(result, 'relevance_score', 6.0)),
                'overall': self._safe_float(getattr(result, 'overall_score', 6.0))
            }
            
            # Apply personality-based adjustments
            scores = self._apply_personality_adjustments(scores)
            
            # Ensure scores are in valid range
            for key in scores:
                scores[key] = round(max(1.0, min(10.0, scores[key])), 1)
            
            return scores
            
        except Exception as e:
            logger.error(f"Error extracting scores: {str(e)}")
            return self._get_default_scores()
    
    def _safe_float(self, value) -> float:
        """Safely convert value to float."""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                # Extract first number from string
                import re
                match = re.search(r'[\d.]+', value)
                if match:
                    return float(match.group())
            return 6.0
        except:
            return 6.0
    
    def _apply_personality_adjustments(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Apply personality trait adjustments to scores."""
        strictness = self.personality_traits.get('strictness', 0.5)
        optimism = self.personality_traits.get('optimism', 0.5)
        innovation_bias = self.personality_traits.get('innovation_bias', 0.5)
        methodology_rigor = self.personality_traits.get('methodology_rigor', 0.5)
        
        # Strictness reduces all scores slightly
        strictness_adj = (0.5 - strictness) * 1.5  # Range: -0.75 to +0.75
        
        # Optimism increases all scores slightly
        optimism_adj = (optimism - 0.5) * 1.0  # Range: -0.5 to +0.5
        
        # Apply general adjustments
        for key in scores:
            scores[key] += strictness_adj + optimism_adj
        
        # Innovation bias affects novelty specifically
        scores['novelty'] += (innovation_bias - 0.5) * 1.5
        
        # Methodology rigor affects methodology score
        scores['methodology'] += (0.5 - methodology_rigor) * 1.0
        
        return scores
    
    def _format_feedback(self, result) -> str:
        """Format DSPy result into readable feedback."""
        parts = []
        
        # Summary
        summary = getattr(result, 'summary', '')
        if summary:
            parts.append(f"## Summary\n{summary}")
        
        # Strengths
        strengths = getattr(result, 'strengths', '')
        if strengths:
            parts.append(f"## Strengths\n{strengths}")
        
        # Weaknesses
        weaknesses = getattr(result, 'weaknesses', '')
        if weaknesses:
            parts.append(f"## Weaknesses\n{weaknesses}")
        
        # Detailed feedback
        detailed = getattr(result, 'detailed_feedback', '')
        if detailed:
            parts.append(f"## Detailed Feedback\n{detailed}")
        
        # Recommendation
        rec = getattr(result, 'recommendation', 'Minor Revision')
        parts.append(f"## Recommendation\n**{rec}**")
        
        return '\n\n'.join(parts) if parts else "Review feedback not available."
    
    def _calculate_confidence(self, scores: Dict[str, float]) -> float:
        """Calculate confidence based on score consistency."""
        try:
            values = list(scores.values())
            mean = sum(values) / len(values)
            variance = sum((x - mean) ** 2 for x in values) / len(values)
            
            # Lower variance = higher confidence
            confidence = max(0.5, 1.0 - (variance / 20.0))
            return round(confidence, 2)
        except:
            return 0.7
    
    def _sanitize_paper_data(self, paper: Dict) -> Dict:
        """Ensure paper has all required fields."""
        return {
            'title': paper.get('title') or 'Unknown Title',
            'abstract': paper.get('abstract') or 'No abstract available',
            'authors': paper.get('authors') or ['Unknown Author'],
            'year': paper.get('year') or 'Unknown',
            'full_text': paper.get('full_text') or '',
            'sections': paper.get('sections') or {},
            'visual_analysis': paper.get('visual_analysis') or [],
            'keywords': paper.get('keywords') or []
        }
    
    def _get_default_scores(self) -> Dict[str, float]:
        """Return default scores."""
        return {
            'novelty': 6.0,
            'clarity': 6.0,
            'methodology': 6.0,
            'relevance': 6.0,
            'overall': 6.0
        }
    
    def _create_fallback_review(self, error_msg: str) -> Dict[str, Any]:
        """Create fallback review on error."""
        scores = self._get_default_scores()
        return {
            'reviewer_id': self.agent_id,
            'scores': scores,
            'written_feedback': f"Review could not be completed: {error_msg}. Default assessment provided.",
            'confidence': 0.5,
            'recommendation': 'Minor Revision',
            'logs': f"Fallback review by {self.name}: {error_msg}"
        }
    
    def _generate_fallback_review(self, paper: Dict) -> Dict[str, Any]:
        """Generate review using Groq API as fallback."""
        try:
            import httpx
            
            prompt = f"""You are an academic peer reviewer with expertise in {', '.join(self.expertise)}.
Your personality traits: 
- Strictness: {self.personality_traits.get('strictness', 0.5):.1f}/1.0
- Detail focus: {self.personality_traits.get('detail_focus', 0.5):.1f}/1.0  
- Innovation preference: {self.personality_traits.get('innovation_bias', 0.5):.1f}/1.0
- Writing standards: {self.personality_traits.get('writing_standards', 0.5):.1f}/1.0
- Methodology rigor: {self.personality_traits.get('methodology_rigor', 0.5):.1f}/1.0
- Optimism: {self.personality_traits.get('optimism', 0.5):.1f}/1.0

CRITICAL SCORING PHILOSOPHY - YOU MUST FOLLOW THIS:
1. A solid paper with good methodology deserves 8-9/10, NOT 6-7 because of minor issues
2. Writing/grammar issues should NEVER drop a score below 7/10
3. If the science is sound, the paper passes. Don't invent flaws to seem thorough.
4. Score what you SEE, not what you WISH was there
5. Default assumption: The paper is GOOD unless you find SPECIFIC, SERIOUS problems

SCORING CALIBRATION:
- 9-10: Excellent, publishable as-is
- 7-8: Good solid work, minor revisions needed (this is where MOST papers should be)
- 5-6: Acceptable but major revisions needed
- 3-4: Serious problems (only if methodology is fundamentally flawed)
- 1-2: Reject (fabricated data, plagiarism, completely wrong approach)

Review this paper and provide scores (1-10) and feedback:

Title: {paper['title']}
Abstract: {paper['abstract'][:1000]}

Return ONLY valid JSON with: novelty_score, clarity_score, methodology_score, relevance_score, overall_score, summary, strengths, weaknesses, detailed_feedback, recommendation

IMPORTANT: recommendation should be "Accept" (8+), "Minor Revision" (6-8), "Major Revision" (4-6), or "Reject" (only for scores <4 with SERIOUS flaws)"""

            # Call Groq API
            response = httpx.post(
                f"{Config.GROQ_API_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {Config.GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": Config.GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 4000,
                    "response_format": {"type": "json_object"}
                },
                timeout=60.0
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            text = result['choices'][0]['message']['content'].strip()
            
            # Parse JSON
            if text.startswith('```'):
                text = text.split('\n', 1)[1] if '\n' in text else text[3:]
            if text.endswith('```'):
                text = text[:-3]
            
            data = json.loads(text.strip())
            
            scores = {
                'novelty': self._safe_float(data.get('novelty_score', 6)),
                'clarity': self._safe_float(data.get('clarity_score', 6)),
                'methodology': self._safe_float(data.get('methodology_score', 6)),
                'relevance': self._safe_float(data.get('relevance_score', 6)),
                'overall': self._safe_float(data.get('overall_score', 6))
            }
            
            feedback = f"""## Summary
{data.get('summary', 'No summary')}

## Strengths
{data.get('strengths', 'Not specified')}

## Weaknesses  
{data.get('weaknesses', 'Not specified')}

## Detailed Feedback
{data.get('detailed_feedback', 'No detailed feedback')}

## Recommendation
**{data.get('recommendation', 'Minor Revision')}**"""

            return {
                'reviewer_id': self.agent_id,
                'scores': scores,
                'written_feedback': feedback,
                'confidence': 0.7,
                'recommendation': data.get('recommendation', 'Minor Revision'),
                'logs': f"Fallback Groq review by {self.name}"
            }
            
        except Exception as e:
            logger.error(f"Fallback Groq review failed: {str(e)}")
            # Try Gemma 3 via OpenRouter as second fallback
            return self._generate_gemma_review(paper)
    
    def _generate_gemma_review(self, paper: Dict) -> Dict[str, Any]:
        """
        Generate review using Gemma 3 27B via OpenRouter (FREE fallback).
        This is used when both DSPy and Groq API fail.
        """
        try:
            import httpx
            
            if not Config.OPENROUTER_API_KEY:
                logger.warning("OpenRouter API key not configured, using default review")
                return self._create_fallback_review("No fallback API available")
            
            logger.info(f"[{self.agent_id}] Trying Gemma 3 fallback via OpenRouter")
            
            prompt = f"""You are an academic peer reviewer. Review this paper and provide scores (1-10) and feedback.

Title: {paper['title']}
Abstract: {paper['abstract'][:1000]}

SCORING GUIDE:
- 9-10: Excellent, publishable
- 7-8: Good, minor revisions (MOST papers belong here)
- 5-6: Major revisions needed
- 3-4: Serious flaws
- 1-2: Reject

Return ONLY valid JSON:
{{"novelty_score": 7, "clarity_score": 7, "methodology_score": 7, "relevance_score": 7, "overall_score": 7, "summary": "...", "strengths": "...", "weaknesses": "...", "detailed_feedback": "...", "recommendation": "Minor Revision"}}"""

            response = httpx.post(
                f"{Config.OPENROUTER_API_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://peernet.app",
                    "X-Title": "PeerNet++ Academic Review"
                },
                json={
                    "model": Config.OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 4000
                },
                timeout=90.0
            )
            response.raise_for_status()
            
            result = response.json()
            text = result['choices'][0]['message']['content'].strip()
            
            # Extract JSON from response
            if '{' in text:
                start = text.find('{')
                end = text.rfind('}') + 1
                text = text[start:end]
            
            data = json.loads(text)
            
            scores = {
                'novelty': self._safe_float(data.get('novelty_score', 6)),
                'clarity': self._safe_float(data.get('clarity_score', 6)),
                'methodology': self._safe_float(data.get('methodology_score', 6)),
                'relevance': self._safe_float(data.get('relevance_score', 6)),
                'overall': self._safe_float(data.get('overall_score', 6))
            }
            
            feedback = f"""## Summary
{data.get('summary', 'No summary')}

## Strengths
{data.get('strengths', 'Not specified')}

## Weaknesses  
{data.get('weaknesses', 'Not specified')}

## Detailed Feedback
{data.get('detailed_feedback', 'No detailed feedback')}

## Recommendation
**{data.get('recommendation', 'Minor Revision')}**"""

            logger.info(f"[{self.agent_id}] Gemma 3 review completed - Overall: {scores['overall']}/10")
            
            return {
                'reviewer_id': self.agent_id,
                'scores': scores,
                'written_feedback': feedback,
                'confidence': 0.7,
                'recommendation': data.get('recommendation', 'Minor Revision'),
                'logs': f"Gemma 3 (OpenRouter) fallback review by {self.name}"
            }
            
        except Exception as e:
            logger.error(f"Gemma 3 fallback also failed: {str(e)}")
            return self._create_fallback_review(f"All AI providers failed: {str(e)}")
