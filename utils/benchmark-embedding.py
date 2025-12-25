#!/usr/bin/env python3
"""
Benchmark script for Ollama embedding models
Usage: docker compose exec openwebui python3 /app/benchmark-embedding.py [model_name] [text_size]
"""
import time
import requests
import sys
import os

model = sys.argv[1] if len(sys.argv) > 1 else os.getenv('RAG_EMBEDDING_MODEL', 'nomic-embed-text')
text_multiplier = int(sys.argv[2]) if len(sys.argv) > 2 else 100
ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')

# Create test text
base_text = "This is a test sentence to benchmark the embedding model performance. "
text = base_text * text_multiplier
word_count = len(text.split())
token_count = int(word_count * 1.3)  # Rough estimate: ~1.3 tokens per word

print(f"=" * 60)
print(f"Ollama Embedding Benchmark")
print(f"=" * 60)
print(f"Model: {model}")
print(f"Ollama URL: {ollama_url}")
print(f"Approximately {token_count} tokens")
print(f"Text length: {len(text)} characters")
print(f"-" * 60)

# Benchmark
start = time.time()
response = requests.post(
    f'{ollama_url}/api/embeddings',
    json={'model': model, 'prompt': text}
)
end = time.time()

duration = end - start
tokens_per_sec = token_count / duration

print(f"Duration: {duration:.3f}s")
print(f"Speed: {tokens_per_sec:.2f} tokens/second")
print(f"Speed: {tokens_per_sec * 60:.0f} tokens/minute")
print(f"=" * 60)

if response.status_code == 200:
    embedding_data = response.json()
    print(f"✓ Success")
    print(f"Embedding dimensions: {len(embedding_data['embedding'])}")
else:
    print(f"✗ Error: {response.text}")
    sys.exit(1)
