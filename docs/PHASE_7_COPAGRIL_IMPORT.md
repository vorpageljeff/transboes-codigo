# Fase 7 — Importação do relatório Copagril

## Fonte validada

Arquivo analisado: `CLACI P51 07.2026 (1).xls`.

Apesar da extensão `.xls`, o conteúdo é HTML UTF-8 gerado pelo Oracle BI Publisher. O perfil ativo
foi criado especificamente para esse formato e possui versionamento, mapeamento de 19 campos,
validações e configuração separada de detecção de cancelamento.

Resultados observados no arquivo:

- 52 viagens válidas;
- 18 diferenças entre frete recebido e frete calculado;
- 18 linhas marcadas em amarelo;
- todas as linhas amarelas coincidem com diferenças financeiras neste relatório.

O amarelo deste perfil é armazenado como marcador de estilo e não é interpretado como cancelamento.
Uma futura planilha de programação deverá possuir perfil e regra de cancelamento próprios.

## Implementação

- `import_profiles` e `import_profile_versions` guardam mapeamentos e regras versionadas.
- `import_runs` guarda checksum SHA-256, arquivo, usuário, totais e resultado.
- `import_rows` preserva conteúdo, estado, erros e marcadores por linha.
- `loads.external_id` impede duplicidade da mesma viagem entre arquivos diferentes.
- O checksum impede reprocessamento acidental do mesmo arquivo.
- Cada linha cria carga histórica, receita e conferência de frete.
- A conferência usa diretamente as duas colunas do relatório; não aplica fórmula presumida.
- Datas do arquivo são interpretadas no fuso `America/Sao_Paulo`.
- O arquivo original não é gravado no servidor.

## Endpoint e tela

- `GET /api/v1/imports`
- `POST /api/v1/imports/copagril-report`
- Tela **Mais → Importações** com envio e histórico.

## Testes

- Importação completa de fixture com registros financeiros.
- Detecção de divergência.
- Idempotência por checksum.
- Rejeição de layout desconhecido.
- Validação adicional contra o arquivo real: 52/18/18.
- Total da suíte: 11 testes Pytest, Ruff, ESLint e build Next.js aprovados.

## Dados insuficientes

- A base textual não informa CNH dos motoristas nem capacidade/ano dos veículos; esses campos não
  serão inventados no seed operacional.
- O KML contém somente um `NetworkLink`; as coordenadas não estão incorporadas ao arquivo.
- O relatório é histórico de viagens, não a planilha de programação. A detecção de cancelamento
  aguarda uma amostra real da programação.
