FROM python:3.11-slim

WORKDIR /app

# 安裝基本系統套件
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# 安裝 Python 依賴與 PDF 解析套件
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir markitdown[pdf]

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
