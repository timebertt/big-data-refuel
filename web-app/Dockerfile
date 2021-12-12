FROM python:3.9

# fetch recent root CA certificates
RUN apt-get update && \
  apt-get install -y ca-certificates --no-install-recommends && \
  rm -rf /var/lib/apt/lists/* && \
  update-ca-certificates

# instruct python to use system CA certificates instead of its own bundled certs
# (might be outdated and not include the new Let's Encrypt CA yet)
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

# Install dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install -r /app/requirements.txt

# Install app
COPY . /app/

CMD ["python", "app.py"]
