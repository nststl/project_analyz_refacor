FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt pyproject.toml ./
COPY src ./src
COPY tests ./tests

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

RUN mkdir -p reports htmlcov

CMD ["pytest", "tests", "-q", "--junitxml=reports/junit.xml", "--cov=models", "--cov=services", "--cov=storage", "--cov=patterns", "--cov=utils", "--cov=web", "--cov-report=xml:coverage.xml", "--cov-report=html:htmlcov"]
