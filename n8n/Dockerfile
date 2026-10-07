FROM n8nio/n8n:latest

USER root
# Ensure workflow data directory exists and has proper permissions
RUN mkdir -p /data/workflows && chown -R node:node /data/workflows

COPY ./workflows /data/workflows/
RUN chown -R node:node /data/workflows

USER node

EXPOSE 5678

CMD ["sh", "-c", "export N8N_PORT=${PORT:-5678}; n8n import:workflow --separate=/data/workflows || true; exec n8n start"]
