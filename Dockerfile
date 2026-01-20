FROM python:3.11-slim

WORKDIR /app

# Install Node.js, unzip, nginx, cron, and curl
RUN apt-get update && apt-get install -y curl unzip nginx cron && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Initialize and build frontend
RUN reflex init && reflex export --frontend-only --no-zip

EXPOSE 3000

# Default backup schedule: hourly at minute 8
ENV BACKUP_SCHEDULE="8 * * * *"

ENTRYPOINT ["./entrypoint.sh"]
