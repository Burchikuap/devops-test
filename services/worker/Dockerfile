FROM python:3.12-slim AS builder

ENV VIRTUAL_ENV=/opt/venv
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
RUN python -m venv "${VIRTUAL_ENV}"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/* && \
    groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --create-home app
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY app ./app

USER 10001:10001
EXPOSE 9100

CMD ["python", "-m", "app.main"]
