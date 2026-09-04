# Rastreabilidade do MVP

| Requisito prático | Implementação | Evidência automática |
|---|---|---|
| Identificar vaga livre/ocupada | `main.py` e `app/domain.py` | `tests/unit/test_domain.py` |
| Consultar disponibilidade | painel em `static/` e `GET /api/readings/latest` | `tests/system/test_user_flow.py` |
| Persistir leituras | `SupabaseReadingRepository` e migração SQL | `tests/integration/test_supabase_repository.py` |
| Impedir publicação não autorizada | cabeçalho `X-Ingest-Key` | `tests/system/test_user_flow.py` |
| Deploy público | `api/index.py` e `vercel.json` | teste manual descrito em `docs/DEPLOY.md` |
| Ambiente reproduzível | `Dockerfile` e `compose.yaml` | build local/CI a ser registrado pela equipe |
| Qualidade no PR | workflow `.github/workflows/ci.yml` | check `tests` no GitHub |

## Regras de negócio implementadas

1. Uma vaga é livre quando sua contagem de pixels processados é menor que o limite configurado (padrão 900).
2. A quantidade livre deve estar entre zero e o total monitorado.
3. A quantidade ocupada é sempre `total - livres`.
4. Quando há detalhes individuais, sua quantidade deve coincidir com o total de vagas.
5. Apenas quem conhece a chave de ingestão pode publicar uma leitura.

