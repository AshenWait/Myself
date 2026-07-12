ARG PYTHON_IMAGE=python:3.11-slim
FROM ${PYTHON_IMAGE}
ARG PIP_INDEX_URL=https://pypi.org/simple

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --index-url "${PIP_INDEX_URL}" --no-cache-dir --upgrade pip \
    && pip install --index-url "${PIP_INDEX_URL}" --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p storage/uploads

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
