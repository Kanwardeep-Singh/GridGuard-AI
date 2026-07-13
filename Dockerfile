FROM python:3.12-slim

WORKDIR /app

# System deps for faiss/scikit-learn wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV LLM_PROVIDER=mock \
    API_HOST=0.0.0.0 \
    API_PORT=8000

EXPOSE 8000

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
