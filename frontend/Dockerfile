# Build stage
FROM node:20 AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# If .env.production is present, it will be injected at this point
RUN npm run build

# Serve stage
FROM node:20-slim
WORKDIR /app
RUN npm install -g serve
COPY --from=build /app/build ./build

# Listen on the port that Cloud Run sets
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "serve -s build -l ${PORT:-8080}"]