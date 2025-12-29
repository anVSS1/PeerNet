'''
PeerNet++ PDF Report Generator
==============================
Generate downloadable PDF review reports using ReportLab.

Includes:
- Paper metadata and abstract
- Individual reviewer scores and feedback
- Consensus decision and explanation
- Bias flags (if any)
- Ledger audit trail

Returns BytesIO buffer for Flask send_file().
'''

from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from io import BytesIO
from datetime import datetime
from models.papers import Paper
from models.reviews import Review
from models.consensus import Consensus
from models.bias_flags import BiasFlag
from models.ledger_blocks import LedgerBlock
import re
import textwrap

class ReviewReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            spaceAfter=30,
            textColor=colors.darkblue,
            alignment=TA_CENTER
        )
        self.feedback_style = ParagraphStyle(
            'FeedbackStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=20,
            rightIndent=20,
            spaceAfter=12,
            alignment=TA_JUSTIFY
        )
        self.abstract_style = ParagraphStyle(
            'AbstractStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=10,
            rightIndent=10,
            spaceAfter=15,
            alignment=TA_JUSTIFY
        )
    
    def format_markdown_text(self, text, max_width=80):
        """Convert markdown to ReportLab formatted text with proper wrapping"""
        if not text:
            return ''
        
        # Wrap long lines to prevent overflow
        lines = text.split('\n')
        wrapped_lines = []
        for line in lines:
            if len(line) > max_width:
                wrapped_lines.extend(textwrap.wrap(line, width=max_width))
            else:
                wrapped_lines.append(line)
        text = '\n'.join(wrapped_lines)
        
        # Convert bold markdown to ReportLab bold
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        
        # Convert italic markdown to ReportLab italic
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        
        # Convert bullet points
        text = re.sub(r'^\*\s+', '• ', text, flags=re.MULTILINE)
        
        # Convert numbered lists (keep numbers)
        text = re.sub(r'^(\d+)\.(\s+)', r'\1. ', text, flags=re.MULTILINE)
        
        # Convert headers to bold
        text = re.sub(r'^#{1,6}\s+(.*?)$', r'<b>\1</b>', text, flags=re.MULTILINE)
        
        # Clean up line breaks
        text = re.sub(r'\n\s*\n', '<br/><br/>', text)
        text = re.sub(r'\n', '<br/>', text)
        
        return text
        
    def generate_report(self, paper_id):
        """Generate PDF report for a paper's review process"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4, 
            rightMargin=50, 
            leftMargin=50, 
            topMargin=50, 
            bottomMargin=50,
            title=f"PeerNet++ Review Report - {paper_id}"
        )
        
        try:
            # Get paper data
            paper = Paper.objects(paper_id=paper_id).first()
            if not paper:
                raise ValueError(f"Paper {paper_id} not found")
                
            reviews = Review.objects(paper=paper)
            consensus = Consensus.objects(paper=paper).first()
            bias_flags = BiasFlag.objects(paper=paper)
            ledger_blocks = LedgerBlock.objects(paper=paper).order_by('timestamp')
        except Exception as e:
            raise ValueError(f"Error fetching data for paper {paper_id}: {str(e)}")
        
        story = []
        
        # Title
        story.append(Paragraph("PeerNet++ Review Report", self.title_style))
        story.append(Spacer(1, 12))
        
        # Paper Info
        story.append(Paragraph("Paper Information", self.styles['Heading2']))
        
        # Wrap long title if needed
        title_wrapped = textwrap.fill(paper.title, width=60) if len(paper.title) > 60 else paper.title
        authors_text = ', '.join(paper.authors[:5]) if paper.authors else 'N/A'
        if len(paper.authors) > 5:
            authors_text += f' (+{len(paper.authors)-5} more)'
        
        paper_data = [
            ['Title:', title_wrapped],
            ['Authors:', authors_text],
            ['Year:', str(paper.year) if paper.year else 'N/A'],
            ['DOI:', paper.doi[:50] + '...' if paper.doi and len(paper.doi) > 50 else paper.doi or 'N/A'],
            ['Source:', paper.source or 'N/A']
        ]
        paper_table = Table(paper_data, colWidths=[1.2*inch, 4.3*inch])
        paper_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(paper_table)
        story.append(Spacer(1, 20))
        
        # Abstract
        if paper.abstract:
            story.append(Paragraph("Abstract", self.styles['Heading2']))
            # Wrap abstract text properly
            abstract_wrapped = self.format_markdown_text(paper.abstract, max_width=90)
            story.append(Paragraph(abstract_wrapped, self.abstract_style))
            story.append(Spacer(1, 20))
        
        # Reviews
        story.append(Paragraph("Review Results", self.styles['Heading2']))
        for review in reviews:
            story.append(Paragraph(f"Reviewer: {review.reviewer_id}", self.styles['Heading3']))
            
            # Scores table
            if review.scores:
                score_data = [['Criterion', 'Score']]
                for criterion, score in review.scores.items():
                    score_data.append([criterion.title(), str(score)])
                
                score_table = Table(score_data, colWidths=[2*inch, 1*inch])
                score_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.grey),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0,0), (-1,-1), 10),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                    ('GRID', (0,0), (-1,-1), 1, colors.black)
                ]))
                story.append(score_table)
                story.append(Spacer(1, 10))
            
            # Written feedback
            if review.written_feedback:
                story.append(Paragraph("Feedback:", self.styles['Heading4']))
                formatted_feedback = self.format_markdown_text(review.written_feedback, max_width=85)
                story.append(Paragraph(formatted_feedback, self.feedback_style))
            
            story.append(Spacer(1, 15))
        
        # Consensus
        if consensus:
            story.append(Paragraph("Consensus Decision", self.styles['Heading2']))
            
            # Safe access to consensus fields
            decision = getattr(consensus, 'decision', 'N/A')
            confidence = getattr(consensus, 'confidence', None)
            final_scores = getattr(consensus, 'final_scores', {})
            overall_score = final_scores.get('overall', 'N/A') if final_scores else 'N/A'
            
            consensus_data = [
                ['Decision:', decision],
                ['Confidence:', f"{confidence:.2f}" if confidence else 'N/A'],
                ['Overall Score:', str(overall_score)]
            ]
            consensus_table = Table(consensus_data, colWidths=[1.5*inch, 2*inch])
            consensus_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(consensus_table)
            
            explanation = getattr(consensus, 'overall_explanation', None)
            if explanation:
                story.append(Spacer(1, 10))
                story.append(Paragraph("Reasoning:", self.styles['Heading4']))
                formatted_explanation = self.format_markdown_text(explanation, max_width=85)
                story.append(Paragraph(formatted_explanation, self.feedback_style))
            
            story.append(Spacer(1, 20))
        
        # Bias Detection
        if bias_flags:
            story.append(Paragraph("Bias Detection Results", self.styles['Heading2']))
            for flag in bias_flags:
                confidence_text = f" (Confidence: {flag.confidence:.2f})" if flag.confidence else ""
                story.append(Paragraph(f"Type: {flag.flag_type}{confidence_text}", self.styles['Heading4']))
                if flag.evidence:
                    evidence_text = str(flag.evidence) if isinstance(flag.evidence, dict) else flag.evidence
                    story.append(Paragraph(f"Evidence: {evidence_text}", self.styles['Normal']))
                story.append(Spacer(1, 10))
        
        # Audit Trail
        if ledger_blocks:
            story.append(Paragraph("Audit Trail", self.styles['Heading2']))
            audit_data = [['Timestamp', 'Event', 'Hash']]
            for block in ledger_blocks:
                event_type = block.data.get('event_type', 'Unknown')
                timestamp = block.timestamp.strftime('%Y-%m-%d %H:%M:%S') if block.timestamp else 'N/A'
                hash_short = block.hash[:16] + '...' if block.hash else 'N/A'
                audit_data.append([timestamp, event_type, hash_short])
            
            audit_table = Table(audit_data, colWidths=[1.5*inch, 2*inch, 1.5*inch])
            audit_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            story.append(audit_table)
        
        # Footer
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", self.styles['Normal']))
        story.append(Paragraph("Generated by PeerNet++ - Decentralized Peer Review System", self.styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer