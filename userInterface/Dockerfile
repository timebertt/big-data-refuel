FROM python:3.8-alpine

# Install dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install -r /app/requirements.txt

# Install app
COPY . /app/

CMD ["python", "app.py"]
