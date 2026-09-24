FROM python:3.12-slim AS runtime

RUN useradd --create-home --uid 10001 devloop
WORKDIR /opt/devloop
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

USER devloop
ENTRYPOINT ["devloop"]
CMD ["--help"]

