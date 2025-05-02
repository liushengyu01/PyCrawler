FROM python:3.9.19-slim  

WORKDIR /app  

COPY requirements.txt .  

RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && pip3 install --no-cache-dir -r requirements.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*  

COPY . .  

CMD ["python", "app.py"]