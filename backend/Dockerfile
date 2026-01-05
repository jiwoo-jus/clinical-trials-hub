# Use lightweight Python base image
FROM python:3.13-slim

# Set working directory inside container
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy all local files into container
COPY . .

# Expose the port that Uvicorn will run on
EXPOSE 5050

# Start the FastAPI app with Uvicorn
CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-5050} --proxy-headers"]