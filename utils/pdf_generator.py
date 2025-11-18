from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime
from models.papers import Paper
from models.reviews import Review
from models.consensus import Consensus
from models.bias_flags import BiasFlag
from models.ledger_blocks import LedgerBlock
import re

class ReviewReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            textColor=colors.darkblue
        )
        self.feedback_style = ParagraphStyle(
            'FeedbackStyle',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=20,
            spaceAfter=12,
            alignment=0
        )
    
    def format_markdown_text(self, text):
        """Convert markdown to ReportLab formatted text"""
        if not text:
            return ''
        
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
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
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
        paper_data = [
            ['Title:', paper.title],
            ['Authors:', ', '.join(paper.authors) if paper.authors else 'N/A'],
            ['Year:', paper.year or 'N/A'],
            ['DOI:', paper.doi or 'N/A'],
            ['Source:', paper.source or 'N/A']
        ]
        paper_table = Table(paper_data, colWidths=[1.5*inch, 4*inch])
        paper_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(paper_table)
        story.append(Spacer(1, 20))
        
        # Abstract
        if paper.abstract:
            story.append(Paragraph("Abstract", self.styles['Heading2']))
            story.append(Paragraph(paper.abstract, self.styles['Normal']))
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
                formatted_feedback = self.format_markdown_text(review.written_feedback)
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
                formatted_explanation = self.format_markdown_text(explanation)
                story.append(Paragraph(formatted_explanation, self.feedback_style))
            
            story.append(Spacer(1, 20))
        
        # Bias Detection
        if bias_flags:
            story.append(Paragraph("Bias Detection Results", self.styles['Heading2']))
            for flag in bias_flags:
                story.append(Paragraph(f"Type: {flag.bias_type} (Severity: {flag.severity})", self.styles['Heading4']))
                if flag.description:
                    story.append(Paragraph(flag.description, self.styles['Normal']))
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