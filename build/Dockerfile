# ==============================================================================
# Stage 1: Build Python virtual environment and run tests
# ==============================================================================
FROM haproxy:3.3-alpine AS builder

USER root

RUN apk add --no-cache python3 bash curl build-base python3-dev musl-dev linux-headers \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /scripts

COPY pyproject.toml uv.lock LICENSE README.md ./
COPY src/ ./src/
COPY tests/ ./tests/

RUN uv sync --frozen
RUN uv run pytest -s -vv tests/
RUN uv sync --no-dev
RUN rm -rf tests/

# ==============================================================================
# Stage 2: Lean runtime image
# ==============================================================================
FROM haproxy:3.3-alpine

ARG RELEASE_VERSION_ARG

ENV RELEASE_VERSION=$RELEASE_VERSION_ARG
ENV TZ="Etc/UTC"

USER root

RUN apk add --no-cache certbot openssl bash curl su-exec \
    && mkdir -p /etc/easyhaproxy/haproxy \
    && mkdir -p /etc/easyhaproxy/certs/certbot /etc/easyhaproxy/certs/haproxy \
    && openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
        -keyout /tmp/placeholder.key \
        -out /tmp/placeholder.crt \
        -subj "/CN=placeholder" \
    && cat /tmp/placeholder.crt /tmp/placeholder.key > /etc/easyhaproxy/certs/certbot/placeholder.pem \
    && cat /tmp/placeholder.crt /tmp/placeholder.key > /etc/easyhaproxy/certs/haproxy/placeholder.pem \
    && rm /tmp/placeholder.key /tmp/placeholder.crt

COPY build/assets /
COPY build/entrypoint.sh /entrypoint.sh
COPY --from=builder /scripts /scripts

RUN chmod +x /entrypoint.sh \
    && chown -R haproxy:haproxy /etc/easyhaproxy /scripts

ENTRYPOINT ["/entrypoint.sh"]
CMD ["--base-path", "/etc/easyhaproxy"]