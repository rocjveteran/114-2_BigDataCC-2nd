FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    fonts-noto-cjk \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "\
import glob, os, matplotlib; \
cache = matplotlib.get_cachedir(); \
[os.remove(f) for f in glob.glob(os.path.join(cache,'fontlist-*.json'))]; \
import matplotlib.font_manager as fm; fm._rebuild(); \
cjk=[f.name for f in fm.fontManager.ttflist if 'CJK' in f.name]; \
print('CJK fonts:', cjk[:2] if cjk else 'NOT FOUND')"

EXPOSE 7860

CMD ["python", "app.py"]
