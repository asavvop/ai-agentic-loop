FROM python:3.11-slim

# Install standard kubectl for in-cluster operations
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates iproute2 && \
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && mv kubectl /usr/local/bin/ && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY main.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "src.daemon.main_daemon"]
