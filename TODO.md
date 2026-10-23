# Pendências dependentes da Trans Boes

- Obter exemplos reais do Excel Copagril, inclusive retificação e cancelamento.
- Obter tabela Frimesa estruturada e formalizar regra de vigência e cálculo.
- Definir regras de capacidade, jornada, região, prioridade e elegibilidade.
- Receber documentação e credenciais da API GPS contratada; o adapter mock e os contratos de health/retry já estão disponíveis.
- WhatsApp removido do escopo por decisão de custo do cliente; o compartilhamento manual por link permanece suficiente para o MVP.
- Definir raio e eventos válidos de geofence/check-in.
- Confirmar usuários, perfis finais e matriz de permissões.
- Definir retenção de histórico, backups e exportações contábeis.

# Pendências técnicas planejadas

## Próxima evolução — retomar em 10/09/2026

- Criar ficha de carregamento por viagem, convertida em romaneio digital após o carregamento.
- Validar origem, destino, motorista, veículo, horários, quantidades, pesos, GTA, documentos fiscais, ocorrências e comprovantes.
- Enviar ao cliente um link temporário para aprovar, registrar divergência ou recusar o recebimento.
- Gerar PDF versionado do romaneio e usar o aceite como evidência para liberar a cobrança.

- Homologar a fórmula/tarifa oficial da Frimesa antes de ativar uma versão em produção.
- Mapear os estados operacionais detalhados aos estados legados sem reescrever o histórico existente.
- Implementar o adapter do fornecedor GPS quando a documentação estiver disponível.
- Adicionar testes E2E em navegador e concorrência contra PostgreSQL real.

# Decisões encerradas

- Backend no VPS próprio substitui o Render por decisão aprovada de custo.
- Compartilhamento via WhatsApp/provider automático não faz parte do MVP por decisão aprovada de custo.
