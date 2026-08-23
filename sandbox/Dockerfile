FROM python:3.11-slim

# Prevent python from buffering stdout/stderr and writing .pyc files
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/sandboxuser/.local/bin:$PATH"

# Create non-root sandbox user
RUN groupadd -g 1000 sandboxgroup && \
    useradd -u 1000 -g sandboxgroup -m -s /bin/bash sandboxuser

# Install standard coding benchmark and test libraries
RUN pip install --no-cache-dir \
    pytest>=8.0.0 \
    pytest-asyncio>=0.23.0 \
    numpy>=1.26.0 \
    pandas>=2.2.0

# Set up isolated workspace directory
WORKDIR /workspace
RUN chown -R sandboxuser:sandboxgroup /workspace

USER sandboxuser

CMD ["python", "main.py"]
