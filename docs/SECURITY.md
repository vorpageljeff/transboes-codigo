# Segurança do VPS

- Crie usuário administrativo com sudo e use chave SSH.
- Confirme o acesso por chave antes de desabilitar senha e login root.
- Libere no firewall apenas 22, 80 e 443.
- Proteja SSH contra força bruta e aplique atualizações de segurança.
- Nunca registre `.env`, chaves, dumps ou `acme.json` no Git.
- Use senhas únicas, JWT secret aleatório e usuário PostgreSQL exclusivo.
- Acesse Portainer e Uptime Kuma por túnel SSH.
- Revise imagens e atualizações mensalmente.

Após testar o acesso do usuário `innovagro`, instale `infrastructure/ssh/99-innovagro-hardening.conf` em `/etc/ssh/sshd_config.d/` e valide com `sshd -t` antes de recarregar o SSH.
