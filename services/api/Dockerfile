# Build context: repo root.
FROM public.ecr.aws/docker/library/node:22-slim AS web
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --no-fund --no-audit
COPY apps/web ./
RUN npm run build

FROM public.ecr.aws/docker/library/python:3.12-slim
WORKDIR /app
COPY packages/core /app/packages/core
COPY services/agent /app/services/agent
COPY services/api /app/services/api
RUN pip install --no-cache-dir -e /app/packages/core -e /app/services/agent -e /app/services/api
COPY --from=web /web/dist /app/web

ENV LATCH_WEB_DIST=/app/web
EXPOSE 8000
CMD ["uvicorn", "latch_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
