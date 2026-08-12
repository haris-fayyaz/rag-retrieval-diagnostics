# Stage 1: build the React app
FROM node:22-alpine AS builder

RUN npm install -g pnpm

WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# Stage 2: serve the built files with nginx
FROM nginx:alpine

# SPA fallback rule: any path nginx doesn't find as a file
# gets index.html, React Router handles the rest
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 8443