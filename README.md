# PeerNet++ 

A decentralized peer review system powered by AI agents and blockchain-style ledger technology.

## Features

- **AI-Powered Review System**: Automated peer review using advanced language models
- **Bias Detection**: Built-in algorithms to detect and flag potential biases
- **Consensus Mechanism**: Multi-agent consensus for fair review decisions  
- **Blockchain Ledger**: Immutable audit trail of all review activities
- **Web Interface**: User-friendly dashboard for paper management
- **Batch Processing**: Upload and process multiple papers simultaneously

## Quick Start

### Prerequisites
- Python 3.8+
- MongoDB
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd PeerNett
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   copy .env.example .env
   # Edit .env with your configuration
   ```

4. **Start MongoDB**
   ```bash
   # Make sure MongoDB is running on localhost:27017
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the web interface**
   ```
   http://127.0.0.1:5000
   ```

## Configuration

Edit `.env` file with your settings:

```env
# MongoDB Configuration
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_DB=peernet_plus

# Hugging Face API Key (optional, for AI reviews)
HF_API_KEY=your_huggingface_api_key_here

# Review Configuration
MIN_REVIEWERS=3
MAX_REVIEWERS=5

# Flask Configuration
SECRET_KEY=your_secret_key_here
DEBUG=False

# Logging
LOG_LEVEL=INFO
```

## Usage

### Web Interface
1. Navigate to `http://127.0.0.1:5000`
2. Click "Batch Upload" to upload papers
3. View papers and their review status on the main dashboard

### API Endpoints

#### Upload Single Paper
```bash
POST /api/papers
Content-Type: application/json

{
  "source": "json",
  "data": {
    "paper_id": "example1",
    "title": "Example Paper",
    "authors": ["Author One"],
    "year": 2024,
    "abstract": "Paper abstract...",
    "doi": "10.1000/example"
  }
}
```

#### Batch Upload
```bash
POST /api/batch
Content-Type: application/json

{
  "papers": [
    {
      "source": "json",
      "data": {
        "paper_id": "example1",
        "title": "Example Paper 1",
        "authors": ["Author One"],
        "year": 2024,
        "abstract": "Abstract...",
        "doi": "10.1000/example1"
      }
    }
  ]
}
```

#### Get Papers
```bash
GET /api/papers?search=keyword&limit=50
```

## Project Structure

```
PeerNett/
├── agents/              # AI review agents
├── api/                 # REST API endpoints
├── dashboard/           # Web interface
├── data_collection/     # Paper intake modules
├── models/              # Database models
├── simulation/          # Review simulation engine
├── utils/               # Utility functions
├── app.py              # Main application
├── config.py           # Configuration
└── requirements.txt    # Dependencies
```

## Security

This application implements multiple security measures:
- Input sanitization to prevent injection attacks
- Path validation to prevent traversal attacks
- Secure dependency versions
- Proper error handling and logging

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions, please create an issue in the repository.