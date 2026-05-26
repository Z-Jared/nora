FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY mini_agent/ mini_agent/

RUN pip install --no-cache-dir .

RUN mkdir -p data logs plugins

EXPOSE 8080

ENV NORA_HOST=0.0.0.0
ENV NORA_PORT=8080

CMD ["nora-serve"]
