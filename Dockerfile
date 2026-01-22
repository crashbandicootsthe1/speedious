# Python 3.13 slim
FROM python:3.13

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg nodejs curl git && \
    rm -rf /var/lib/apt/lists/*

# Expose port Render will use
EXPOSE 8000
