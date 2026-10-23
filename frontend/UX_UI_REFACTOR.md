# Refatoração UX/UI do portal Trans Boes

## 1. Auditoria

A análise completa de rotas, arquitetura, hierarquia, consistência, responsividade e prioridades está em [AUDITORIA_UX_UI.md](./AUDITORIA_UX_UI.md). A auditoria confirmou que as páginas autenticadas são estados internos de `/dashboard`, controlados por `?tab=`, e que essa estrutura precisa ser preservada para não afetar contratos da API.

## 2. Design system

O portal passou a usar um único sistema visual, definido em `src/app/globals.css`:

- fundo `#0B1117`, sidebar `#080D12`, cards `#111820` e superfícies elevadas `#151E27`;
- bordas `#24303C`, texto principal `#F1F5F9` e texto secundário `#94A3B8`;
- verde reservado para ação primária, foco, seleção e estados positivos;
- azul, amarelo e vermelho usados apenas em estados semânticos;
- tipografia Geist via `next/font`;
- raios, sombras, espaçamento, inputs, botões, cards, badges, alertas, formulários, listas, gráficos, estados vazios e paginação padronizados.

## 3. App shell e navegação

A navegação foi reorganizada em Operação, Gestão e Administrativo. Monitoramento virou uma subárea de Frota; cobranças, manutenção, registro móvel e importações usam navegação contextual de Gestão. Meu acesso fica no menu do usuário e na central de Gestão.

No celular, a navegação fixa possui quatro destinos: Início, Cargas, Frota e Gestão. No tablet, a mesma navegação ganha largura controlada. No desktop, a sidebar fica fixa e o conteúdo usa toda a largura disponível com limite de leitura por componente.

## 4. Páginas e fluxos

Foram preservados e redesenhados os fluxos de visão geral, cargas, viagens, monitoramento, frota, motoristas, financeiro, cobranças, importações, manutenção e planejamento, registro móvel, usuários, perfil e central de Gestão. Login e compartilhamento público de localização também seguem o mesmo sistema.

O dashboard ficou mais compacto, com quatro indicadores principais, quatro ações rápidas, gráficos operacionais e uma fila de prioridade. A conferência financeira ganhou busca, contagem e paginação de dez registros para evitar rolagem excessiva.

## 5. Responsividade e acessibilidade

Os breakpoints seguem os intervalos do projeto: celular abaixo de 768 px, tablet entre 768 e 1279 px e desktop a partir de 1280 px. A interface mantém navegação por teclado, link de salto, `aria-current`, regiões nomeadas, feedback com `role`, foco visível, alvos de toque adequados e suporte a movimento reduzido.

## 6. Validação

- ESLint: aprovado.
- TypeScript e build de produção do Next.js 16.3.4: aprovados.
- Rotas `/`, `/dashboard` e `/rastrear/[token]`: compiladas.
- As 13 áreas internas do dashboard: abertas em navegador com dados reais sem erro de aplicação.
- Inspeção visual: desktop 1440 px, tablet 1024 px e celular 390 px.
- Overflow horizontal: não encontrado em tablet ou celular.

As regras de negócio, endpoints e formatos de dados não foram alterados.
