# Auditoria de engenharia, segurança e confiabilidade — 08/09/2026

Base: commit fc53326; inspeção do código versionado, configurações de deploy, consultas somente leitura ao VPS e testes locais em SQLite descartável. Produção não foi alterada. Este relatório não constitui certificação nem prova de ausência de vulnerabilidades.

## Parecer

O sistema é um MVP funcional, mas ainda não está suficientemente protegido para operação ampla com múltiplos perfis nem para ser a única fonte de verdade financeira. Há falhas comprovadas de autorização, consistência financeira e alocação. A disponibilidade observada é boa; recuperação de desastre e concorrência ainda não foram demonstradas.

## Achados prioritários

### A01 — Alta: perfil VIEWER consegue escrever nas operações

Evidência: backend/app/api/v1/router.py usa CurrentUser nos POST/PATCH de veículos, motoristas, cargas e viagens. Não há require_roles nessas mutações. Teste isolado autenticado como VIEWER criou veículo com HTTP 201. Restrições existem em custos/importação, portanto são inconsistentes.

Impacto: qualquer conta ativa, inclusive consulta, pode alterar a operação e valores de cargas. Restringir no servidor cada mutação com matriz de papéis e testes negativos de todos os perfis. Revisar também quem pode ler CNH, telefone e relatórios financeiros.

### A02 — Alta: API usa superusuário PostgreSQL em produção

Consulta pg_roles retornou current_user=transboes_app, rolsuper=true, rolcreatedb=true, rolcreaterole=true. O Compose usa POSTGRES_USER também na DATABASE_URL: o usuário criado na inicialização oficial do PostgreSQL é administrativo.

Impacto: comprometimento da API teria privilégios excessivos sobre o banco. Criar papéis separados para administração/migrations e execução da API; conceder apenas privilégios necessários sobre tabelas/sequências. Testar migrations, escrita e backup após a separação.

### A03 — Alta: editar frete não atualiza receita

Evidência: create_load cria RevenueEntry, mas update_load modifica apenas Load. Reprodução: carga criada com frete 100; PATCH para 200 retornou 200; receita permaneceu 100. Datas e cancelamentos também não possuem reconciliação financeira centralizada.

Impacto: dashboard e CSV podem divergir do cadastro de cargas. Definir política de reconhecimento/estorno e atualizar lançamentos na mesma transação, com auditoria. Corrigir dados existentes por reconciliação revisável, sem substituição indiscriminada.

### A04 — Alta: motorista reservado em duas viagens e corrida de alocação

Reprodução sequencial: duas cargas e dois veículos com mesmo motorista e mesmo horário foram aceitos (201/201). create_trip verifica apenas driver.is_active. Para carga/veículo há leitura e escrita sem bloqueio de linha, versão otimista ou restrição de unicidade de reserva ativa. A corrida concorrente é um risco identificado no código; não foi executada contra produção.

Impacto: programação operacional impossível ou dupla reserva. Centralizar reserva em transação, bloquear recursos em ordem estável, verificar motorista e adicionar restrições adequadas à regra temporal. Testar concorrência com PostgreSQL real.

### A05 — Alta: estados operacionais podem ser alterados fora da transição de viagem

VehicleUpdate.status e LoadUpdate.status permitem modificar diretamente recursos já associados a viagens. As mutações também permitem reduzir capacidade ou aumentar carga sem revalidar uma reserva existente. A finalização/cancelamento libera o veículo incondicionalmente. Flags de liberação configuradas não são consultadas nesse fluxo.

Impacto: carga, veículo e viagem podem se contradizer. Aplicar máquina de estados em serviço único e preservar invariantes de capacidade, reserva e liberação.

### A06 — Alta: recuperação e rollback incompletos

O timer transboes-backup.timer está agendado; LAST estava vazio e o serviço sem execução registrada na consulta. Foi encontrado um dump manual de 2.538 bytes com permissão 0644 no diretório padrão. Isso não prova restauração nem cobertura dos dados importados depois. A leitura efetiva por outros usuários depende também das permissões dos diretórios pais.

backup.sh não usa arquivo temporário + rename atômico nem umask restritivo; uma falha pode deixar arquivo parcial. A retenção por mtime não garante exatamente sete diários/quatro semanais. restore.sh não usa --exit-on-error/--single-transaction; não coordena suspensão de escritas por conta própria.

deploy.sh migra o banco antes de substituir a API. O rollback cobre apenas falha do healthcheck final; falha de build/migration encerra por set -e. A imagem é reconstruída em tag mutável com dependências sem lock Python: voltar commit não garante voltar ao mesmo artefato. Não há backup pré-migration integrado. Um /health saudável não detecta erro funcional/financeiro.

Correção: backup atômico com permissões 0600, alerta de falhas, restore testado em banco isolado, RPO/RTO definidos, imagem imutável por commit e migrations compatíveis com versão anterior. Backup local continua sem cobrir perda total do VPS, conforme limitação já aceita do orçamento.

### A07 — Média: autenticação sem contenção de tentativas e revogação

Não foram encontrados rate limit/bloqueio progressivo no login nem middleware equivalente no Traefik versionado. JWT dura oito horas; logout remove o token do navegador, sem revogação no servidor. A consulta de usuário ativo em cada requisição é positiva, mas trocar senha não invalida necessariamente tokens emitidos. sessionStorage fica acessível a JavaScript da origem; não foi encontrado XSS explorável nesta auditoria. Não há CSP na resposta observada do portal.

Aplicar limitação de login, trilha de eventos, estratégia de revogação e política de sessão; avaliar cookie HttpOnly com proteção CSRF se mudar o transporte. Configuração deve rejeitar segredo de desenvolvimento em produção. O segredo atual foi verificado apenas por tamanho e comparação: 96 caracteres e diferente do padrão, sem exposição de valor.

### A08 — Média: importador pode omitir linhas e confundir versões de dados

parser.py valida número de colunas, mas não os nomes/ordem completos do cabeçalho. Linhas com largura diferente ou sem external_id são ignoradas, sem compor erro/total. A cor é reconhecida por classes c66/c67 específicas, não por semântica geral. service.py ignora um external_id já existente mesmo que os valores tenham mudado; não compara conteúdo nem apresenta conflito detalhado. Importação concorrente depende de restrições do banco e não trata IntegrityError como conflito controlado.

O resultado de 51 cargas para 52 linhas foi observado anteriormente; a regra de identidade precisa ser validada com a operação: uma viagem pode ou não representar vários romaneios. Não afirmar que toda repetição de viagem equivale a duplicata de negócio sem essa confirmação.

Correção: validar esquema, contabilizar todas as linhas, explicitar rejeições/conflitos e revisar chave composta quando necessário. Perfis e versões estão armazenados, mas o parser usa REPORT_MAPPING fixo no código.

### A09 — Média: limites de recursos e crescimento

Upload lê o conteúdo inteiro antes de checar 10 MB e executa parsing/SQL síncronos dentro de endpoint async. Não há limite de memória configurado para API (MemoryLimit=0). Listagens retornam tudo e o frontend busca nove conjuntos completos em Promise.all; uma falha impede a atualização conjunta. CSV e importação acumulam dados em memória.

Aplicar limite de corpo antes da leitura total, limite de linhas, processamento fora do event loop quando necessário, paginação, índices e testes de volume adequados ao VPS.

### A10 — Média: métricas de conferência contam histórico, não última situação

build_summary soma todas as FreightValidation de cada carga. Revalidar acumula registros e pode manter divergências antigas no indicador, enquanto a interface mostra apenas o registro mais recente. Em produção FREIGHT_VALIDATION_MODE=MOCK: o endpoint manual retorna AGUARDANDO_REGRA mesmo com valor esperado informado. A importação compara colunas reais e tem comportamento distinto.

Correção: separar histórico e estado atual; agregar última validação por carga. Comunicar modo na interface e habilitar validação manual apenas quando tiver semântica definida. Receita sem custos cadastrados não comprova lucro real.

### A11 — Média: exportação CSV aceita fórmulas

billing_csv escreve referência/cliente/origem/destino sem neutralizar prefixos de fórmula. Campos podem ser fornecidos por usuários autenticados. Ao abrir em planilha, valores iniciados por caracteres de fórmula podem ser interpretados como fórmulas, conforme aplicativo/configuração. Não foi executada fórmula externa.

Neutralizar células textuais perigosas na exportação e testar preservação dos dados.

### A12 — Média: trilha e validação de entradas incompletas

Auditoria cobre custos, conferência e importação, mas não alterações operacionais/login. Modelos PATCH aceitam null para campos não nulos; reprodução de model=null em veículo retornou HTTP 500. get_current_user não trata ValueError de UUID inválido em sub; isso exige token validamente assinado para alcançar o caso. Custos verificam veículo, mas não validam explicitamente existência/compatibilidade da viagem associada antes de gravar.

Adicionar validação consistente, conflitos HTTP apropriados e trilha com autor/antes/depois. Evitar informações sensíveis em logs.

## Engenharia e entrega

Monólito modular FastAPI/SQLAlchemy/Alembic e frontend Next.js/React são proporcionais ao porte. Porém, regras centrais estão concentradas no router e a interface em um arquivo denso, dificultando manutenção. Vários módulos planejados permanecem placeholders. Não há evidência de teste E2E de navegador ou suíte PostgreSQL concorrente; os testes atuais usam SQLite e create_all, portanto não validam as migrations de produção.

O workflow testa pushes, mas só faz deploy VPS em workflow_dispatch. O frontend foi publicado por conector, não por integração Git automática. Actions usam tags, não hashes imutáveis; não há fingerprint explícito do host SSH na action. Python e imagens não possuem lock/digest para builds reproduzíveis. Essas diferenças devem constar da documentação operacional.

Traefik acessa docker.sock e Portainer tem acesso administrativo ao Docker; comprometimento dessas ferramentas aumenta o alcance do incidente. Montagem :ro do socket não constitui autorização somente leitura da API Docker. Revisar isolamento/proxy de socket e atualização das imagens.

## Proteções confirmadas

- API executa como transboes, sem privileged; PostgreSQL não publica porta.
- Portainer 9443 e Kuma 3001 publicados somente em loopback.
- Portas públicas observadas no host: 22, 80, 443; HTTPS funcionando.
- CORS de produção restrito a duas origens do portal; .env com permissão 0600.
- JWT com segredo diferente do padrão; senhas usam Argon2 por pwdlib.
- SQLAlchemy usa consultas estruturadas; não foi identificado SQL dinâmico baseado diretamente em entrada nas rotas examinadas.
- Logs Docker com rotação, volumes persistentes e healthcheck com SELECT 1.
- VPS no instante da consulta: 13% de disco usado; aproximadamente 3,1 GiB de memória disponível.
- Reenvio do mesmo relatório já havia sido bloqueado com 409; isso não resolve todos os conflitos por identidade de negócio.

## Verificação realizada e limites

11 testes existentes passaram. Quatro reproduções locais adicionais comprovaram escrita por VIEWER, receita desatualizada, reserva dupla de motorista e null causando 500. Nenhuma escrita de teste em produção.

npm audit --omit=dev retornou zero vulnerabilidades conhecidas no lockfile local; isso não certifica o artefato Vercel, especialmente porque o deploy anterior omitiu package-lock.json. pip-audit não estava instalado; Python, Ubuntu e imagens não receberam varredura de CVEs nesta auditoria. Não foi realizado teste de carga ou pentest externo.

ufw e sshd -T exigiram sudo com senha e não puderam ser verificados. Não foi inferido que firewall ou bloqueio de root estejam ativos apenas a partir dos arquivos locais. A existência do container Kuma não comprova monitores configurados ou notificações entregues. Não foram acessados segredos do GitHub/Vercel nem realizada auditoria completa de histórico Git. A busca por nomes de arquivos versionados encontrou apenas .env.example; isso não é scanner completo de segredos.

## Ordem recomendada

1. Corrigir autorização, papel PostgreSQL, consistência de receita e reservas/estados.
2. Validar restauração isolada, backup automático e rollback funcional.
3. Corrigir reconciliação de importações/conferências, auditoria e validações de entrada.
4. Limitar login/upload, paginar, fixar dependências/artefatos e testar fluxos reais no navegador + PostgreSQL.
5. Só então ampliar usuários e automações operacionais.

Critério para encerrar os principais riscos: VIEWER recebe 403 em toda escrita; API não é superusuária; atualização de frete reconcilia receita; disputas por recursos produzem uma única reserva; restauração recupera dados atuais em ambiente isolado; agregações financeiras refletem a última situação válida.
