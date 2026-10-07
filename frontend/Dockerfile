FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . ./

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

FROM node:20-alpine

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 3000

CMD ["sh", "-c", "echo \"window.__RUNTIME_CONFIG__ = { VITE_API_BASE_URL: '${VITE_API_BASE_URL}' };\" > /app/dist/config.js && serve -s dist -l ${PORT:-3000}"]