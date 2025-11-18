import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Blueprint, request, jsonify
from models.papers import Paper
from models.reviews import Review
from models.consensus import Consensus
from utils.logger import get_logger
import re

logger = get_logger(__name__)

search_bp = Blueprint('search', __name__)

@search_bp.route('/papers', methods=['GET'])
def search_papers():
    """Advanced paper search with multiple filters."""
    try:
        # Get search parameters
        query = request.args.get('q', '').strip()
        status = request.args.get('status', '')  # pending, reviewed, accepted, rejected
        source = request.args.get('source', '')  # pdf, json, openalex
        year_from = request.args.get('year_from', '')
        year_to = request.args.get('year_to', '')
        author = request.args.get('author', '').strip()
        sort_by = request.args.get('sort', 'created_at')  # created_at, title, year
        order = request.args.get('order', 'desc')  # asc, desc
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)  # Max 100 per page
        
        # Build MongoDB query
        filters = {}
        
        # Text search in title, abstract, authors
        if query:
            safe_query = re.escape(query)
            filters['$or'] = [
                {'title': {'$regex': safe_query, '$options': 'i'}},
                {'abstract': {'$regex': safe_query, '$options': 'i'}},
                {'authors': {'$regex': safe_query, '$options': 'i'}},
                {'keywords': {'$regex': safe_query, '$options': 'i'}}
            ]
        
        # Source filter
        if source:
            filters['source'] = source
        
        # Year range filter
        if year_from:
            try:
                filters['year__gte'] = str(int(year_from))
            except ValueError:
                pass
        
        if year_to:
            try:
                filters['year__lte'] = str(int(year_to))
            except ValueError:
                pass
        
        # Author filter
        if author:
            safe_author = re.escape(author)
            filters['authors'] = {'$regex': safe_author, '$options': 'i'}
        
        # Get papers with filters
        papers_query = Paper.objects(**filters)
        
        # Apply sorting
        sort_field = sort_by if sort_by in ['title', 'year', 'created_at'] else 'created_at'
        if order == 'asc':
            papers_query = papers_query.order_by(f'+{sort_field}')
        else:
            papers_query = papers_query.order_by(f'-{sort_field}')
        
        # Get total count
        total_count = papers_query.count()
        
        # Apply pagination
        skip = (page - 1) * per_page
        papers = papers_query.skip(skip).limit(per_page)
        
        # Enhance results with review status
        results = []
        for paper in papers:
            paper_dict = paper.to_dict()
            
            # Add review status
            consensus = Consensus.objects(paper=paper).first()
            if consensus:
                paper_dict['review_status'] = 'reviewed'
                paper_dict['decision'] = consensus.decision
                paper_dict['overall_score'] = consensus.final_scores.get('overall', 0)
            else:
                paper_dict['review_status'] = 'pending'
                paper_dict['decision'] = None
                paper_dict['overall_score'] = None
            
            # Filter by status if requested
            if status:
                if status == 'pending' and paper_dict['review_status'] != 'pending':
                    continue
                elif status == 'reviewed' and paper_dict['review_status'] != 'reviewed':
                    continue
                elif status in ['accepted', 'rejected'] and paper_dict.get('decision', '').lower() != status:
                    continue
            
            results.append(paper_dict)
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        return jsonify({
            'papers': results,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'total_pages': total_pages,
                'has_next': has_next,
                'has_prev': has_prev
            },
            'filters_applied': {
                'query': query,
                'status': status,
                'source': source,
                'year_from': year_from,
                'year_to': year_to,
                'author': author,
                'sort_by': sort_by,
                'order': order
            }
        })
        
    except Exception as e:
        logger.error(f"Error in paper search: {str(e)}")
        return jsonify({'error': 'Search failed'}), 500

@search_bp.route('/suggestions', methods=['GET'])
def get_search_suggestions():
    """Get search suggestions for autocomplete."""
    try:
        query = request.args.get('q', '').strip()
        if len(query) < 2:
            return jsonify({'suggestions': []})
        
        safe_query = re.escape(query)
        
        # Get title suggestions
        title_matches = Paper.objects(title__iregex=safe_query).limit(5)
        title_suggestions = [paper.title for paper in title_matches]
        
        # Get author suggestions
        author_matches = Paper.objects(authors__iregex=safe_query).limit(5)
        author_suggestions = []
        for paper in author_matches:
            for author in paper.authors:
                if query.lower() in author.lower() and author not in author_suggestions:
                    author_suggestions.append(author)
                    if len(author_suggestions) >= 5:
                        break
        
        return jsonify({
            'suggestions': {
                'titles': title_suggestions[:5],
                'authors': author_suggestions[:5]
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting search suggestions: {str(e)}")
        return jsonify({'suggestions': {'titles': [], 'authors': []}})

@search_bp.route('/filters', methods=['GET'])
def get_filter_options():
    """Get available filter options for search."""
    try:
        # Get unique sources
        sources = Paper.objects().distinct('source')
        
        # Get year range
        years = [paper.year for paper in Paper.objects() if paper.year and paper.year.isdigit()]
        year_range = {
            'min': min(years) if years else None,
            'max': max(years) if years else None
        }
        
        # Get common authors (top 20)
        all_authors = []
        for paper in Paper.objects():
            all_authors.extend(paper.authors)
        
        author_counts = {}
        for author in all_authors:
            author_counts[author] = author_counts.get(author, 0) + 1
        
        top_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:20]
        
        return jsonify({
            'sources': sources,
            'year_range': year_range,
            'top_authors': [author for author, count in top_authors],
            'status_options': ['pending', 'reviewed', 'accepted', 'rejected'],
            'sort_options': ['created_at', 'title', 'year']
        })
        
    except Exception as e:
        logger.error(f"Error getting filter options: {str(e)}")
        return jsonify({'error': 'Failed to get filter options'}), 500