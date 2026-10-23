# Infraestrutura TransBoes

A produção usa um VPS Ubuntu 24.04 LTS: Traefik expõe somente 80/443, a API compartilha a rede `proxy` e acessa o PostgreSQL pela rede privada `transboes_private`. PostgreSQL não publica portas. Portainer e Uptime Kuma escutam somente em localhost e devem ser acessados por túnel SSH.

O alvo é o Hostinger KVM 1, dentro do teto mensal. O frontend continua na Vercel gratuita e usa `NEXT_PUBLIC_API_URL=https://API_DOMAIN/api/v1`.

O Docker Engine 29 do Ubuntu é configurado por `infrastructure/docker/daemon.json` para aceitar o cliente local usado pelo Traefik. O socket permanece sem exposição TCP e acessível apenas a root e ao grupo Docker.

Ordem de instalação: Docker, rede proxy/Traefik, aplicação, Portainer e Uptime Kuma. Os serviços administrativos são opcionais se a RAM ficar pressionada.
