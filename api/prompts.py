from flask import Blueprint, jsonify

# Define the templates for reviewers
reviewer_templates = [
    {
        'id': 'dr_methodology',
        'name': 'Dr. Methodology',
        'avatar': 'scientist',
        'expertise': 'methodology',
        'description': 'Focuses on the rigor and validity of the experimental design and statistical analysis. Very strict about methodological flaws.',
        'strictness': 0.8,
        'detail_focus': 0.9,
        'innovation_bias': 0.2,
        'writing_standards': 0.6,
        'methodology_rigor': 0.9,
        'optimism': 0.3
    },
    {
        'id': 'prof_novelty',
        'name': 'Prof. Novelty',
        'avatar': 'explorer',
        'expertise': 'novelty',
        'description': 'Prioritizes groundbreaking ideas and innovative approaches. Forgiving of minor flaws if the core idea is exciting.',
        'strictness': 0.4,
        'detail_focus': 0.5,
        'innovation_bias': 0.9,
        'writing_standards': 0.5,
        'methodology_rigor': 0.4,
        'optimism': 0.8
    },
    {
        'id': 'dr_clarity',
        'name': 'Dr. Clarity',
        'avatar': 'writer',
        'expertise': 'clarity',
        'description': 'Emphasizes clear, concise, and well-structured writing. Believes good ideas are lost in bad prose.',
        'strictness': 0.6,
        'detail_focus': 0.8,
        'innovation_bias': 0.4,
        'writing_standards': 0.9,
        'methodology_rigor': 0.6,
        'optimism': 0.6
    },
    {
        'id': 'prof_theory',
        'name': 'Prof. Theory',
        'avatar': 'philosopher',
        'expertise': 'theory',
        'description': 'Concerned with the theoretical underpinnings and conceptual soundness of the work. Likes to see a strong theoretical framework.',
        'strictness': 0.7,
        'detail_focus': 0.6,
        'innovation_bias': 0.6,
        'writing_standards': 0.7,
        'methodology_rigor': 0.8,
        'optimism': 0.5
    },
    {
        'id': 'dr_practical',
        'name': 'Dr. Practical',
        'avatar': 'engineer',
        'expertise': 'application',
        'description': 'Looks for real-world applications and practical implications. Is the work useful and impactful?',
        'strictness': 0.5,
        'detail_focus': 0.4,
        'innovation_bias': 0.7,
        'writing_standards': 0.6,
        'methodology_rigor': 0.5,
        'optimism': 0.7
    }
]

# Create a Blueprint for the prompts
prompts_bp = Blueprint('prompts', __name__)

@prompts_bp.route('/reviewer_templates', methods=['GET'])
def get_reviewer_templates():
    """Returns the list of default reviewer templates."""
    return jsonify({'templates': reviewer_templates}), 200
