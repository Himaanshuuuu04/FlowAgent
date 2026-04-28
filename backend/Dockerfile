FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for FAISS, Chroma, and other ML packages
RUN apt-get update && apt-get install -y \
    build-essential \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Expose the default Flask-SocketIO port
EXPOSE 5000

# Set environment variables for production behavior
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=server.py

# Command to run the WebSocket server
# Assuming server.py executes socketio.run() with host="0.0.0.0"
CMD ["python", "server.py"]