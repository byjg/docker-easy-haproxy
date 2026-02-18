FROM python:3.12-slim

WORKDIR /app

COPY server.py .

RUN chmod +x server.py

EXPOSE 8080

CMD ["python3", "server.py"]
