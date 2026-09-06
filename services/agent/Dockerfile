FROM public.ecr.aws/docker/library/python:3.12-slim

WORKDIR /app

COPY packages/core /app/packages/core
COPY services/agent /app/services/agent

RUN pip install --no-cache-dir -e /app/packages/core \
    && pip install --no-cache-dir -r /app/services/agent/requirements.txt \
    && pip install --no-cache-dir -e /app/services/agent

CMD ["python", "-m", "latch_agent.main"]
