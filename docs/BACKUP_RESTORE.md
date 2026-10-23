# Backup e restore

O timer `transboes-backup.timer` executa `deploy/scripts/backup.sh` diariamente às 02:00, com atraso aleatório de até dez minutos. O script mantém sete diários e quatro semanas de semanais. O backup local não cobre perda total do VPS.

Para restaurar, pare tráfego de escrita, faça um backup do estado atual e execute `deploy/scripts/restore.sh CAMINHO`. Em seguida rode `alembic upgrade head`, reinicie a API e valide healthcheck, login e contagens do banco.
