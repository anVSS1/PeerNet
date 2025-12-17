'''
PeerNet++ Papers API
====================
REST API endpoints for paper management.

Endpoints:
- GET /papers: List all papers (with pagination)
- GET /papers/<id>: Get paper details
- POST /papers: Upload new paper (PDF/JSON)
- DELETE /papers/<id>: Remove paper
- GET /papers/<id>/report: Download PDF review report

Paper Upload Pipeline:
1. PDF extraction (Gemini Vision / Groq Llama 4 Scout)
2. Embedding generation (text-embedding-004)
3. Plagiarism check (MongoDB vector search)
4. Auto-review (5 AI reviewers + consensus)
'''

from flask import Blueprint, request, jsonify, send_file
from models.papers import Paper
from models.reviews import Review
from data_collection.paper_intake import PaperIntake
from utils.logger import get_logger
from utils.pdf_generator import ReviewReportGenerator
import json
from utils.auth_middleware import get_current_user
from extensions import socketio

papers_bp = Blueprint('papers', __name__)
logger = get_logger(__name__)

@papers_bp.route('', methods=['GET'])
def get_papers():
    """Get all papers with optional search and status filter."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        search = request.args.get('search', '')
        status = request.args.get('status', '')  # pending, reviewed, all
        limit = int(request.args.get('limit', 50))

        # Start with user filter
        papers_query = Paper.objects(user_id=str(user.id))
        
        # Add search filter first
        if search:
            from mongoengine import Q
            papers_query = papers_query.filter(
                Q(title__icontains=search) | 
                Q(authors__icontains=search) | 
                Q(abstract__icontains=search)
            )

        # Get all papers matching criteria
        all_papers = papers_query.limit(limit)
        
        # Filter by review status if needed
        if status == 'pending':
            # Filter papers that have no reviews
            papers_list = []
            for paper in all_papers:
                review_count = Review.objects(paper=paper).count()
                if review_count == 0:
                    papers_list.append(paper.to_dict())
        elif status == 'reviewed':
            # Filter papers that have at least one review
            papers_list = []
            for paper in all_papers:
                review_count = Review.objects(paper=paper).count()
                if review_count > 0:
                    papers_list.append(paper.to_dict())
        else:
            # Return all papers
            papers_list = [paper.to_dict() for paper in all_papers]
        
        return jsonify({
            'papers': papers_list,
            'count': len(papers_list)
        })
    except Exception as e:
        logger.error(f"Error getting papers: {str(e)}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

@papers_bp.route('/<paper_id>', methods=['GET'])
def get_paper(paper_id):
    """Get a specific paper by ID."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        paper = Paper.objects(paper_id=paper_id, user_id=str(user.id)).first()
        if not paper:
            return jsonify({'error': 'Paper not found'}), 404

        return jsonify(paper.to_dict())
    except Exception as e:
        logger.error(f"Error getting paper {paper_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@papers_bp.route('', methods=['POST'])
def create_paper():
    user = get_current_user()
    """Create a new paper from JSON or file upload."""
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        # Handle file upload (PDF)
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # Save file temporarily and process
            import os
            import tempfile
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                file.save(temp_file.name)
                temp_path = temp_file.name
            
            try:
                intake = PaperIntake()
                # Load user's saved reviewer preferences
                prefs = user.preferences.get('reviewer_config', {
                    'num_reviewers': 5,
                    'selected_reviewers': []
                })

                paper = intake.intake_single_paper(
                    source='pdf', 
                    data=temp_path, 
                    user_id=str(user.id),
                    num_reviewers=prefs['num_reviewers'],
                    custom_reviewer_ids=prefs['selected_reviewers']
                )
                
                if paper:
                    # Emit real-time notification
                    try:
                        socketio.emit('upload_progress', {
                            'paper_id': paper.paper_id,
                            'paper_title': paper.title,
                            'message': f'PDF "{paper.title}" uploaded successfully',
                            'status': 'success'
                        }, room=str(user.id))
                    except Exception as e:
                        logger.debug(f"SocketIO notification failed: {str(e)}")
                    
                    return jsonify({
                        'message': 'Paper created successfully from PDF',
                        'paper': paper.to_dict()
                    }), 201
                else:
                    return jsonify({'error': 'Failed to process PDF file. Paper may have been rejected for plagiarism.'}), 400
            except Exception as e:
                logger.error(f"Error processing PDF: {str(e)}")
                return jsonify({'error': f'Failed to process PDF: {str(e)}'}), 500
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass  # File already deleted or in use
        
        # Handle JSON data
        elif request.is_json:
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400

            source = data.get('source', 'json')
            source_data = data.get('data', data)

            # Validate required fields for JSON source
            if source == 'json' and isinstance(source_data, dict):
                if not source_data.get('title'):
                    return jsonify({'error': 'Missing required field: title'}), 400
                # paper_id is auto-generated if not provided

            intake = PaperIntake()
            logger.debug(f"Processing paper from source: {source}")
            paper = intake.intake_single_paper(source, source_data, user_id=str(user.id))

            if paper:
                # Emit real-time notification
                try:
                    socketio.emit('upload_progress', {
                        'paper_id': paper.paper_id,
                        'paper_title': paper.title,
                        'message': f'Paper "{paper.title}" uploaded successfully',
                        'status': 'success'
                    }, room=str(user.id))
                except Exception as e:
                    logger.debug(f"SocketIO notification failed: {str(e)}")
                
                return jsonify({
                    'message': 'Paper created successfully',
                    'paper': paper.to_dict()
                }), 201
            else:
                return jsonify({'error': 'Failed to create paper - invalid data or processing error'}), 400
        
        # Handle form data (API fetch)
        elif request.form:
            form_data = request.form.to_dict()
            source = form_data.get('source', 'openalex')
            paper_id = form_data.get('paper_id', '')
            
            # Load user's saved reviewer preferences
            prefs = user.preferences.get('reviewer_config', {
                'num_reviewers': 5,
                'selected_reviewers': []
            })
            
            intake = PaperIntake()
            paper = intake.intake_single_paper(source, paper_id, user_id=str(user.id),
                                             num_reviewers=prefs['num_reviewers'], 
                                             custom_reviewer_ids=prefs['selected_reviewers'])
            
            if paper:
                # Emit real-time notification
                try:
                    socketio.emit('upload_progress', {
                        'paper_id': paper.paper_id,
                        'paper_title': paper.title,
                        'message': f'Paper "{paper.title}" fetched successfully',
                        'status': 'success'
                    }, room=str(user.id))
                except Exception as e:
                    logger.debug(f"SocketIO notification failed: {str(e)}")
                
                return jsonify({
                    'message': 'Paper created successfully',
                    'paper': paper.to_dict()
                }), 201
            else:
                return jsonify({'error': 'Failed to create paper from form data'}), 400
        
        else:
            return jsonify({'error': 'No valid data provided'}), 400

    except ValueError as e:
        logger.error(f"Validation error creating paper: {str(e)}")
        return jsonify({'error': f'Validation error: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Error creating paper: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@papers_bp.route('/<paper_id>/export-pdf', methods=['GET'])
def export_paper_pdf(paper_id):
    """Export paper review report as PDF."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        # Verify paper exists and belongs to user
        paper = Paper.objects(paper_id=paper_id, user_id=str(user.id)).first()
        if not paper:
            return jsonify({'error': 'Paper not found'}), 404
        
        # Generate PDF report
        generator = ReviewReportGenerator()
        pdf_buffer = generator.generate_report(paper_id)
        
        # Create safe filename
        safe_title = ''.join(c for c in paper.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"review_report_{safe_title[:50]}_{paper_id}.pdf"
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except ValueError as e:
        logger.error(f"Validation error exporting PDF for {paper_id}: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error exporting PDF for {paper_id}: {str(e)}")
        return jsonify({'error': 'Failed to generate PDF report'}), 500
