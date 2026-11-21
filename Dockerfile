FROM sandbox-init-verifier:latest

WORKDIR /app
RUN rm -rf /app/src/* /app/tests/*
COPY pyproject.toml ./
RUN pip install --no-cache-dir "psycopg[binary]>=3.2.0" "pgvector>=0.3.5"
COPY src/ ./src/
COPY tests/ ./tests/

ENV PYTHONPATH=/app/src
CMD ["python", "-m", "interview_ops.server"]
