FROM --platform=linux/arm64/v8 python:3.11-slim AS build

WORKDIR /app
COPY . /app

# Install build dependencies (gcc) and python dependencies
RUN apt-get update && \
    apt-get install -y gcc && \
    pip install --no-cache-dir -r requirements.txt

# Final stage
FROM --platform=linux/arm64/v8 python:3.11-slim

WORKDIR /app
COPY . /app

# Copy installed packages from build stage
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

CMD ["python", "run.py"]