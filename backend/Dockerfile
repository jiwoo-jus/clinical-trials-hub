# # Use lightweight Python base image
# FROM python:3.10-slim

# # Set working directory inside container
# WORKDIR /app

# # Copy all local files into container
# COPY . .

# # Install Python dependencies
# RUN pip install --no-cache-dir -r requirements.txt

# # Expose the port that Uvicorn will run on
# EXPOSE 8080

# # Start the FastAPI app with Uvicorn
# CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers"]

# Use lightweight Python base image
FROM python:3.10-slim

# Set working directory inside container
WORKDIR /app

# Copy all local files into container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that Uvicorn will run on
EXPOSE 5050

# Start the FastAPI app with Uvicorn
CMD ["sh", "-c", "exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-5050} --proxy-headers"]