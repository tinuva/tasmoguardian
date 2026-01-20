FROM python:3.11-slim

WORKDIR /app

# Install Node.js, unzip, and nginx
RUN apt-get update && apt-get install -y curl unzip nginx && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Initialize and build frontend
RUN reflex init && reflex export --frontend-only --no-zip

EXPOSE 3000

# Start nginx and backend
CMD sh -c "nginx & reflex run --env prod --backend-only --backend-host 127.0.0.1"
