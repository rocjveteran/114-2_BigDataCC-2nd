FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "import matplotlib.font_manager as fm; fm._rebuild()" 2>/dev/null || true

EXPOSE 7860

CMD ["python", "app.py"]
