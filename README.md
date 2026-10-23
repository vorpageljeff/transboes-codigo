# Trans Boes — Gestão Operacional de Fretes

Fundação do MVP em arquitetura modular monolítica: Next.js no front-end, FastAPI no back-end e PostgreSQL. A API é a autoridade para autenticação, autorização e regras de negócio.

## Estrutura

```text
backend/                FastAPI, SQLAlchemy 2, Alembic, testes e seed
  app/api/v1/           API REST versionada
  app/core/             configuração e segurança
  app/db/               engine e sessões
  app/models/           modelos iniciais
  app/modules/          serviços por domínio
  app/tests/            testes automatizados
  alembic/              migrações
frontend/               Next.js App Router e TypeScript strict
  src/app/              rotas e layout
  src/features/         funcionalidades por domínio
  src/lib/              cliente da API
docker-compose.yml      PostgreSQL local
```

## Execução local

Pré-requisitos: Python 3.11+, Node.js 20.9+ e Docker (opcional).

```bash
docker compose up -d db
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload
```

Em outro terminal:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Abra `http://localhost:3000`. A API fica em `http://localhost:8000`, com OpenAPI em `/docs` e health check em `/health`.

### Teste de rastreamento pelo celular

1. Cadastre um caminhão e acesse **Acompanhar frota**.
2. No celular, abra o portal por HTTPS, selecione o caminhão e toque em **Compartilhar minha localização**.
3. Autorize a localização precisa e mantenha a página aberta durante o teste.
4. Outro usuário autenticado pode acompanhar a última posição no painel e abri-la no Google Maps.

O teste usa a geolocalização do navegador e o mapa do OpenStreetMap, sem chave paga. O compartilhamento para quando a página é fechada ou quando o usuário toca em **Parar localização**. A integração definitiva com o rastreador veicular deve publicar as posições nos mesmos endpoints de tracking.

## Qualidade

```bash
cd backend && ruff check . && pytest
cd frontend && npm run lint && npm run build
```

## Decisões da fundação

- UUIDs evitam IDs previsíveis e facilitam integrações futuras.
- JWT curto contém identidade e perfil; toda autorização crítica permanece na API.
- Senhas usam Argon2. O seed lê credenciais do ambiente e é idempotente.
- SQLite existe apenas como padrão conveniente de desenvolvimento/teste; PostgreSQL é o banco-alvo e está no Compose.
- A migração inicial cobre usuários, veículos, motoristas e localizações. As entidades transacionais entram na Fase 2.
- O token fica em `sessionStorage` nesta fundação. Antes da produção, migrar para cookie HttpOnly ou BFF para reduzir exposição a XSS.
- O backend de produção foi migrado do Render para VPS próprio por decisão aprovada de custo; a Vercel continua hospedando o frontend.
- A automação por provider de WhatsApp foi retirada do escopo por decisão aprovada de custo. O portal pode compartilhar manualmente o link temporário de rastreamento.
- Tabelas de frete são versionadas e possuem vigência. Nenhuma tarifa deve ser ativada sem homologação da regra oficial da Frimesa.

## Próximas fases e dados pendentes

Consulte [TODO.md](TODO.md). Não use as credenciais de demonstração em staging ou produção.
