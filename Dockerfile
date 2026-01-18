FROM python:3.11-slim

WORKDIR /app

# Install Node.js and unzip for Reflex frontend build
RUN apt-get update && apt-get install -y curl unzip && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Initialize and fully build frontend
RUN reflex init && reflex export --frontend-only --no-zip

# Install serve to host static frontend
RUN npm install -g serve

EXPOSE 3000 8000

# Start both frontend (serve) and backend (reflex)
CMD sh -c "serve -s .web/build/client -l 3000 & reflex run --env prod --backend-only --backend-host 0.0.0.0"
