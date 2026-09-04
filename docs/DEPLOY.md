# Configuração de entrega e deploy

## 1. Supabase

1. Crie um projeto no Supabase.
2. No computador de um integrante, instale a Supabase CLI e autentique.
3. Na raiz do repositório, execute `supabase link --project-ref SEU_PROJECT_REF`.
4. Aplique a migração versionada com `supabase db push`.
5. Confirme no Table Editor a existência de `parking_readings`.

Para a Vercel, copie do painel do Supabase a URL do projeto e uma **secret key**. Essa chave privilegiada deve existir somente nas variáveis protegidas do servidor. O navegador nunca recebe a chave. A variável legada `SUPABASE_SERVICE_ROLE_KEY` ainda é aceita, mas `SUPABASE_SECRET_KEY` é a opção atual recomendada.

## 2. Vercel

1. Importe o repositório GitHub na Vercel.
2. Mantenha a raiz do projeto como diretório de build; a Vercel detecta `api/index.py` como a função Python que atende `/api/*`.
3. Cadastre `SUPABASE_URL`, `SUPABASE_SECRET_KEY` e uma `PARKING_INGEST_KEY` longa e aleatória.
4. Publique a branch `main`.
5. Abra `https://SEU-DOMINIO.vercel.app/api/health` e confirme `database: supabase`.
6. Configure no computador da câmera `PARKING_API_URL=https://SEU-DOMINIO.vercel.app` e a mesma `PARKING_INGEST_KEY`.
7. Execute `main.py`, aguarde uma leitura e confirme o painel e a tabela no Supabase.

Se `/api/health` mostrar `database: memory`, as variáveis do Supabase estão ausentes. Esse modo é útil apenas para desenvolvimento e não atende à entrega final.

## 3. Proteção da `main` no GitHub

Em **Settings > Rules > Rulesets**, crie uma regra para a branch `main` com:

- exigir Pull Request antes do merge;
- exigir pelo menos uma aprovação;
- dispensar aprovações antigas quando houver novos commits;
- exigir resolução das conversas;
- exigir o status check `tests`;
- bloquear force push e exclusão;
- não permitir bypass para os integrantes da equipe.

Faça a alteração a partir de uma Issue, crie a branch, envie commits pequenos e abra o Pull Request. Tire capturas da regra e do check aprovado para a evidência.

## 4. Checklist de aceite

- [ ] migração aplicada no Supabase;
- [ ] variáveis cadastradas na Vercel sem expor segredos;
- [ ] endereço público abre em outro dispositivo;
- [ ] detector publica uma leitura real;
- [ ] leitura aparece no painel e na tabela;
- [ ] CI passa no Pull Request;
- [ ] Pull Request recebe aprovação antes do merge;
- [ ] teste com cliente é gravado e registrado.
