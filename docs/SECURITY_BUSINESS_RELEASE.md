# Entrega de segurança e evolução operacional — 08/09/2026

## Implementado

- Escrita operacional restrita a ADMIN/MANAGER/OPERATOR; financeiro a ADMIN/MANAGER/FINANCIAL; importação a ADMIN/MANAGER.
- API com papel PostgreSQL transboes_runtime (NOSUPERUSER, NOCREATEDB, NOCREATEROLE); migrations usam credencial separada. As credenciais ficam somente no ambiente privado.
- Edição do frete reconcilia a receita na mesma transação e registra antes/depois na auditoria. Cancelamento remove o lançamento corrente e preserva o histórico de alteração na auditoria.
- Reserva por bloqueio de linha e índices únicos parciais no PostgreSQL: uma viagem ativa por carga, veículo e motorista. Alterações em recursos reservados são bloqueadas. Estados de trânsito não podem ser inventados por PATCH independente da viagem.
- Manutenção por data/hodômetro bloqueia programação quando vencida. Limites ausentes continuam visíveis como dados a conferir; não há prazo inventado.
- Logout revoga token no servidor, login limita tentativas e produção rejeita JWT secret fraco/padrão. Limite de corpo também cobre streaming sem Content-Length. API tem limite de memória de 768 MiB.
- Campos nulos indevidos são rejeitados; CSV neutraliza fórmulas; conferência agrega a última validação por carga; custo valida correspondência entre viagem e veículo.
- Importador valida nomes e ordem das colunas, limita linhas, rejeita linhas estruturalmente inválidas e conflitos de valores para uma viagem já importada. Parsing/SQL executados fora do event loop.
- Cobranças: EM_REVISAO → COBRADA → RECEBIDA, ou encerramento JUSTIFICADA. Motivo, referência de prova e comprovante de recebimento são exigidos conforme a etapa. Recebimentos adicionais ficam em indicador separado para não duplicar receita da carga.
- Resultado parcial por viagem e lançamento de custos vinculados. Categorias presentes são exibidas; ausência de custos não é tratada como lucro confirmado.
- Operação móvel: saída, entrega e ocorrência ficam em fila local por usuário quando a conexão cai com a página aberta. Sincronização é explícita, ordenada e idempotente por evento. Conflitos permanecem na fila para revisão; sem descarte automático.
- Seleção de mês financeiro e exportação do mesmo período. Menu Mais separa cobranças, operação móvel e planejamento/manutenção.
- Backup atômico com validação, permissões restritas, retenção e compatibilidade com execução por root do timer; restore com transação única e parada ao primeiro erro.
- Deploy faz backup pré-migration, usa imagem por commit e conserva imagem anterior para rollback. Dependências Python fixadas em requirements.lock; Vercel recebe package-lock.json. SSH do pipeline usa known_hosts verificado e StrictHostKeyChecking=yes.
- Uptime Kuma inicializado e dois monitores HTTPS ativos, com heartbeat saudável: API/banco e portal. Credencial administrativa guardada fora do repositório, em ~/.config/transboes/monitoring.json no VPS.

## Evidências

- Testes automatizados de autorização, receita, reserva, cobranças, logout, limite de login, esquema de importação, manutenção e idempotência de eventos.
- PostgreSQL isolado: migrations desde banco vazio até 20260908_06 aplicadas; duas reservas concorrentes para o mesmo motorista produziram 201 e 409, com exatamente uma viagem persistida.
- Restore isolado de backup atual: 51 cargas e 51 receitas recuperadas. Banco temporário removido após validação.
- Navegador local: login, navegação das novas áreas e criação de cobrança em EM_REVISAO validados com dados fictícios; sem erros de execução reportados pelo navegador.
- npm audit de produção e pip-audit dos pacotes Python instalados: nenhuma vulnerabilidade conhecida encontrada na consulta realizada. Isso não é certificação nem varredura de imagens/Ubuntu.
- Produção após primeira publicação: papel runtime sem privilégios administrativos, migration 20260908_06 e 51 cargas preservadas.

## Limites que continuam explícitos

Esta entrega não declara todos os itens da auditoria encerrados. Permanecem: paginação completa e otimização do carregamento do portal; anexos binários de comprovantes (atualmente referências); cadastro individual e isolamento de acesso por motorista; cálculo de quilômetros vazios; custos completos validados por fechamento; varredura e atualização das imagens/Ubuntu; teste de rollback funcional provocado; isolamento do socket Docker; autenticação de sessão com cookie HttpOnly/CSP sem unsafe-inline; automatização completa do Vercel via Git. A CSP atual restringe origens e enquadramento, mas ainda permite scripts inline para compatibilidade com Next.js.

GPS, jornada, regras oficiais de frete, envio WhatsApp e conciliação bancária dependem de dados/regras/credenciais reais. Sugestões usam apenas dados disponíveis e exigem confirmação. Não foi contratado serviço pago adicional. Backup local continua sem cobrir perda física total do VPS.

Alertas externos precisam de um destino/SMTP autorizado. Enquanto isso, a disponibilidade é registrada no painel. A operação móvel não garante abertura inicial sem internet; não limpar o armazenamento do navegador com pendências. O posicionamento comercial e os resultados de economia precisam ser validados com operadores e clientes reais.
