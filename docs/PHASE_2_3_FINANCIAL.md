# Fases 2 e 3 — Fundação financeira e dashboard

## Arquivos e migrations

- Migration `20260908_03_financial_foundation.py`.
- Novos modelos: auditoria, receitas, custos, regras e conferências de frete.
- Novo router financeiro separado do router operacional.
- Novos schemas e motor configurável de conferência.
- Dashboard e área Financeiro atualizados no frontend.
- Feature flags documentadas nos exemplos de ambiente e no Compose de produção.

## Endpoints

- `GET /api/v1/financial/summary`
- `GET /api/v1/financial/costs`
- `POST /api/v1/financial/costs`
- `GET /api/v1/freight/validations`
- `POST /api/v1/freight/loads/{load_id}/validate`
- `GET /api/v1/reports/billing.csv`

## Telas

- Dashboard com faturamento mensal em primeiro lugar.
- Indicadores de receita, custo, margem e divergência.
- Área Financeiro com lançamento manual de custos.
- Conferência de fretes e exportação CSV.

## Testes

- 9 testes Pytest aprovados.
- Ruff aprovado.
- ESLint aprovado.
- Build Next.js com TypeScript aprovado.

## Decisões e TODOs

- O modo padrão de conferência é `MOCK` e retorna `AGUARDANDO_REGRA`; nenhuma fórmula foi inventada.
- `PASS_THROUGH` e `MANUAL` estão funcionais no motor; `RULE_BASED` aguarda a tabela oficial.
- Custos são manuais e por veículo nesta fase; não há rateio contábil presumido.
- CSV foi priorizado. XLSX entra na fase de relatórios.
- Auditoria foi aplicada às novas mutações financeiras e será expandida aos demais módulos.
- A autorização financeira aceita ADMIN, MANAGER e FINANCIAL; VIEWER permanece somente leitura.

## Dependências externas e riscos

- A tabela oficial e o relatório real de conferência continuam necessários para `RULE_BASED`.
- Receita é reconhecida pela data de coleta ou pela data do cadastro quando a carga tem valor informado.
- Custos incompletos produzem margem estimada, explicitamente identificada como tal.

## Próximo passo

Evoluir carga e viagem com unidade Frimesa, distância, timeline, confirmação de cancelamento,
política configurável de liberação e sugestão de alocação. Em seguida, implementar manutenção.
