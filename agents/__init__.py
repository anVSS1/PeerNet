'''
PeerNet++ Agents Module
=======================
AI agent implementations for the peer review simulation.

Agents:
- ReviewerAgent: Generates paper reviews using DSPy + Groq/Gemma
- ConsensusAgent: Builds consensus from multiple reviews using Gemini
- PlagiarismAgent: Detects similar papers using vector embeddings
- BiasDetectionAgent: Statistical bias detection in reviews
- GeminiAgent: Legacy text analysis (deprecated)

All agents inherit from BaseAgent for consistent interface.
'''