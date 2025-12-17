'''
PeerNet++ Data Collection Module
================================
Paper data ingestion from various sources.

Fetchers:
- arxiv_fetcher: arXiv.org API
- pubmed_fetcher: PubMed API
- semantic_fetcher: Semantic Scholar API
- openalex_fetcher: OpenAlex API

Parsers:
- pdf_parser: Extract text from PDFs using Gemini/Groq Vision
- json_handler: Parse JSON paper metadata

Intake:
- paper_intake: Main entry point for paper processing
'''