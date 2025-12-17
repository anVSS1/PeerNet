# PeerNet++ V3.0 - Project Documentation

## Executive Summary

PeerNet++ V3.0 is a comprehensive AI-powered peer review system that revolutionizes academic paper evaluation through a multi-provider AI stack, plagiarism-first architecture, and blockchain-style audit trails. The system combines 2025 state-of-the-art language models with user-centric design to provide transparent, reliable, and personalized academic review experiences.

## System Architecture

### Core Technologies (V3.0 Stack)

| Layer | Technology | Model/Version | Purpose |
|-------|------------|---------------|---------|
| **PDF Extraction** | Google Gemini | gemini-2.0-flash-lite | Vision-based text + figure extraction |
| **Embeddings** | Google Gemini | text-embedding-004 | 768-dim vectors for plagiarism |
| **Reviews** | Groq | Llama 3.1 8B Instant | Fast inference (560 tok/sec) |
| **Consensus** | Google Gemini | gemini-2.5-flash | Built-in reasoning/thinking |
| **Fallback** | OpenRouter | Gemma 3 27B IT (FREE) | Backup when rate limited |
| **Database** | MongoDB Atlas | Cloud | Document storage with embeddings |
| **Real-time** | Flask-SocketIO | WebSocket | Live progress updates |
| **Backend** | Flask | Python 3.8+ | Web framework |
| **Frontend** | Bootstrap 5 | Vanilla JS | Responsive UI |

### Project Structure
```
PeerNet++/
├── agents/                    # AI Review Agents
│   ├── __init__.py           # Module exports
│   ├── base_agent.py         # Abstract base class
│   ├── reviewer_agent.py     # DSPy + Groq + Gemma fallback chain
│   ├── consensus_agent.py    # Gemini 2.5 Flash Thinking
│   ├── bias_detection_agent.py # Bias pattern detection
│   ├── gemini_agent.py       # Gemini API wrapper
│   └── plagiarism_agent.py   # Text similarity analysis
├── api/                      # REST API Endpoints
│   ├── auth.py              # Authentication (login/register/logout)
│   ├── papers.py            # Paper CRUD operations
│   ├── reviews.py           # Review management
│   ├── reviewers.py         # Custom reviewer management
│   ├── consensus.py         # Consensus retrieval
│   ├── analytics.py         # Dashboard metrics
│   ├── search.py            # Advanced search
│   ├── batch.py             # Batch processing
│   ├── ledger.py            # Audit trail
│   ├── bias_flags.py        # Bias flag management
│   └── prompts.py           # Prompt management
├── dashboard/                # Web Interface
│   ├── routes.py            # Route handlers
│   └── templates/           # Jinja2 HTML templates
│       ├── base.html        # Base layout with WebSocket
│       ├── login.html       # User authentication
│       ├── register.html    # Account creation
│       ├── papers_list.html # Paper management
│       ├── paper_detail.html # Review results
│       ├── reviewer_builder.html # Custom reviewer UI
│       ├── advanced_analytics.html # Analytics dashboard
│       └── upload_*.html    # Upload interfaces
├── data_collection/          # Paper Intake System
│   ├── paper_intake.py      # Plagiarism-first pipeline
│   ├── pdf_parser.py        # Gemini Vision extraction
│   ├── json_handler.py      # JSON parsing
│   ├── arxiv_fetcher.py     # arXiv API
│   ├── pubmed_fetcher.py    # PubMed API
│   ├── semantic_fetcher.py  # Semantic Scholar API
│   └── openalex_fetcher.py  # OpenAlex API
├── models/                   # MongoDB Models (MongoEngine)
│   ├── papers.py            # Paper with embeddings
│   ├── reviews.py           # Individual reviews
│   ├── consensus.py         # Final decisions
│   ├── users.py             # User accounts
│   ├── custom_reviewers.py  # User-defined personalities
│   ├── bias_flags.py        # Detected biases
│   ├── ledger_blocks.py     # Blockchain audit trail
│   └── reviewers.py         # Reviewer registry
├── simulation/               # Review Orchestration
│   └── review_simulation.py # Multi-agent coordination
├── utils/                    # Utilities
│   ├── embedding_generator.py # text-embedding-004
│   ├── auth_middleware.py   # Authentication decorators
│   ├── security.py          # Rate limiting, validation
│   ├── logger.py            # Logging configuration
│   ├── ledger.py            # SHA-256 hashing
│   ├── pdf_generator.py     # ReportLab PDF export
│   └── ai_metadata_extractor.py # Metadata parsing
├── static/                   # Static assets
│   └── notifications.js     # In-app notifications
├── app.py                   # Main Flask application
├── config.py                # Configuration management
├── extensions.py            # Flask extensions
├── socketio_events.py       # WebSocket event handlers
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
└── .gitignore              # Git ignore rules
```

## Key Features

### 1. Plagiarism-First Architecture (NEW in V3.0)

The system checks for plagiarism **BEFORE** running expensive AI reviews:

```
Upload → Extract → Embed → PLAGIARISM CHECK → Reviews → Consensus
                              ↓
                         REJECT if >85%
```

**Benefits:**
- Saves API costs by rejecting duplicates early
- Uses cosine similarity on 768-dim embeddings
- Configurable threshold (default: 85%)
- Similar papers listed for transparency

### 2. Multi-Provider AI Stack with Fallback

```python
# Reviewer fallback chain:
1. DSPy + Groq Llama 3.1 8B  →  Primary (optimized prompts)
2. Groq Direct API           →  Fallback 1 (rate limit bypass)
3. Gemma 3 27B (OpenRouter)  →  Fallback 2 (FREE, always works)
```

**Rate Limit Handling:**
- Groq free tier: 6,000 TPM limit
- Automatic retry with exponential backoff
- Seamless failover to next provider

### 3. Real-time Progress Updates

WebSocket-powered live logs with step-by-step progress:

```
🚀 Starting AI review for: Neural Networks for Image...
📋 Step 1/5: Assembling reviewer panel...
👥 3 reviewers assigned: Methodology Expert, Novelty Expert, Clarity Expert
🤖 Step 2/5: Methodology Expert analyzing... (1/3) [Groq Llama 3.1]
🎯 Step 3/5: Building consensus from 3 reviews... [Groq Llama 3.3 70B]
✅ Preliminary decision: Accept (confidence: 85%)
🔍 Step 4/5: Running originality check...
⚖️ Step 5/5: Analyzing for reviewer bias patterns...
🎉 Review complete! ✅ Decision: Accept | 3 reviewers
```

### 4. Custom Reviewer Personalities

6 adjustable traits (0.0 - 1.0):

| Trait | Low Value | High Value |
|-------|-----------|------------|
| Strictness | Lenient | Harsh |
| Detail Focus | Big Picture | Nitpicky |
| Innovation Bias | Conservative | Novelty-seeking |
| Writing Standards | Relaxed | Perfectionist |
| Methodology Rigor | Flexible | Statistical Purist |
| Optimism | Critical | Encouraging |

5 Expertise Areas: Methodology, Novelty, Clarity, Theory, Application

### 5. Blockchain-Style Audit Ledger

Every action creates an immutable block:

```python
{
    'previous_hash': 'abc123...',
    'timestamp': '2025-12-16T10:30:00',
    'data': {
        'event': 'review_generated',
        'reviewer_id': 'methodology_expert',
        'scores': {...}
    },
    'hash': 'def456...'  # SHA-256
}
```

## Technical Implementation

### AI Review Pipeline

1. **Paper Intake** (`data_collection/paper_intake.py`)
   - Multi-format processing (PDF, JSON, API)
   - Gemini Vision for PDF extraction
   - text-embedding-004 for vector generation

2. **Plagiarism Check** (BEFORE reviews)
   - Cosine similarity against all existing papers
   - 85% threshold → auto-reject
   - Returns similar papers list

3. **Agent Initialization** (`agents/reviewer_agent.py`)
   - 3-5 reviewers spawned based on config
   - DSPy signatures for structured output
   - Groq LM for fast inference

4. **Parallel Review** (`simulation/review_simulation.py`)
   - Each agent analyzes independently
   - Fallback chain on failures
   - Real-time progress via WebSocket

5. **Consensus Building** (`agents/consensus_agent.py`)
   - Gemini 2.5 Flash with thinking
   - Multi-round negotiation simulation
   - Confidence scoring

6. **Bias Detection** (`agents/bias_detection_agent.py`)
   - Scoring outlier detection
   - Topic/affiliation bias flags
   - Evidence collection

### Database Schema (MongoDB)

**Papers Collection:**
```javascript
{
  paper_id: String (unique),
  title: String,
  authors: [String],
  abstract: String,
  full_text: String,
  embedding: [Float] (768-dim),
  plagiarism_score: Float,
  similar_papers: [Object],
  status: String (processing|completed|rejected),
  visual_analysis: [Object],
  source: String (pdf|arxiv|pubmed|json)
}
```

**Reviews Collection:**
```javascript
{
  paper: Reference(Paper),
  reviewer_id: String,
  scores: {
    novelty: Float,
    clarity: Float,
    methodology: Float,
    relevance: Float,
    overall: Float
  },
  written_feedback: String,
  confidence: Float,
  logs: String
}
```

**Consensus Collection:**
```javascript
{
  paper: Reference(Paper),
  decision: String (Accept|Minor Revision|Major Revision|Reject),
  negotiation_rounds: [Object],
  final_scores: Object,
  confidence: Float,
  overall_explanation: String
}
```

### Security Measures

- **Authentication**: Session-based with Werkzeug password hashing
- **Rate Limiting**: Configurable per-IP limits
- **Input Validation**: XSS/SQL injection prevention
- **Audit Logging**: Complete activity tracking
- **API Key Protection**: .env excluded from git

## Configuration

### Environment Variables

```env
# MongoDB Atlas (REQUIRED)
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/db

# Google Gemini (REQUIRED)
GEMINI_API_KEY=AIza...
GEMINI_VISION_MODEL=gemini-2.0-flash-lite
GEMINI_EMBEDDING_MODEL=text-embedding-004
GEMINI_THINKING_MODEL=gemini-2.5-flash

# Groq (REQUIRED)
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.1-8b-instant

# OpenRouter (RECOMMENDED - fallback)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=google/gemma-3-27b-it:free

# Plagiarism
PLAGIARISM_SIMILARITY_THRESHOLD=0.85

# Flask
SECRET_KEY=your_secret_key
DEBUG=False
HOST=0.0.0.0
PORT=5000

# Reviewers
MIN_REVIEWERS=3
MAX_REVIEWERS=5
```

### API Keys (All Free Tiers Available)

| Provider | URL | Free Tier |
|----------|-----|-----------|
| Google AI Studio | https://aistudio.google.com/apikey | 15 RPM |
| Groq | https://console.groq.com/keys | 6000 TPM |
| OpenRouter | https://openrouter.ai/keys | Gemma FREE |
| MongoDB Atlas | https://cloud.mongodb.com | 512MB |

## API Documentation

### Authentication
- `POST /api/auth/register` - Create account
- `POST /api/auth/login` - Login
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Current user

### Papers
- `GET /api/papers` - List papers
- `POST /api/papers` - Upload paper
- `GET /api/papers/{id}` - Get paper
- `DELETE /api/papers/{id}` - Delete paper

### Reviews
- `GET /api/reviews/{paper_id}` - Get reviews
- `POST /paper/{id}/simulate` - Start AI review

### Custom Reviewers
- `GET /api/reviewers` - List reviewers
- `POST /api/reviewers` - Create reviewer
- `DELETE /api/reviewers/{id}` - Delete reviewer

### Analytics
- `GET /api/analytics/dashboard` - Dashboard stats
- `GET /api/analytics/trends` - Review trends

## Deployment

### Local Development
```bash
git clone https://github.com/anVSS1/PeerNet.git
cd PeerNet
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
python app.py
```

### Production (Azure VM)
1. Clone repository on VM
2. Set up Python environment
3. Configure .env with production keys
4. Use gunicorn/uwsgi for production server
5. Configure nginx reverse proxy
6. Set up SSL certificate

### Docker (Optional)
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```

## Performance Optimizations

- **Lazy Loading**: Pagination on paper lists
- **Async Reviews**: Non-blocking AI calls
- **Connection Pooling**: MongoDB connection reuse
- **Fallback Chain**: Automatic provider switching
- **Embedding Cache**: Reuse for similar queries

## Future Enhancements

1. **GPT-4/Claude Integration**: Premium review option
2. **Collaborative Reviews**: Multi-user sessions
3. **Journal Integration**: Direct submission APIs
4. **Mobile App**: React Native client
5. **Institutional SSO**: SAML/OAuth support

---

**Project Status**: Production Ready  
**Version**: 3.0.0  
**Last Updated**: December 2025  
**License**: MIT License  
**Repository**: https://github.com/anVSS1/PeerNet
