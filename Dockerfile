# Stage 1: Build the Next.js static files 
FROM node:20-alpine AS builder  

WORKDIR /app/frontend  

# Install dependencies  
COPY frontend/package.json frontend/package*.json ./  
RUN npm install

# Build static files
COPY frontend/ ./  
RUN npm run build  


# Stage 2: Serve API and Frontend 
FROM python:3.11-slim  

WORKDIR /app  

# Install python dependencies
COPY backend/requirements.txt /app/backend/  
RUN pip install --no-cache-dir -r /app/backend/requirements.txt  

# Copy backend source  
COPY backend/ /app/backend/  

# Copy nextjs build output  
COPY --from=builder /app/frontend/out /app/frontend/out  

WORKDIR /app/backend  

ENV PORT=8000
EXPOSE ${PORT}  

CMD sh -c "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"
