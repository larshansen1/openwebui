#!/bin/bash
set -e

# Start Ollama in the background
/bin/ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama service to be ready..."
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 1
done

echo "Ollama service is ready!"

# Set default embedding model if not provided
EMBEDDING_MODEL=${EMBEDDING_MODEL:-nomic-embed-text}

# Pull the embedding model if it doesn't exist
echo "Checking for ${EMBEDDING_MODEL} model..."
if ! ollama list | grep -q "${EMBEDDING_MODEL}"; then
    echo "Pulling ${EMBEDDING_MODEL} model..."
    ollama pull "${EMBEDDING_MODEL}"
    echo "${EMBEDDING_MODEL} model pulled successfully!"
else
    echo "${EMBEDDING_MODEL} model already exists."
fi

# Keep the Ollama service running in the foreground
wait $OLLAMA_PID
