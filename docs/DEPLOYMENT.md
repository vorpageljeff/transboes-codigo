# Deploy no VPS

1. Crie `/opt/innovagro/apps/transboes` e clone o repositório.
2. Copie `deploy/.env.example` para `.env`, preencha todos os segredos e execute `chmod 600 .env`.
3. Crie a rede com `docker network create proxy`.
4. Suba o Traefik em `infrastructure/traefik`.
5. Execute `docker compose --env-file .env -f deploy/docker-compose.production.yml up -d --build`.
6. Rode `docker compose --env-file .env -f deploy/docker-compose.production.yml run --rm api alembic upgrade head`.
7. Valide `https://API_DOMAIN/health` e o login.

O DNS deve apontar para o VPS antes da emissão Let's Encrypt. Configure a Vercel somente após validar a URL da API.

