# PeerNet++

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)

> **AI-Powered Academic Peer Review System**

Revolutionizes academic paper evaluation through intelligent automation, custom reviewer personalities, and blockchain-style audit trails.

## 🚀 Features

### 📄 **Multi-Modal Paper Upload**

- **PDF Upload**: Automatic text extraction and AI-powered metadata parsing
- **JSON Upload**: Direct structured metadata input for bulk imports
- **API Integration**: Fetch papers from arXiv, PubMed, Semantic Scholar

### 🤖 **Customizable AI Review System**

- **Choose Number of Reviewers**: Select 3-7 reviewers per paper
- **5 Built-in Reviewer Types**: Methodology, Innovation, Communication, Theory, Application
- **Custom Reviewer Builder**: Create personalized AI reviewers with 6 adjustable traits:
  - Strictness (Lenient ↔ Harsh)
  - Detail Focus (Big Picture ↔ Nitpicky)
  - Innovation Bias (Conservative ↔ Novelty-seeking)
  - Writing Standards (Relaxed ↔ Perfectionist)
  - Methodology Rigor (Flexible ↔ Statistical Purist)
  - Optimism (Critical ↔ Encouraging)

### 👤 **Pre-built Reviewer Templates**

- **The Encourager**: Supportive, constructive feedback
- **The Perfectionist**: High standards, detailed critiques
- **The Innovator**: Values novelty and creativity
- **The Traditionalist**: Emphasizes established methods

### 📊 **Advanced Features**

- **Real-time Dashboard**: Paper tracking, analytics, and review progress
- **Reviewer Configuration**: Save preferred reviewer combinations
- **Bias Detection**: Automated identification and mitigation
- **Blockchain-style Ledger**: Immutable audit trail
- **WebSocket Notifications**: Real-time upload and review updates

## 🛠️ Quick Start

1. **Clone & Setup**

   ```bash
   git clone https://github.com/anVSS1/PeerNet.git
   cd PeerNet
   python -m venv venv
   venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

2. **Configure**

   ```bash
   cp .env.example .env
   # Edit .env with your MongoDB and API keys
   ```

3. **Run**
   ```bash
   python app.py
   # Visit: http://127.0.0.1:5000
   ```

## ⚙️ Configuration

Edit `.env` file:

```env
# Database
MONGODB_HOST=localhost
MONGODB_DB=peernet_plus

# API Keys (optional but recommended)
HF_API_KEY=your_huggingface_key
GEMINI_API_KEY=your_gemini_key

# Review Settings
MIN_REVIEWERS=3
MAX_REVIEWERS=5
REVIEWER_COUNT=4

# App Settings
SECRET_KEY=your_secret_key
DEBUG=True
```

## 📖 Usage

### Web Interface

1. **Register/Login** at http://127.0.0.1:5000
2. **Configure Reviewers**:
   - Choose number of reviewers (3-5)
   - Select built-in personalities or create custom ones
   - Save your preferred configuration
3. **Upload Papers**:
   - PDF files with automatic extraction
   - JSON data for structured input
   - API fetch from arXiv, PubMed, Semantic Scholar
4. **Monitor Progress**: Real-time dashboard with review status
5. **View Results**: Detailed reviews with consensus scoring

### Custom Reviewer Creation

```javascript
// Example reviewer personality
{
  "name": "Dr. Strict Methodologist",
  "expertise": "methodology",
  "strictness": 0.9,
  "detail_focus": 0.8,
  "innovation_bias": 0.3,
  "writing_standards": 0.7,
  "methodology_rigor": 1.0,
  "optimism": 0.4
}
```

### API Endpoints

```bash
# Upload paper
POST /api/papers
{
  "paper_id": "unique_id",
  "title": "Paper Title",
  "abstract": "Abstract text...",
  "authors": ["Author 1", "Author 2"]
}

# Create custom reviewer
POST /api/reviewers
{
  "name": "Custom Reviewer",
  "expertise": "methodology",
  "strictness": 0.7,
  "detail_focus": 0.6
}

# Save reviewer preferences
POST /api/reviewers/preferences
{
  "num_reviewers": 5,
  "selected_reviewers": ["reviewer_id_1", "reviewer_id_2"]
}
```

## 📁 Project Structure

```
PeerNet++/
├── agents/              # AI Review Agents & Consensus Building
├── api/                 # REST API Endpoints
├── dashboard/           # Web Interface & Templates
├── data_collection/     # Multi-source Paper Intake
│   ├── pdf_parser.py    # PDF text extraction
│   ├── arxiv_fetcher.py # arXiv API integration
│   ├── pubmed_fetcher.py# PubMed API integration
│   └── semantic_fetcher.py # Semantic Scholar API
├── models/              # Database Models
│   ├── papers.py        # Paper documents
│   ├── custom_reviewers.py # User-created reviewers
│   └── reviews.py       # Review results
├── simulation/          # Review Processing Engine
├── utils/               # Utilities & Security
├── app.py               # Main Flask Application
└── requirements.txt     # Dependencies
```

## 🎯 How It Works

1. **Upload**: Choose from PDF, JSON, or API sources
2. **Configure**: Select number and types of reviewers
3. **Process**: AI agents analyze paper based on their personalities
4. **Consensus**: Multiple reviewers build consensus with confidence scoring
5. **Results**: Detailed feedback with bias detection and audit trail

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m 'Add feature'`
4. Push branch: `git push origin feature-name`
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 📞 Contact

Connect with the development team:

- **Anass Ouzaouit** - [LinkedIn](https://www.linkedin.com/in/anass-ouzaouit)
- **Abdelaziz Afquir** - [LinkedIn](https://www.linkedin.com/in/abdelaziz-afquir-285514351)
- **Mohamed Kannoun** - [LinkedIn](https://www.linkedin.com/in/kannoun)

## 🙏 Acknowledgments

Built with [Flask](https://flask.palletsprojects.com/), [MongoDB](https://www.mongodb.com/), [Hugging Face](https://huggingface.co/), and [Google Gemini](https://ai.google.dev/).

---

**Made with ❤️ for the academic community**
