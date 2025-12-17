# PeerNet++ V3.0

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)](https://flask.palletsprojects.com/)

> **AI-Powered Academic Peer Review System - 2025 SOTA Multi-Provider Stack**

Revolutionizes academic paper evaluation through intelligent automation, custom reviewer personalities, plagiarism-first architecture, and blockchain-style audit trails.

## 🆕 What's New in V3.0

- 🔬 **Gemini 2.0 Flash** for PDF Vision extraction
- 🤖 **Groq Llama 3.1 8B** for lightning-fast reviews (560 tok/sec)
- 🧠 **Gemini 2.5 Flash Thinking** for consensus with reasoning
- 📊 **text-embedding-004** for plagiarism detection
- 🔄 **Gemma 3 27B Fallback** via OpenRouter (FREE!)
- ⚡ **Plagiarism-First Architecture** - Rejects before wasting API calls
- 📡 **Real-time WebSocket Progress** with step-by-step live logs

## 🛠️ Tech Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| PDF Extraction | Gemini 2.0 Flash Lite | Vision-based text + figure extraction |
| Embeddings | text-embedding-004 | 768-dim vectors for similarity |
| Reviews | Groq Llama 3.1 8B | Fast inference (560 tok/sec) |
| Consensus | Gemini 2.5 Flash | Built-in reasoning capabilities |
| Fallback | Gemma 3 27B (OpenRouter) | FREE fallback when rate limited |
| Database | MongoDB Atlas | Cloud-hosted document store |
| Real-time | Flask-SocketIO | Live progress updates |

## 🚀 Features

### 📄 **Multi-Modal Paper Upload**
- **PDF Upload**: AI-powered vision extraction with figure descriptions
- **JSON Upload**: Direct structured metadata input
- **API Integration**: arXiv, PubMed, Semantic Scholar, OpenAlex

### 🔍 **Plagiarism-First Architecture**
- Papers checked **BEFORE** reviews (saves API costs!)
- 85% similarity threshold auto-rejects duplicates
- Cosine similarity on 768-dim embeddings

### 🤖 **Multi-Provider AI Reviews**
- **Primary**: Groq Llama 3.1 8B (DSPy optimized)
- **Fallback 1**: Groq direct API
- **Fallback 2**: Gemma 3 27B via OpenRouter (FREE)
- 5 reviewer personalities: Methodology, Innovation, Communication, Theory, Application

### 👤 **Custom Reviewer Builder**
Create personalized AI reviewers with 6 adjustable traits:
- Strictness (Lenient ↔ Harsh)
- Detail Focus (Big Picture ↔ Nitpicky)
- Innovation Bias (Conservative ↔ Novelty-seeking)
- Writing Standards (Relaxed ↔ Perfectionist)
- Methodology Rigor (Flexible ↔ Statistical Purist)
- Optimism (Critical ↔ Encouraging)

### 📊 **Advanced Features**
- **Real-time Dashboard**: Live progress with emojis and step numbers
- **Bias Detection**: Automated identification and flagging
- **Blockchain Ledger**: Immutable SHA-256 audit trail
- **PDF Report Export**: Download complete review reports

## 🛠️ Quick Start

1. **Clone & Setup**
   ```bash
   git clone https://github.com/anVSS1/PeerNet.git
   cd PeerNet
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Required API Keys** (all have free tiers!)
   - [Google AI Studio](https://aistudio.google.com/apikey) - Gemini API
   - [Groq Console](https://console.groq.com/keys) - Groq API
   - [OpenRouter](https://openrouter.ai/keys) - Gemma fallback
   - [MongoDB Atlas](https://cloud.mongodb.com) - Database

4. **Run**
   ```bash
   python app.py
   # Visit: http://127.0.0.1:5000
   ```

## ⚙️ Configuration

Edit `.env` file:

```env
# MongoDB Atlas
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/peernet_plus

# Google Gemini (Vision + Embeddings + Consensus)
GEMINI_API_KEY=your_gemini_key
GEMINI_VISION_MODEL=gemini-2.0-flash-lite
GEMINI_EMBEDDING_MODEL=text-embedding-004
GEMINI_THINKING_MODEL=gemini-2.5-flash

# Groq (Reviews - 560 tokens/sec!)
GROQ_API_KEY=your_groq_key
GROQ_MODEL=llama-3.1-8b-instant

# OpenRouter (Gemma 3 Fallback - FREE!)
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=google/gemma-3-27b-it:free

# Plagiarism Threshold
PLAGIARISM_SIMILARITY_THRESHOLD=0.85

# Review Settings
MIN_REVIEWERS=3
MAX_REVIEWERS=5
```

## 📁 Project Structure

```
PeerNet++/
├── agents/              # AI Review Agents
│   ├── reviewer_agent.py   # DSPy + Groq + Gemma fallback
│   ├── consensus_agent.py  # Gemini 2.5 Flash Thinking
│   ├── bias_detection_agent.py
│   └── plagiarism_agent.py
├── api/                 # REST API Endpoints
├── dashboard/           # Web Interface & Templates
├── data_collection/     # Paper Intake System
│   ├── pdf_parser.py       # Gemini Vision extraction
│   ├── paper_intake.py     # Plagiarism-first pipeline
│   ├── arxiv_fetcher.py
│   ├── pubmed_fetcher.py
│   └── semantic_fetcher.py
├── models/              # MongoDB Models
├── simulation/          # Review Orchestration
├── utils/               # Utilities & Security
├── app.py               # Main Flask Application
└── requirements.txt
```

## 🎯 How It Works

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  1. Upload  │───▶│ 2. Extract   │───▶│ 3. Embed    │
│  PDF/JSON   │    │ Gemini Vision│    │ text-emb-004│
└─────────────┘    └──────────────┘    └─────────────┘
                                              │
                                              ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│ 6. Consensus│◀───│ 5. Reviews   │◀───│4. Plagiarism│
│Gemini 2.5   │    │ Groq/Gemma   │    │ Check FIRST │
└─────────────┘    └──────────────┘    └─────────────┘
       │                                     │
       ▼                                     ▼
┌─────────────┐                       ┌─────────────┐
│ 7. Bias     │                       │  REJECT if  │
│ Detection   │                       │  >85% match │
└─────────────┘                       └─────────────┘
```

## 📡 Live Progress Logs

Real-time WebSocket updates show:
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

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -m 'Add feature'`
4. Push branch: `git push origin feature-name`
5. Open Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 👥 Team

- **Anass Ouzaouit** - [GitHub](https://github.com/anVSS1) | [LinkedIn](https://www.linkedin.com/in/anass-ouzaouit)
- **Abdelaziz Afquir** - [GitHub](https://github.com/Abdelaazizafquir) | [LinkedIn](https://www.linkedin.com/in/abdelaziz-afquir-285514351)
- **Mohamed Kannoun** - [GitHub](https://github.com/kannoun) | [LinkedIn](https://www.linkedin.com/in/kannoun)

## 🙏 Acknowledgments

Built with:
- [Google Gemini](https://ai.google.dev/) - Vision, Embeddings, Consensus
- [Groq](https://groq.com/) - Ultra-fast LLM inference
- [OpenRouter](https://openrouter.ai/) - Gemma 3 fallback
- [MongoDB Atlas](https://www.mongodb.com/atlas) - Cloud database
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [DSPy](https://github.com/stanfordnlp/dspy) - LLM optimization

---

**Made with ❤️ for the academic community**

**Version**: 3.0.0 | **Last Updated**: December 2025
