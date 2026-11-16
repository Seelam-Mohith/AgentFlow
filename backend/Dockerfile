FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend /app/backend
RUN useradd --create-home agentflow && mkdir /data && chown agentflow /data
USER agentflow
ENV DATABASE_URL=sqlite:////data/agentflow.db
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
