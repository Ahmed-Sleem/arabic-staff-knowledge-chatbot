# Stage 1: Build Next.js 15 GPR GUI (`gpr-web`)
FROM node:20-alpine AS builder

WORKDIR /app/src/frontend
COPY src/frontend/package*.json ./
RUN npm install --legacy-peer-deps

RUN mkdir -p /app/src/frontend/public
COPY src/frontend/ .
ENV NODE_ENV=production
ENV API_INTERNAL_URL=http://127.0.0.1:8000
RUN npm run build

# Stage 2: Unified Production Runner (FastAPI Python 3.11 + Next.js Node 20)
FROM python:3.11-slim AS runner

WORKDIR /app

# Install Node.js 20 & build/relational dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gnupg \
    build-essential \
    libpq-dev \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Backend Python requirements
COPY src/backend/requirements.txt ./src/backend/requirements.txt
RUN pip install --no-cache-dir -r ./src/backend/requirements.txt

# Copy Backend Code & Sample Manuals
COPY src/backend/ ./src/backend/
# Keep immutable seed data outside /app/src/backend/data because Railway volumes can mount over that path.
COPY src/backend/data/ ./seed_data/backend_data/
COPY sample_manuals/ ./sample_manuals/
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh

# Copy built Next.js 15 GPR GUI from builder stage
RUN mkdir -p ./src/frontend/public
COPY --from=builder /app/src/frontend/package*.json ./src/frontend/
COPY --from=builder /app/src/frontend/.next ./src/frontend/.next
COPY --from=builder /app/src/frontend/public ./src/frontend/public
COPY --from=builder /app/src/frontend/node_modules ./src/frontend/node_modules

EXPOSE 3000
EXPOSE 8000

ENV NODE_ENV=production
ENV API_INTERNAL_URL=http://127.0.0.1:8000
ENV NEXT_PUBLIC_API_URL=""

CMD ["/app/docker-entrypoint.sh"]
