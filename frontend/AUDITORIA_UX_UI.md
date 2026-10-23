# Auditoria global de UX/UI — Portal Trans Boes

Data: 10 de setembro de 2026
Base analisada: branch `main`, commit `c685e25`

## 1. Mapa atual de rotas e telas

### Rotas reais do Next.js

| Rota | Responsabilidade | Componente principal |
| --- | --- | --- |
| `/` | Login | `LoginForm` |
| `/dashboard` | Portal autenticado completo | `OperationsApp` |
| `/rastrear/[token]` | Compartilhamento de localização do motorista | `DriverTracking` |

### Telas internas do portal

O portal autenticado usa o parâmetro `?tab=` e estado local para alternar entre
13 áreas dentro de `/dashboard`:

1. Visão geral (`inicio`)
2. Cargas (`cargas`)
3. Acompanhamento de frota (`acompanhar`)
4. Viagens (`viagens`)
5. Frota e motoristas (`frota`)
6. Financeiro (`financeiro`)
7. Cobranças (`cobrancas`)
8. Importações (`importacoes`)
9. Planejamento (`operacao`)
10. Registro móvel (`mobile`)
11. Usuários e acessos (`usuarios`, apenas administrador)
12. Meu acesso (`conta`)
13. Mais áreas (`mais`, navegação móvel)

Detalhes de carga e viagem ainda aparecem no contexto das listas e formulários;
não existem rotas dedicadas para esses detalhes.

## 2. Inventário de componentes

### Estrutura e navegação

- `OperationsApp`: busca global de dados, estado, mutações, topbar e roteamento
  das telas internas.
- `WorkspaceNav`: sidebar desktop e grupos de navegação.
- `WorkspaceMobileNav`: navegação inferior no celular.
- `PageTitle`, `Title`, `Row`, `Badge`, `Empty`, `Input`, `Select`: primitivas
  locais definidas no mesmo arquivo das telas.

### Domínios

- `DashboardView` e `DashboardCharts`: resumo da operação.
- `LoadsView` e `LoadQueueCard`: cargas e fila.
- `TripsView`: programação e acompanhamento de viagens.
- `FleetView`: veículos e motoristas.
- `FinancialView`: indicadores, custos e conferência de fretes.
- `ImportsView`: importações e histórico.
- `BusinessView`: cobranças.
- `FleetTracking`: acompanhamento de frota e mapa.
- `OperationalInsights`: planejamento e manutenção.
- `MobileEvents`: registro operacional em campo.
- `UsersView` e `AccountView`: administração e perfil.
- `DriverTracking` e `TrackingShareButton`: rastreamento compartilhado.

## 3. Diagnóstico

### Arquitetura da informação

- A sidebar expõe tarefas como módulos principais, aumentando ruído e
  repetindo conceitos: fila de carregamento, acompanhamento e programação
  deveriam pertencer a Cargas, Frota e Viagens.
- Frota e motoristas estão fundidos em uma única tela, embora tenham leituras e
  decisões operacionais diferentes.
- Meu acesso compete com módulos de negócio na navegação.
- O estado por query string permite deep link básico, mas não oferece semântica,
  histórico de navegação ou carregamento independente por módulo.

### Hierarquia visual

- O tema atual mistura gradientes azuis e verdes, brilho, grid decorativo,
  sombras fortes e cards altos. O resultado se aproxima de um painel temático,
  em vez de um produto empresarial de operação.
- A dashboard apresenta hero, quatro cards grandes, seis ações rápidas,
  gráficos, próximos passos e duas listas. A primeira dobra não prioriza a
  informação que exige decisão.
- Muitos blocos repetem borda, fundo e elevação, diminuindo a distinção entre
  informação primária e apoio.
- Valores, status e ações usam pesos visuais semelhantes.

### Consistência e componentes

- Primitivas reutilizáveis estão acopladas ao arquivo `operations-app.tsx`.
- As telas usam combinações distintas de `content-card`, `form-card`,
  `list-row`, tabelas e cards, sem uma API visual comum.
- Estados vazios, sucesso, erro e carregamento existem, mas não seguem um
  componente único com título, explicação e ação contextual.
- A semântica de status está parcialmente correta, mas alguns status operacionais
  usam amarelo onde azul comunica melhor acompanhamento.

### Responsividade e acessibilidade

- O mobile reduz grades e esconde elementos, mas ainda herda a densidade e a
  ordem do desktop.
- A navegação inferior atual tem seis destinos e rótulos ligados a tarefas,
  reduzindo clareza e área de toque.
- Tabelas não possuem um padrão único de transformação para listas mobile.
- Existem bons fundamentos: skip link, labels, `aria-current`, regiões de alerta
  e botões semânticos. Faltam foco visual global consistente e estados de
  interação padronizados.

### Engenharia

- `OperationsApp` concentra orquestração, dados e todas as telas, elevando custo
  de mudança e risco de regressão.
- A busca paralela de dados está correta e evita cascata de requisições.
- O CSS global acumula um tema base claro e uma segunda camada escura de
  sobrescritas, gerando duplicidade e especificidade alta.
- Lucide já é a biblioteca única de ícones e deve ser preservada.

## 4. Prioridades de refatoração

1. Consolidar tokens e eliminar as duas camadas visuais conflitantes do CSS.
2. Refatorar sidebar, topbar e bottom navigation segundo a arquitetura proposta.
3. Reduzir a dashboard para faturamento principal, faixa de indicadores,
   atenção, operação do dia, frota e resumo financeiro.
4. Aplicar superfícies, tipografia, formulários, badges, listas e tabelas
   consistentes a todas as telas existentes.
5. Reorganizar o mobile para quatro destinos: Início, Cargas, Frota e Gestão.
6. Extrair primitives de UI e metadados de navegação do componente central.
7. Validar desktop, tablet e celular, além de lint, TypeScript e build.

## 5. Escopo funcional preservado

A refatoração não altera os endpoints, contratos de dados, regras de permissão,
armazenamento de sessão, estados operacionais ou sequências de mutação. As
mudanças desta etapa se concentram em arquitetura de interface, componentes e
apresentação responsiva.
