FROM python:3.12-alpine

RUN apk add --no-cache certbot

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir .

EXPOSE 2080
EXPOSE 8088

VOLUME ["/certs"]

CMD ["python", "-m", "src.main"]
