# ---------- Stage 1: Build ----------
FROM node:20-alpine AS builder

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ .

ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# ---------- Stage 2: Serve ----------
FROM nginx:alpine

RUN rm -rf /usr/share/nginx/html/*

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /build/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
