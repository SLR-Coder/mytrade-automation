FROM python:3.11-slim

# Install system dependencies for TA-Lib and plotting
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    libpng-dev \
    libfreetype6-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib C library
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "main.py"]