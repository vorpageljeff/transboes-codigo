# Auditoria do estado atual — Trans Boes

Data: 8 de setembro de 2026  
Commit auditado: `1d6db7a`

## Resumo executivo

O repositório já possui uma fundação funcional em Next.js, FastAPI, PostgreSQL, SQLAlchemy e Alembic. Login, cadastro básico de frota, motoristas, cargas, programação e transição simples de viagens estão publicados. A infraestrutura de produção também está operacional no VPS próprio e na Vercel.

A especificação atual muda a prioridade do produto: faturamento e conferência de fretes passam a ser P0, seguidos por operação e manutenção. Esses domínios ainda não existem. O backend também concentra todos os endpoints em um único `router.py`, embora existam diretórios vazios que indicam a intenção de um monólito modular.

A referência ao Render no documento não representa o estado atual. O backend já foi migrado e validado no VPS Ubuntu com Docker, Traefik e PostgreSQL. Reintroduzir Render contrariaria a arquitetura de produção e o teto mensal aprovados anteriormente.

## Árvore relevante

```text
Transboes_portal_mobile/
├── .github/workflows/deploy-vps.yml
├── backend/
│   ├── alembic/versions/
│   │   ├── 20260907_01_foundation.py
│   │   └── 20260908_02_operations.py
│   └── app/
│       ├── api/v1/router.py
│       ├── core/{config.py,security.py}
│       ├── db/{base.py,session.py}
│       ├── integrations/{copagril,gps,whatsapp}/
│       ├── models/{user,vehicle,driver,location,load,trip}.py
│       ├── modules/{audit,auth,fleet,freight,notification,planning,reporting,tracking,trip}/
│       ├── schemas/{auth,operations}.py
│       └── tests/{test_auth,test_operations}.py
├── frontend/
│   └── src/
│       ├── app/{page.tsx,dashboard/page.tsx,globals.css}
│       ├── features/auth/login-form.tsx
│       ├── features/dashboard/operations-app.tsx
│       └── lib/api.ts
├── deploy/
│   ├── docker-compose.production.yml
│   └── scripts/{deploy,backup,restore,healthcheck}.sh
├── infrastructure/{traefik,portainer,uptime-kuma,ssh,systemd}/
└── docs/
```

Os diretórios de módulos e integrações que contêm apenas `__init__.py` são estruturas reservadas; não representam funcionalidades implementadas.

## Stack real

| Camada | Implementação encontrada |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript strict, App Router, CSS próprio |
| Backend | Python 3.11, FastAPI, API REST em `/api/v1` |
| Persistência | PostgreSQL 16 em produção; SQLite nos testes |
| ORM e migrações | SQLAlchemy 2 e Alembic |
| Autenticação | JWT, senhas Argon2, token no `sessionStorage` |
| Infraestrutura | VPS Ubuntu, Docker Compose, Traefik, Let's Encrypt, Portainer CE e Uptime Kuma |
| Frontend em produção | Vercel Hobby |
| CI/CD | GitHub Actions testa todos os pushes; deploy do VPS por `workflow_dispatch` |
| Observabilidade | Healthcheck e rotação de logs Docker; sem logs estruturados de negócio |

## Matriz de aderência

| Item | Status | Arquivo/módulo | Ação necessária |
|---|---|---|---|
| Next.js e TypeScript strict | OK | `frontend/`, `frontend/tsconfig.json` | Manter validação no CI. |
| Interface mobile-first | PARCIAL | `operations-app.tsx`, `globals.css` | Remover dependência de tabela larga em cargas e criar navegação “Mais”. |
| FastAPI e REST `/api/v1` | OK | `backend/app/main.py`, `api/v1/router.py` | Preservar contratos versionados. |
| Monólito modular | PRECISA REVISÃO | `api/v1/router.py`, `modules/` | Separar routers, schemas e serviços por domínio sem criar microserviços. |
| PostgreSQL, SQLAlchemy e Alembic | OK | `db/`, `models/`, `alembic/` | Expandir o domínio com migrations incrementais. |
| Infraestrutura VPS | OK | `deploy/`, `infrastructure/` | Manter VPS; a menção ao Render está obsoleta. |
| Login e autenticação | PARCIAL | `auth`, `security.py`, `login-form.tsx` | Adicionar gestão de usuários, renovação/expiração visível e cookie HttpOnly/BFF. |
| Perfis ADMIN/MANAGER/OPERATOR | PARCIAL | `models/user.py` | Adicionar FINANCIAL e VIEWER com migration. |
| Autorização por permissão | AUSENTE | dependências da API | Criar matriz e dependências para ações críticas. |
| Auditoria de decisões | AUSENTE | `modules/audit/` vazio | Criar `audit_logs` e serviço usado por mutações e automações. |
| Empresas | AUSENTE | sem modelo | Criar `companies` e seed controlado da Frimesa. |
| Unidades Frimesa | PARCIAL | `locations` genérico | Criar `facilities`, endereços e seed UFM/UFA/UFR. |
| Sede Trans Boes | AUSENTE | sem seed específico | Cadastrar como local controlado. |
| Veículos | PARCIAL | `vehicle.py`, endpoints e tela Frota | Adicionar ano, odômetro, histórico e autorização de bloqueio/liberação. |
| Motoristas | PARCIAL | `driver.py`, endpoints e tela Frota | Criar tela própria e dados operacionais necessários. |
| Vínculos veículo/motorista | AUSENTE | sem modelo | Criar `vehicle_driver_links`, vigência e prioridade configurável. |
| Elegibilidade/sugestão | AUSENTE | `modules/planning/` vazio | Criar interface e regras configuráveis; não inventar jornada/combinações. |
| Cargas | PARCIAL | `load.py`, endpoints e tela Cargas | Adicionar horário, distância, unidade, `external_id`, versões e histórico. |
| Cancelamento confirmado | PRECISA REVISÃO | status atual permite alteração simples | Criar confirmação explícita, auditoria e alerta se houver atribuição. |
| Viagens | PARCIAL | `trip.py`, endpoints e tela Viagens | Adicionar timestamps semânticos, timeline e checkpoints. |
| Liberação automática | PRECISA REVISÃO | conclusão libera veículo diretamente | Mover para política `VEHICLE_RELEASE_RULE`; padrão temporário `AFTER_UNLOAD`. |
| Faturamento mensal | AUSENTE | sem módulo financeiro | Implementar primeiro card e consolidação por período. |
| Receita por frete/viagem/veículo | AUSENTE | sem entidades financeiras | Criar `revenue_entries` e consultas agregadas. |
| Custos e margem | AUSENTE | sem módulo financeiro | Permitir custos manuais e categorias configuráveis, sem rateio inventado. |
| Conferência de frete | AUSENTE | `modules/freight/` vazio | Criar entidades, interface e modos PASS_THROUGH/MANUAL/MOCK/RULE_BASED. |
| Regra oficial de frete | AUSENTE | dependência externa | Manter RULE_BASED sem fórmula até receber tabela oficial. |
| Ajuste manual de frete | AUSENTE | sem entidade/permissão | Criar ajuste com motivo, usuário e trilha de auditoria. |
| Manutenção | AUSENTE | sem módulo/modelos/tela | Criar tipos, planos, eventos, lembretes e custos. |
| Alertas por data/odômetro | AUSENTE | sem scheduler de domínio | Calcular na leitura e preparar job idempotente futuro. |
| Import profile/version | AUSENTE | integração Copagril vazia | Criar perfis, versões, mapeamentos e validações configuráveis. |
| Importação Excel | AUSENTE | sem parser/upload | Implementar após o modelo, com CSV/XLSX e contingência manual. |
| Idempotência/checksum | AUSENTE | sem modelos | Criar `source_checksum`, `external_id`, `import_run` e `import_row`. |
| Detector de cancelamento | AUSENTE | sem interface | Implementar detectores extensíveis de valor, estilo, coluna e regra. |
| GPS abstrato e mock | AUSENTE | `integrations/gps/` vazio | Criar `GpsProvider`, mock, eventos, health e retry. |
| WhatsApp abstrato e mock | AUSENTE | `integrations/whatsapp/` vazio | Criar provider, mensagens, status e confirmação do motorista. |
| Relatórios por período | AUSENTE | `modules/reporting/` vazio | Priorizar faturamento e conferência. |
| Exportação CSV/XLSX | AUSENTE | sem endpoints | Criar streaming CSV e XLSX após consultas financeiras. |
| Dashboard operacional | PARCIAL | `/dashboard`, `operations-app.tsx` | Colocar faturamento do mês em primeiro lugar e ampliar alertas. |
| Dashboard financeiro | AUSENTE | sem métricas financeiras | Criar KPIs de receita, divergência, custo e margem. |
| Feature flags operacionais | AUSENTE | `core/config.py` | Adicionar flags tipadas e documentadas no `.env.example`. |
| Logs estruturados | AUSENTE | somente logs padrão | Adicionar configuração JSON e correlation/request ID. |
| Healthcheck de banco | OK | `main.py` | Ampliar para integrações sem expor dados sensíveis. |
| Testes de autenticação | OK | `test_auth.py` | Expandir com autorização por perfil. |
| Testes de operação | PARCIAL | `test_operations.py` | Adicionar conflitos, cancelamento confirmado, timeline e auditoria. |
| Testes financeiros/conferência | AUSENTE | sem testes | Criar junto aos serviços P0. |
| Testes de importação/idempotência | AUSENTE | sem testes | Criar junto ao importador. |
| Testes de manutenção | AUSENTE | sem testes | Criar junto ao domínio. |
| Seed de demonstração | PRECISA REVISÃO | `seed.py` | Substituir veículos genéricos por dados controlados; evitar dados pessoais desnecessários. |
| Deploy e rollback do backend | OK | workflow e `deploy.sh` | Manter backup antes de migrations relevantes. |
| Deploy automático da Vercel pelo Git | PARCIAL | projeto Vercel sem vínculo Git | Concluir após recuperação do acesso 2FA da Vercel. |

## Problemas que exigem correção

1. A prioridade visual atual é “Operação de hoje”; o requisito atual exige “Faturamento do mês” como primeira informação no celular.
2. A conclusão da viagem libera o veículo diretamente. Essa decisão deve passar por uma política configurável porque “após descarga” e “retorno à base” ainda estão em validação.
3. Qualquer usuário autenticado pode executar ações críticas. Não existe autorização por papel ou permissão.
4. Cancelamentos não possuem confirmação específica nem auditoria.
5. O `router.py` concentra autenticação, frota, cargas, viagens e dashboard, dificultando a evolução modular prevista.
6. O token no `sessionStorage` é uma limitação de segurança já documentada e precisa ser substituído antes de ampliar usuários.
7. O backup automático existe, mas o usuário de deploy não pode criar manualmente arquivos no diretório central de backups; o timer administrativo continua separado.

## Regras que permanecerão configuráveis

- Fórmula oficial de conferência do frete.
- Definição de jornada e motorista “mais folgado”.
- Combinações proibidas de motorista e veículo.
- Semântica definitiva de liberação do veículo.
- Comportamento e autenticação da API real de GPS.

Esses pontos não bloqueiam financeiro manual, conferência em modo PASS_THROUGH/MANUAL/MOCK, manutenção, mocks de integração e importação versionada.

## Ordem de implementação proposta

1. **Fundação transversal:** modularizar routers/serviços, adicionar feature flags, papéis, permissões e auditoria.
2. **Modelo financeiro e conferência P0:** migrations de regras/versões, validações, ajustes, receitas, custos e períodos.
3. **Dashboard e relatórios P0:** faturamento mensal, divergências, custos, margem e consulta por período.
4. **Domínio operacional:** enriquecer cargas/viagens, vínculos, timeline, política de liberação e sugestão configurável.
5. **Manutenção:** planos, eventos, lembretes por data/odômetro e reflexo financeiro.
6. **Mocks GPS e WhatsApp:** adapters, checkpoints, mensagens e confirmações auditáveis.
7. **Importação:** perfis versionados, CSV/XLSX, checksum, idempotência e cancelamento confirmado.
8. **Exportações e qualidade final:** CSV/XLSX, testes de ponta a ponta, documentação e revisão de produção.

## Próxima entrega recomendada

A próxima migration deve criar a fundação transversal e o núcleo P0 financeiro/conferência. A entrega deve incluir:

- papéis `FINANCIAL` e `VIEWER`;
- feature flags tipadas;
- `audit_logs`;
- `freight_rule_sets`, `freight_rule_versions`, `freight_validation_runs`, `freight_validation_items` e `freight_manual_adjustments`;
- `revenue_entries`, `trip_costs`, `vehicle_cost_profiles` e `financial_periods`;
- `FreightValidationEngine` com modos configuráveis e sem fórmula inventada;
- endpoints de faturamento, conferência e ajustes;
- dashboard com faturamento mensal em primeiro lugar;
- testes de autorização, conferência e agregação financeira.

