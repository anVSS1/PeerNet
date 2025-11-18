import hashlib
import re
from typing import Dict, Any, List
import logging
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class PlagiarismAgent(BaseAgent):
    def __init__(self, agent_id: str):
        super().__init__(agent_id, f"Plagiarism_{agent_id}")
        self.similarity_threshold = 0.8
        self.min_phrase_length = 10

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect potential plagiarism in paper content.
        """
        try:
            paper = input_data.get('paper', {})
            comparison_papers = input_data.get('comparison_papers', [])
            
            if not paper:
                return self._create_fallback_result("No paper data provided")
            
            text_content = self._extract_text_content(paper)
            if not text_content:
                return self._create_fallback_result("No text content to analyze")
            
            self.log_activity(f"Analyzing plagiarism for paper: {paper.get('title', 'Unknown')}")
            
            # Perform plagiarism detection
            plagiarism_results = self._detect_plagiarism(text_content, comparison_papers)
            
            # Calculate overall plagiarism score
            overall_score = self._calculate_plagiarism_score(plagiarism_results)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(plagiarism_results, overall_score)
            
            result = {
                'agent_id': self.agent_id,
                'plagiarism_score': overall_score,
                'similarity_matches': plagiarism_results['matches'],
                'suspicious_phrases': plagiarism_results['phrases'],
                'recommendations': recommendations,
                'analysis_summary': self._generate_summary(overall_score, plagiarism_results)
            }
            
            self.log_activity(f"Plagiarism analysis completed. Score: {overall_score}")
            return result
            
        except Exception as e:
            logger.error(f"Error in plagiarism detection: {str(e)}")
            return self._create_fallback_result(f"Analysis failed: {str(e)}")
    
    def _extract_text_content(self, paper: Dict) -> str:
        """Extract and clean text content from paper."""
        content_parts = []
        
        # Add title
        if paper.get('title'):
            content_parts.append(paper['title'])
        
        # Add abstract
        if paper.get('abstract'):
            content_parts.append(paper['abstract'])
        
        # Add full text if available
        if paper.get('full_text'):
            content_parts.append(paper['full_text'])
        
        # Combine and clean
        full_text = ' '.join(content_parts)
        
        # Basic cleaning
        full_text = re.sub(r'\s+', ' ', full_text)  # Normalize whitespace
        full_text = re.sub(r'[^\w\s.,;:!?-]', '', full_text)  # Remove special chars
        
        return full_text.strip()
    
    def _detect_plagiarism(self, text: str, comparison_papers: List[Dict]) -> Dict:
        """Detect plagiarism using text similarity analysis."""
        matches = []
        suspicious_phrases = []
        
        # Extract phrases for comparison
        phrases = self._extract_phrases(text)
        
        # Compare with existing papers (simplified simulation)
        for i, comparison_paper in enumerate(comparison_papers[:10]):  # Limit comparisons
            comparison_text = self._extract_text_content(comparison_paper)
            if not comparison_text:
                continue
            
            comparison_phrases = self._extract_phrases(comparison_text)
            
            # Find similar phrases
            similar_phrases = self._find_similar_phrases(phrases, comparison_phrases)
            
            if similar_phrases:
                similarity_score = len(similar_phrases) / max(len(phrases), 1)
                
                if similarity_score > 0.1:  # 10% similarity threshold
                    matches.append({
                        'paper_id': comparison_paper.get('paper_id', f'paper_{i}'),
                        'title': comparison_paper.get('title', 'Unknown'),
                        'similarity_score': round(similarity_score, 3),
                        'matching_phrases': similar_phrases[:5]  # Top 5 matches
                    })
                
                suspicious_phrases.extend(similar_phrases)
        
        # Remove duplicates and sort
        suspicious_phrases = list(set(suspicious_phrases))
        matches = sorted(matches, key=lambda x: x['similarity_score'], reverse=True)
        
        return {
            'matches': matches[:10],  # Top 10 matches
            'phrases': suspicious_phrases[:20]  # Top 20 suspicious phrases
        }
    
    def _extract_phrases(self, text: str) -> List[str]:
        """Extract meaningful phrases from text."""
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        phrases = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) >= self.min_phrase_length:
                # Extract sub-phrases
                words = sentence.split()
                for i in range(len(words) - 4):  # 5-word phrases
                    phrase = ' '.join(words[i:i+5])
                    if len(phrase) >= self.min_phrase_length:
                        phrases.append(phrase.lower())
        
        return list(set(phrases))  # Remove duplicates
    
    def _find_similar_phrases(self, phrases1: List[str], phrases2: List[str]) -> List[str]:
        """Find similar phrases between two sets."""
        similar = []
        
        for phrase1 in phrases1:
            for phrase2 in phrases2:
                similarity = self._calculate_text_similarity(phrase1, phrase2)
                if similarity > self.similarity_threshold:
                    similar.append(phrase1)
                    break
        
        return similar
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_plagiarism_score(self, results: Dict) -> float:
        """Calculate overall plagiarism risk score (0-1)."""
        matches = results.get('matches', [])
        phrases = results.get('phrases', [])
        
        if not matches:
            return 0.0
        
        # Weight by highest similarity and number of matches
        max_similarity = max([m['similarity_score'] for m in matches])
        match_count_factor = min(len(matches) / 5, 1.0)  # Normalize to max 5 matches
        phrase_count_factor = min(len(phrases) / 20, 1.0)  # Normalize to max 20 phrases
        
        overall_score = (max_similarity * 0.5 + match_count_factor * 0.3 + phrase_count_factor * 0.2)
        
        return round(min(overall_score, 1.0), 3)
    
    def _generate_recommendations(self, results: Dict, score: float) -> List[str]:
        """Generate recommendations based on plagiarism analysis."""
        recommendations = []
        
        if score >= 0.7:
            recommendations.extend([
                "HIGH RISK: Significant similarity detected with existing papers",
                "Conduct thorough originality check before publication",
                "Review and rewrite sections with high similarity",
                "Ensure proper citations for all referenced material"
            ])
        elif score >= 0.4:
            recommendations.extend([
                "MODERATE RISK: Some similarity detected",
                "Review flagged sections for proper attribution",
                "Consider paraphrasing similar content",
                "Verify all citations are complete and accurate"
            ])
        elif score >= 0.2:
            recommendations.extend([
                "LOW RISK: Minor similarities found",
                "Standard citation review recommended",
                "Check flagged phrases for proper attribution"
            ])
        else:
            recommendations.append("No significant plagiarism concerns detected")
        
        # Add specific recommendations based on matches
        matches = results.get('matches', [])
        if matches:
            top_match = matches[0]
            recommendations.append(f"Review similarity with: '{top_match['title']}'")
        
        return recommendations
    
    def _generate_summary(self, score: float, results: Dict) -> str:
        """Generate analysis summary."""
        matches = results.get('matches', [])
        phrases = results.get('phrases', [])
        
        if score >= 0.7:
            risk_level = "HIGH RISK"
        elif score >= 0.4:
            risk_level = "MODERATE RISK"
        elif score >= 0.2:
            risk_level = "LOW RISK"
        else:
            risk_level = "MINIMAL RISK"
        
        summary = f"{risk_level}: Plagiarism score {score:.3f}. "
        
        if matches:
            summary += f"Found {len(matches)} similar papers. "
            top_match = matches[0]
            summary += f"Highest similarity: {top_match['similarity_score']:.1%} with '{top_match['title'][:50]}...'."
        else:
            summary += "No significant similarities detected."
        
        if phrases:
            summary += f" {len(phrases)} suspicious phrases identified."
        
        return summary
    
    def _create_fallback_result(self, error_msg: str) -> Dict[str, Any]:
        """Create fallback result when analysis fails."""
        return {
            'agent_id': self.agent_id,
            'plagiarism_score': 0.0,
            'similarity_matches': [],
            'suspicious_phrases': [],
            'recommendations': [f'Analysis failed: {error_msg}'],
            'analysis_summary': f'Plagiarism detection could not be completed: {error_msg}'
        }
        """Generate analysis summary."""
        matches_count = len(results.get('matches', []))
        phrases_count = len(results.get('phrases', []))
        
        risk_level = "HIGH" if score >= 0.7 else "MODERATE" if score >= 0.4 else "LOW" if score >= 0.2 else "MINIMAL"
        
        summary = f"Plagiarism Risk: {risk_level} (Score: {score}). "
        summary += f"Found {matches_count} similar papers and {phrases_count} potentially matching phrases. "
        
        if score >= 0.4:
            summary += "Manual review recommended before publication."
        else:
            summary += "Standard citation verification sufficient."
        
        return summary
    
    def _create_fallback_result(self, error_msg: str) -> Dict[str, Any]:
        """Create fallback result when analysis fails."""
        return {
            'agent_id': self.agent_id,
            'plagiarism_score': 0.0,
            'similarity_matches': [],
            'suspicious_phrases': [],
            'recommendations': [f"Analysis incomplete: {error_msg}"],
            'analysis_summary': f"Plagiarism detection failed: {error_msg}"
        }