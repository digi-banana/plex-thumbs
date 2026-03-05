# --- STAGE 1: Build React ---
FROM node:18-slim AS build-stage
WORKDIR /app
COPY package.json .
RUN npm install
COPY . .
RUN npm run build

# --- STAGE 2: Python Runtime ---
FROM python:3.11-slim
WORKDIR /app

# Copy React build
COPY --from=build-stage /app/build /app/build

# Copy Backend files
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/

# Environment defaults
ENV DATABASE_URL=sqlite:///./plex_data.db
ENV PLEX_DATA_DIR=/plex_data
ENV HUB_URL=https://api.plexthumbs.qzz.io

EXPOSE 8000

# Run FastAPI from the backend directory
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
