# SmartParking — ParkingFAG

MVP que identifica vagas livres e ocupadas em imagens de vídeo/câmera e disponibiliza a situação em um painel web. O detector OpenCV roda no computador conectado à câmera; a API publicada na Vercel recebe as leituras e grava o histórico no PostgreSQL do Supabase.

## O que já está funcional

- detecção visual das vagas cadastradas em `CarParkPos`;
- painel responsivo com total, livres, ocupadas e mapa das vagas;
- API protegida por chave para receber as leituras;
- persistência real no Supabase quando as variáveis de ambiente estão configuradas;
- migração SQL versionada;
- testes de unidade, integração e sistema;
- CI automática em Pull Requests para a `main`;
- execução local direta ou com Docker Compose;
- estrutura pronta para deploy na Vercel.

## Arquitetura

```text
Câmera/vídeo -> detector OpenCV (main.py) -> API na Vercel
                                                   |
                                                   v
                                             Supabase/PostgreSQL
                                                   |
                                                   v
                                             painel no navegador
```

A câmera não roda dentro da Vercel. O detector roda perto da fonte de vídeo e envia somente o estado das vagas, uma solução compatível com o ambiente serverless e mais cuidadosa com a privacidade.

## Rodar localmente

Requer Python 3.12 ou mais recente.

1. Copie `.env.example` para `.env` e, se desejar testar apenas a interface, deixe as variáveis do Supabase vazias.
2. Inicie a aplicação web:

   ```bash
   python server.py
   ```

3. Abra `http://localhost:8000`.
4. Para executar o detector, instale as dependências e configure as variáveis do arquivo `.env` no terminal:

   ```bash
   pip install -r requirements-detector.txt
   python main.py
   ```

O detector funciona sem API, exibindo apenas a janela OpenCV. Para publicar leituras, defina `PARKING_API_URL` e use a mesma `PARKING_INGEST_KEY` configurada no servidor. `PARKING_VIDEO_SOURCE=0` seleciona a primeira webcam; sem essa variável é usado `video.mp4`.

Também é possível subir somente a aplicação web com:

```bash
docker compose up --build
```

## Testes

Todos usam apenas a biblioteca padrão do Python:

```bash
python -m unittest discover -s tests -v
```

- **Unidade:** regra que classifica uma vaga e cálculo da ocupação.
- **Integração:** contrato entre o repositório e a API REST do Supabase.
- **Sistema:** fluxo completo de publicação protegida e consulta da última leitura.

## Banco, deploy e processo de entrega

O roteiro completo está em [docs/DEPLOY.md](docs/DEPLOY.md). A migração está em `supabase/migrations/202609030001_create_parking_readings.sql`.

O desenvolvimento deve acontecer em uma branch de tarefa e chegar à `main` somente por Pull Request aprovado. O check obrigatório no GitHub é `tests`. Nunca coloque `SUPABASE_SECRET_KEY` no JavaScript ou no Git.

## Evidências da aula

- CI: aba **Actions** do repositório e check do Pull Request;
- banco como código: pasta `supabase/migrations`;
- deploy: URL pública da Vercel e leitura gravada no Supabase;
- teste com cliente: roteiro em [docs/TESTE-CLIENTE.md](docs/TESTE-CLIENTE.md);
- rastreabilidade do MVP: [docs/RASTREABILIDADE.md](docs/RASTREABILIDADE.md).
