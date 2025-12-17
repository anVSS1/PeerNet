'''
PeerNet++ Dashboard Routes
==========================
Flask routes for the web dashboard interface.

Pages:
- /papers: List all papers with status
- /papers/<id>: Paper detail with reviews and consensus
- /upload: Paper upload interface (PDF/JSON/API)
- /reviewer-builder: Custom reviewer creation UI
- /analytics: Advanced analytics dashboard
- /login, /register: Authentication pages

All dashboard routes render Jinja2 templates from /templates.
'''

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from models.papers import Paper
from models.reviews import Review
from models.consensus import Consensus
from models.bias_flags import BiasFlag
from models.ledger_blocks import LedgerBlock
from simulation.review_simulation import ReviewSimulation
from utils.auth_middleware import login_required, require_auth, get_current_user
import logging

logger = logging.getLogger(__name__)

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/papers')
@login_required
def papers_list():
    """Display list of all papers."""
    user = get_current_user()
    try:
        search = request.args.get('search', '')
        year = request.args.get('year', '')
        source = request.args.get('source', '')
        status = request.args.get('status', '')
        sort_by = request.args.get('sort', 'title')
        limit = int(request.args.get('limit', 50))

        query = {'user_id': str(user.id)}
        
        # Search filter
        if search:
            import re
            safe_search = re.escape(search)
            query['$or'] = [
                {'title': {'$regex': safe_search, '$options': 'i'}},
                {'authors': {'$regex': safe_search, '$options': 'i'}},
                {'abstract': {'$regex': safe_search, '$options': 'i'}}
            ]
        
        # Year filter
        if year:
            try:
                query['year'] = int(year)
            except ValueError:
                pass
        
        # Source filter
        if source:
            query['source'] = source

        # Get papers with filters
        papers_query = Paper.objects(**query)
        
        # Apply sorting
        if sort_by == 'year':
            papers_query = papers_query.order_by('-year')
        elif sort_by == 'title':
            papers_query = papers_query.order_by('title')
        
        papers = papers_query.limit(limit)

        # Add consensus data to papers for template (optimized)
        papers_with_consensus = []
        paper_ids = [paper.id for paper in papers]
        consensus_map = {c.paper.id: c for c in Consensus.objects(paper__in=paper_ids)}
        
        for paper in papers:
            paper_dict = paper.to_dict()
            consensus = consensus_map.get(paper.id)
            paper_dict['consensus'] = consensus.to_dict() if consensus else None
            papers_with_consensus.append(paper_dict)
        
        # Apply status filter after getting consensus data
        if status:
            if status == 'reviewed':
                papers_with_consensus = [p for p in papers_with_consensus if p['consensus']]
            elif status == 'pending':
                papers_with_consensus = [p for p in papers_with_consensus if not p['consensus']]
        
        # Apply status-based sorting
        if sort_by == 'status':
            papers_with_consensus.sort(key=lambda x: (x['consensus'] is None, x['title']))

        return render_template('papers_list.html',
                             papers=papers_with_consensus,
                             count=len(papers_with_consensus),
                             search=search,
                             year=year,
                             source=source,
                             status=status,
                             sort_by=sort_by,
                             limit=limit)
    except Exception as e:
        logger.error(f"Error loading papers list: {str(e)}")
        flash('Error loading papers list', 'error')
        return render_template('papers_list.html', papers=[], count=0)

import re
import markdown2

@dashboard_bp.route('/paper/<paper_id>')
@login_required
def paper_detail(paper_id):
    """Display detailed view of a paper."""
    user = get_current_user()
    try:
        paper = Paper.objects(paper_id=paper_id, user_id=str(user.id)).first()
        if not paper:
            flash('Paper not found', 'error')
            return redirect(url_for('dashboard.papers_list'))

        # Get related data
        reviews = Review.objects(paper=paper)
        consensus = Consensus.objects(paper=paper).first()
        bias_flags = BiasFlag.objects(paper=paper)
        ledger_blocks = LedgerBlock.objects(paper=paper).order_by('timestamp')

        # Process content for Markdown rendering and cleaning
        if consensus and consensus.overall_explanation:
            # Remove the signature
            cleaned_explanation = re.sub(r'Sincerely,.*', '', consensus.overall_explanation, flags=re.DOTALL)
            consensus.overall_explanation = markdown2.markdown(cleaned_explanation)

        processed_reviews = []
        for r in reviews:
            review_dict = r.to_dict()
            if review_dict.get('written_feedback'):
                review_dict['written_feedback'] = markdown2.markdown(review_dict['written_feedback'])
            processed_reviews.append(review_dict)

        return render_template('paper_detail.html',
                             paper=paper.to_dict(),
                             reviews=processed_reviews,
                             consensus=consensus.to_dict() if consensus else None,
                             bias_flags=[f.to_dict() for f in bias_flags],
                             ledger_blocks=[b.to_dict() for b in ledger_blocks])
    except Exception as e:
        logger.error(f"Error loading paper detail: {str(e)}")
        flash('Error loading paper details', 'error')
        return redirect(url_for('dashboard.papers_list'))

@dashboard_bp.route('/paper/<paper_id>/simulate', methods=['POST'])
@login_required
def simulate_review(paper_id):
    """Trigger review simulation for a paper."""
    user = get_current_user()
    try:
        paper = Paper.objects(paper_id=paper_id, user_id=str(user.id)).first()
        if not paper:
            # Check if AJAX request
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({'error': 'Paper not found'}), 404
            flash('Paper not found', 'error')
            return redirect(url_for('dashboard.papers_list'))

        # Check if already reviewed
        existing_consensus = Consensus.objects(paper=paper).first()
        if existing_consensus:
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({'error': 'Paper already reviewed', 'warning': True}), 400
            flash('Paper already reviewed', 'warning')
            return redirect(url_for('dashboard.paper_detail', paper_id=paper_id))

        # Run simulation in background (non-blocking for AJAX)
        simulation = ReviewSimulation()
        result = simulation.simulate_paper_review(paper)

        # Return JSON for AJAX requests
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({
                'success': True,
                'message': 'Review simulation completed',
                'decision': result.get('consensus_decision')
            }), 200

        flash(f'Review simulation completed: {result["consensus_decision"]}', 'success')
        return redirect(url_for('dashboard.paper_detail', paper_id=paper_id))

    except Exception as e:
        logger.error(f"Error simulating review: {str(e)}")
        if request.is_json or request.headers.get('Content-Type') == 'application/json':
            return jsonify({'error': str(e)}), 500
        flash('Error during review simulation', 'error')
        return redirect(url_for('dashboard.paper_detail', paper_id=paper_id))

@dashboard_bp.route('/upload')
@login_required
def upload_home():
    """Display upload method selection."""
    return render_template('upload_home.html')

@dashboard_bp.route('/upload/json')
@login_required
def upload_json():
    """JSON upload page."""
    return render_template('upload_json.html')

@dashboard_bp.route('/upload/pdf')
@login_required
def upload_pdf():
    """PDF upload page."""
    return render_template('upload_pdf.html')

@dashboard_bp.route('/upload/api')
@login_required
def upload_api():
    """API fetch upload page."""
    return render_template('upload_api.html')



@dashboard_bp.route('/analytics')
@login_required
def advanced_analytics():
    """Advanced analytics page."""
    return render_template('advanced_analytics.html')

@dashboard_bp.route('/login')
def login_page():
    """Login page."""
    return render_template('login.html')

@dashboard_bp.route('/register')
def register_page():
    """Registration page."""
    return render_template('register.html')

@dashboard_bp.route('/reviewers')
@login_required
def reviewer_builder():
    """Custom reviewer builder page."""
    return render_template('reviewer_builder.html')

@dashboard_bp.route('/dashboard')
@login_required
def user_dashboard():
    """User personal dashboard."""
    user = get_current_user()
    try:
        # Get papers with review status
        papers = Paper.objects(user_id=str(user.id)).limit(100)
        paper_ids = [p.id for p in papers]
        reviews = Review.objects(paper__in=paper_ids)
        consensus_data = Consensus.objects(paper__in=paper_ids)
        
        # Calculate statistics
        total_papers = papers.count()
        reviewed_papers = consensus_data.count()
        pending_papers = total_papers - reviewed_papers
        
        # Get recent activity
        recent_papers = papers.order_by('-id')[:10]
        
        return render_template('results_dashboard.html',
                             total_papers=total_papers,
                             reviewed_papers=reviewed_papers,
                             pending_papers=pending_papers,
                             recent_papers=[p.to_dict() for p in recent_papers],
                             consensus_data=[c.to_dict() for c in consensus_data])
    except Exception as e:
        logger.error(f"Error loading user dashboard: {str(e)}")
        return render_template('results_dashboard.html',
                             total_papers=0, reviewed_papers=0, pending_papers=0,
                             recent_papers=[], consensus_data=[])

@dashboard_bp.route('/')
def home():
    """Home route - redirect to login or dashboard based on auth status."""
    if 'user_id' in session:
        return redirect(url_for('dashboard.results_dashboard'))
    return redirect(url_for('dashboard.login_page'))

@dashboard_bp.route('/dashboard')
@login_required
def results_dashboard():
    """Main dashboard - Results and analytics."""
    user = get_current_user()
    try:
        # Get papers with review status
        papers = Paper.objects(user_id=str(user.id)).limit(100)
        paper_ids = [p.id for p in papers]
        reviews = Review.objects(paper__in=paper_ids)
        consensus_data = Consensus.objects(paper__in=paper_ids)
        
        # Calculate statistics
        total_papers = papers.count()
        reviewed_papers = consensus_data.count()
        pending_papers = total_papers - reviewed_papers
        
        # Get recent activity
        recent_papers = papers.order_by('-id')[:10]
        
        return render_template('results_dashboard.html',
                             total_papers=total_papers,
                             reviewed_papers=reviewed_papers,
                             pending_papers=pending_papers,
                             recent_papers=[p.to_dict() for p in recent_papers],
                             consensus_data=[c.to_dict() for c in consensus_data])
    except Exception as e:
        logger.error(f"Error loading results dashboard: {str(e)}")
        return render_template('results_dashboard.html',
                             total_papers=0, reviewed_papers=0, pending_papers=0,
                             recent_papers=[], consensus_data=[])
