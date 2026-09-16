from pathlib import Path
from datetime import date
import io
import textwrap
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether, Preformatted)

OUT = Path(__file__).with_name("relatorio-auditoria-seguranca.pdf")
PROJECT = "SmartParking - ParkingFAG"
DATE = "16/09/2026"
PALETTE = {"Crítica":"#B91C1C","Alta":"#EA580C","Média":"#D97706","Baixa":"#2563EB","Ponto forte":"#059669"}

findings = [
 {"id":1,"cat":"Inputs / XSS","sev":"Alta","loc":"static/app.js:10-14; app/domain.py:31-33,44-50","title":"XSS armazenado no mapa de vagas via space.index","evidence":'''// static/app.js:10-14\nbyId("spaces").innerHTML = spaces.map((space) => `\n  <article class="space ${space.is_free ? "free" : "occupied"}">\n    <strong>Vaga ${space.index}</strong>\n    <span>${space.is_free ? "Livre" : "Ocupada"}</span>\n  </article>`).join("");\n\n# app/domain.py:31-33,48\nnormalized_spaces = spaces or []\nif normalized_spaces and len(normalized_spaces) != total_spaces:\n    raise ValueError(...)\n...\nspaces=payload.get("spaces") or [],''',"why":"O backend aceita os objetos internos de spaces sem validar o tipo/conteúdo de index. A leitura é persistida e depois retornada por /api/readings/latest. O navegador interpola space.index em innerHTML. Um cliente que possua a chave de ingestão pode gravar marcação HTML/JavaScript e executar código no navegador de quem abrir o painel. Condição: capacidade de publicar uma leitura (PARKING_INGEST_KEY válida).","fix":"Validar cada item de spaces no backend (index e pixel_count inteiros; is_free booleano) e construir o DOM com textContent/createElement, sem innerHTML para dados dinâmicos."},
 {"id":2,"cat":"Chaves expostas / configuração","sev":"Alta","loc":".env.example:5; README.md:35; app/web.py:41,64-67","title":"Chave pública de exemplo pode virar credencial real de ingestão","evidence":'''# .env.example:5\nPARKING_INGEST_KEY=troque-por-uma-chave-longa\n\n# README.md:35\nCopie `.env.example` para `.env` ...\n\n# app/web.py:41,64-67\nself.ingest_key = ... os.getenv("PARKING_INGEST_KEY", "")\nif not self.ingest_key: ...\nif headers.get("x-ingest-key") != self.ingest_key:\n    return json_response(401, ...)''',"why":"A documentação orienta copiar o arquivo de exemplo, e o servidor só rejeita chave vazia. Se o operador não substituir o placeholder conhecido, 'troque-por-uma-chave-longa' passa a ser uma credencial válida e pública. Qualquer pessoa que conheça o repositório pode publicar leituras. Condição: deploy realizado com o placeholder sem sobrescrita.","fix":"Falhar no startup quando PARKING_INGEST_KEY estiver ausente, curta ou igual a placeholders conhecidos; documentar geração criptograficamente aleatória."},
 {"id":3,"cat":"Inputs / disponibilidade","sev":"Média","loc":"server.py:10-14; app/web.py:94-105","title":"Corpo HTTP é lido integralmente antes da autenticação, sem limite","evidence":'''# server.py:10-14\nlength = int(self.headers.get("Content-Length", "0"))\nbody = self.rfile.read(length) if length else b""\nresponse = application.dispatch(...)\n\n# app/web.py:94-105\nchunks = []\n...\nchunks.append(message.get("body", b""))\n...\nresponse = parking.dispatch(..., b"".join(chunks))''',"why":"Tanto o servidor local quanto o adaptador ASGI acumulam o corpo completo em memória antes de ParkingApplication verificar X-Ingest-Key. Um cliente não autenticado pode enviar corpos muito grandes e consumir memória/conexões. Exploração depende de o endpoint estar alcançável e de limites do proxy/plataforma não bloquearem antes.","fix":"Aplicar limite de Content-Length/body no primeiro ponto de entrada, rejeitando com 413 antes de acumular o corpo; manter limites também no proxy/plataforma."},
 {"id":4,"cat":"Inputs / disponibilidade","sev":"Média","loc":"app/domain.py:27-33,44-50","title":"Leitura aceita quantidade de vagas sem limite superior","evidence":'''# app/domain.py:27-33\nif total_spaces < 0:\n    raise ValueError(...)\nif not 0 <= free_spaces <= total_spaces:\n    raise ValueError(...)\nnormalized_spaces = spaces or []\nif normalized_spaces and len(normalized_spaces) != total_spaces:\n    raise ValueError(...)''',"why":"Há validação de consistência, mas nenhum teto para total_spaces nem para a lista spaces. Um publicador autenticado pode enviar uma leitura extremamente grande, elevando CPU, memória, tráfego e armazenamento no Supabase. Condição: PARKING_INGEST_KEY válida (ou exploração combinada com o achado 2).","fix":"Definir MAX_SPACES compatível com o estacionamento e rejeitar total_spaces/listas acima do limite; limitar também tamanho e campos de cada item."},
 {"id":5,"cat":"Inputs / desserialização","sev":"Média","loc":"main.py:97-98; Parkingspace picker.py:6-10; maintrackbars.py:8-9","title":"Desserialização insegura de CarParkPos com pickle.load","evidence":'''# main.py:97-98\nwith (ROOT / "CarParkPos").open("rb") as positions_file:\n    positions = pickle.load(positions_file)\n\n# Parkingspace picker.py:6-8\nwith open('CarParkPos', 'rb') as f:\n    posList = pickle.load(f)\n\n# maintrackbars.py:8-9\nwith open('CarParkPos', 'rb') as f:\n    posList = pickle.load(f)''',"why":"pickle executa instruções de desserialização e não é seguro para conteúdo não confiável. Se CarParkPos puder ser substituído (arquivo baixado, artefato adulterado, máquina compartilhada ou comprometimento da cadeia de entrega), abrir qualquer um desses scripts pode executar código arbitrário com os privilégios do usuário. Condição: atacante precisa conseguir adulterar CarParkPos antes da execução.","fix":"Substituir pickle por JSON/CSV com validação estrita de uma lista de pares inteiros; se legado for inevitável, não aceitar arquivos externos e verificar integridade/autenticidade antes de carregar."},
]

strengths = [
"Supabase: RLS está habilitado em supabase/migrations/202609030001_create_parking_readings.sql:15; anon e authenticated têm privilégios revogados nas linhas 17-19. O acesso privilegiado fica no backend via service_role.",
"POST /api/readings: app/web.py:63-67 exige X-Ingest-Key e retorna 503 se a chave não estiver configurada e 401 quando diverge; tests/system/test_user_flow.py:27-35 cobre o fluxo não autorizado/autorizado.",
"Traversal de arquivos estáticos: app/web.py:77-84 resolve o caminho e rejeita candidatos fora de STATIC (linhas 79-81).",
"Campos numéricos principais: app/domain.py:27-33 valida total/free e consistência da contagem; source é limitado a 100 caracteres na linha 39.",
"Segredos reais: varredura do working tree e dos 4 commits disponíveis não encontrou chave Supabase, token, senha ou chave privada real commitida. .gitignore:3 ignora .env; README.md:74 orienta não versionar SUPABASE_SECRET_KEY.",
"Frontend: free_spaces, occupied_spaces, total_spaces, captured_at e status usam textContent (static/app.js:5-8,24-28), evitando HTML nesses pontos.",
]

coverage = [
("Stack","Python 3.12; backend HTTP/ASGI próprio (biblioteca padrão), sem Flask/FastAPI/Django; repositório REST manual para Supabase/PostgreSQL, sem ORM/query builder; autenticação de escrita por chave compartilhada X-Ingest-Key; frontend HTML/CSS/JavaScript vanilla; Dockerfile + compose.yaml; Vercel via api/index.py; migração SQL Supabase. Nenhum Helm/Terraform encontrado. O ZIP não contém .github/workflows, embora README mencione CI."),
("1. Banco sem tranca","Mecanismo detectado: RLS no Supabase + revogação de anon/authenticated, com service_role somente no backend. Não existe modelo de usuário/tenant/workspace no domínio; o painel é público por desenho. Nenhuma quebra de isolamento por tenant/owner foi encontrada. O GET latest usa service_role, mas expõe apenas a última ocupação pública prevista pelo produto."),
("2. Permissão no navegador","Não há papéis, isAdmin/canEdit/role, login ou UI administrativa no frontend. Portanto, não há gates de papel a cruzar. A única escrita é POST /api/readings e a checagem ocorre no servidor."),
("3. IDOR","Foram percorridos todos os handlers em ParkingApplication.dispatch: GET /api/health, GET /api/readings/latest, POST /api/readings, GET / e GET /static/*. Não existem rotas por ID nem objetos pertencentes a usuário/tenant; categoria não aplicável."),
("4. Chaves hardcode","Working tree, configs, docs, compose/Docker e histórico Git disponível foram pesquisados. Não há segredo real hardcoded. Há, porém, um placeholder público de PARKING_INGEST_KEY que o runtime aceita como segredo real se copiado sem troca (Achado 2). Nenhum bundle/minificador: static/app.js foi inspecionado diretamente e não contém chave."),
("5. Inputs / XSS","Foi pesquisado innerHTML/equivalentes, eval/new Function, URLs dinâmicas e sanitização. Existe um sink innerHTML em static/app.js:10-14 e não há biblioteca de sanitização; combinado com spaces sem schema interno no backend, gera XSS armazenado (Achado 1). Não foram encontrados markdown, eval/new Function ou templates de e-mail."),
]

issues = [
(1,"[Segurança] Eliminar XSS armazenado no mapa de vagas","security, alta",findings[0]),
(2,"[Segurança] Rejeitar PARKING_INGEST_KEY padrão ou fraca","security, alta",findings[1]),
(3,"[Segurança] Limitar tamanho de requisições e leituras de estacionamento","security, média",None),
(4,"[Segurança] Substituir pickle por formato seguro em CarParkPos","security, média",findings[4]),
]

styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='Title2', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=25, leading=30, textColor=colors.HexColor('#0F172A'), spaceAfter=18))
styles.add(ParagraphStyle(name='H1x', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=17, leading=21, textColor=colors.HexColor('#0F172A'), spaceBefore=8, spaceAfter=10))
styles.add(ParagraphStyle(name='H2x', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#334155'), spaceBefore=8, spaceAfter=6))
styles.add(ParagraphStyle(name='Bodyx', parent=styles['BodyText'], fontName='Helvetica', fontSize=9.2, leading=13, textColor=colors.HexColor('#334155'), spaceAfter=6))
styles.add(ParagraphStyle(name='Small', parent=styles['BodyText'], fontSize=7.5, leading=10, textColor=colors.HexColor('#475569')))
styles.add(ParagraphStyle(name='Codex', parent=styles['Code'], fontName='Courier', fontSize=6.7, leading=8.4, backColor=colors.HexColor('#F8FAFC'), borderColor=colors.HexColor('#E2E8F0'), borderWidth=.5, borderPadding=6, spaceAfter=8))

def chart_donut():
    counts={s:sum(f['sev']==s for f in findings) for s in ['Crítica','Alta','Média','Baixa']}
    labels=[k for k,v in counts.items() if v]; vals=[v for v in counts.values() if v]; cols=[PALETTE[k] for k,v in counts.items() if v]
    fig,ax=plt.subplots(figsize=(4.2,3.1)); ax.pie(vals,labels=labels,autopct='%1.0f',colors=cols,wedgeprops={'width':.42,'edgecolor':'white'},textprops={'fontsize':9}); ax.set_title('Achados por severidade',fontsize=11); fig.tight_layout()
    b=io.BytesIO(); fig.savefig(b,format='png',dpi=180,bbox_inches='tight',transparent=False); plt.close(fig); b.seek(0); return b

def chart_bar():
    cats=[]
    for f in findings:
        if f['cat'] not in cats: cats.append(f['cat'])
    vals=[sum(x['cat']==c for x in findings) for c in cats]
    fig,ax=plt.subplots(figsize=(5.5,3.2)); ax.bar(range(len(cats)),vals,color='#64748B'); ax.set_xticks(range(len(cats)),[c.replace(' / ','/\n') for c in cats],fontsize=7); ax.set_ylabel('Achados'); ax.set_title('Achados por categoria',fontsize=11); ax.set_ylim(0,max(vals)+1); ax.grid(axis='y',alpha=.2); fig.tight_layout()
    b=io.BytesIO(); fig.savefig(b,format='png',dpi=180,bbox_inches='tight'); plt.close(fig); b.seek(0); return b

def header_footer(canvas,doc):
    canvas.saveState(); w,h=A4
    canvas.setStrokeColor(colors.HexColor('#E2E8F0')); canvas.line(2*cm,h-1.45*cm,w-2*cm,h-1.45*cm)
    canvas.setFont('Helvetica',7.5); canvas.setFillColor(colors.HexColor('#64748B')); canvas.drawString(2*cm,h-1.15*cm,'Relatório de Auditoria de Segurança - SmartParking - ParkingFAG'); canvas.drawRightString(w-2*cm,1.15*cm,f'Página {doc.page}'); canvas.restoreState()

doc=SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=2*cm,leftMargin=2*cm,topMargin=1.8*cm,bottomMargin=1.8*cm,title=f'Relatório de Auditoria de Segurança - {PROJECT}')
story=[]
story += [Spacer(1,2.2*cm), Paragraph('RELATÓRIO DE AUDITORIA<br/>DE SEGURANÇA',styles['Title2']), Paragraph(PROJECT,ParagraphStyle(name='cover',parent=styles['H1x'],fontSize=15,textColor=colors.HexColor('#059669'))), Spacer(1,.5*cm), Paragraph(f'<b>Data:</b> {DATE}',styles['Bodyx']), Paragraph('<b>Escopo:</b> código-fonte entregue no ZIP, frontend, backend, migração Supabase, Docker/Compose, documentação, testes e histórico Git incluído no pacote.',styles['Bodyx']), Spacer(1,.3*cm), Paragraph('<b>Nota metodológica:</b> as cinco categorias solicitadas foram mapeadas para a stack detectada. Foram percorridos todos os handlers do backend, os sinks de HTML do frontend, configuração/deploy e os quatro commits presentes no histórico Git. Somente achados demonstráveis no código foram classificados como falha.',styles['Bodyx']), PageBreak()]

story += [Paragraph('1. Resumo executivo',styles['H1x'])]
sevcounts={s:sum(f['sev']==s for f in findings) for s in ['Crítica','Alta','Média','Baixa']}
summary_data=[[Paragraph('<b>Total</b>',styles['Small']),Paragraph('<b>Crítica</b>',styles['Small']),Paragraph('<b>Alta</b>',styles['Small']),Paragraph('<b>Média</b>',styles['Small']),Paragraph('<b>Baixa</b>',styles['Small'])],[str(len(findings)),str(sevcounts['Crítica']),str(sevcounts['Alta']),str(sevcounts['Média']),str(sevcounts['Baixa'])]]
t=Table(summary_data,colWidths=[3.1*cm]*5,rowHeights=[.6*cm,.7*cm]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#F1F5F9')),('ALIGN',(0,0),(-1,-1),'CENTER'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#CBD5E1')),('INNERGRID',(0,0),(-1,-1),.25,colors.HexColor('#E2E8F0')),('FONTNAME',(0,1),(-1,1),'Helvetica-Bold'),('FONTSIZE',(0,1),(-1,1),13)])); story += [t,Spacer(1,.3*cm)]
story += [Table([[Image(chart_donut(),width=7.3*cm,height=5.4*cm),Image(chart_bar(),width=8.2*cm,height=4.8*cm)]],colWidths=[7.6*cm,8.4*cm]),Spacer(1,.2*cm)]
story += [Paragraph('Os riscos centrais são a possibilidade de XSS armazenado no painel, a aceitação de uma chave de ingestão pública de exemplo quando não substituída, e riscos de disponibilidade/desserialização. Não foram verificadas falhas de IDOR ou de autorização por papel porque o projeto não possui usuários, tenants, papéis nem rotas por ID.',styles['Bodyx'])]

story += [Paragraph('2. Stack e cobertura metodológica',styles['H1x'])]
for title,text in coverage: story += [Paragraph(title,styles['H2x']),Paragraph(text,styles['Bodyx'])]

story += [Paragraph('3. Pontos fortes',styles['H1x'])]
for x in strengths: story.append(Paragraph('• '+x,styles['Bodyx']))
story += [Paragraph('4. Pontos fracos',styles['H1x']),Paragraph('Os pontos fracos verificados concentram-se em validação de entrada e hardening operacional: dados internos de spaces chegam ao DOM sem escaping; o placeholder da chave de ingestão pode ser aceito como segredo; não há limites explícitos de corpo/quantidade; e três utilitários carregam pickle sem autenticação do arquivo.',styles['Bodyx'])]

story += [PageBreak(),Paragraph('5. Achados detalhados',styles['H1x'])]
for f in findings:
    chip=f'<font color="{PALETTE[f["sev"]]}"><b>{f["sev"]}</b></font>'
    story += [KeepTogether([Paragraph(f'{f["id"]}. {f["title"]}',styles['H2x']),Table([[Paragraph(chip,styles['Small']),Paragraph('<b>'+f['cat']+'</b>',styles['Small']),Paragraph(f['loc'],styles['Small'])]],colWidths=[2*cm,4.2*cm,9.4*cm],style=[('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F8FAFC')),('BOX',(0,0),(-1,-1),.5,colors.HexColor('#E2E8F0')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6)]),Spacer(1,.12*cm),Preformatted(f['evidence'],styles['Codex']),Paragraph('<b>Por que é explorável:</b> '+f['why'],styles['Bodyx']),Paragraph('<b>Correção:</b> '+f['fix'],styles['Bodyx']),Spacer(1,.2*cm)])]

story += [Paragraph('6. Recomendações priorizadas',styles['H1x'])]
recs=[('P1','Remover o sink innerHTML para dados dinâmicos e validar o schema de cada vaga no backend.'),('P1','Rejeitar PARKING_INGEST_KEY de exemplo/fraca no startup e rotacionar qualquer ambiente que tenha usado o placeholder.'),('P2','Impor limites de body e MAX_SPACES, com testes para 413/422 e cargas extremas.'),('P2','Migrar CarParkPos de pickle para JSON/CSV validado.'),('P3','Adicionar testes de segurança regressivos: payload XSS, chave placeholder, corpo acima do limite e schema inválido.')]
for p,text in recs: story.append(Paragraph(f'<b>{p}</b> - {text}',styles['Bodyx']))

story += [PageBreak(),Paragraph('7. ISSUES PARA O GITHUB',styles['H1x']),Paragraph('Os blocos abaixo estão prontos para copiar e colar. Achados de limite de body e limite de vagas foram agrupados para evitar spam.',styles['Bodyx'])]

def issue_block(n,title,labels,desc,evidence,impact,fix,criteria):
    txt=f'''--- ISSUE {n} ---\n# {title}\n\n**Labels sugeridas:** {labels}\n\n## Descrição\n{desc}\n\n## Evidência\n{evidence}\n\n## Impacto\n{impact}\n\n## Sugestão de correção\n{fix}\n\n## Critérios de aceite\n{criteria}\n--- FIM ISSUE {n} ---'''
    wrapped='\n'.join('\n'.join(textwrap.wrap(line, width=100, replace_whitespace=False, drop_whitespace=False)) if len(line)>100 else line for line in txt.splitlines())
    return Preformatted(wrapped,ParagraphStyle(name=f'issue{n}',parent=styles['Codex'],fontSize=6.2,leading=7.8))

f=findings[0]; story += [issue_block(1,issues[0][1],issues[0][2],f['why'],f['loc']+'\n'+f['evidence'], 'Execução de JavaScript no contexto do painel, permitindo manipular a interface e agir com as permissões/origem do site.',f['fix'],'- [ ] Nenhum dado de `spaces` é inserido via `innerHTML`.\n- [ ] `index`/`pixel_count` aceitam apenas inteiros e `is_free` apenas booleano.\n- [ ] Payload com `<img onerror=...>` não executa script.\n- [ ] Teste automatizado cobre o caso.')]
f=findings[1]; story += [issue_block(2,issues[1][1],issues[1][2],f['why'],f['loc']+'\n'+f['evidence'],'Publicação não autorizada de leituras e possível encadeamento com o XSS armazenado.',f['fix'],'- [ ] Startup/deploy rejeita `troque-por-uma-chave-longa`.\n- [ ] Chaves abaixo do comprimento/política definida são rejeitadas.\n- [ ] Documentação ensina gerar segredo aleatório.\n- [ ] Teste automatizado cobre placeholder e chave válida.')]
story += [issue_block(3,issues[2][1],issues[2][2],findings[2]['why']+' Além disso, '+findings[3]['why'],findings[2]['loc']+'\n'+findings[2]['evidence']+'\n\n'+findings[3]['loc']+'\n'+findings[3]['evidence'],'Consumo excessivo de memória/CPU/tráfego/armazenamento e degradação ou indisponibilidade do serviço.', 'Aplicar limite de body antes da autenticação/acúmulo e definir MAX_SPACES/schema com limites de tamanho.','- [ ] Corpo acima do limite retorna 413 sem ser acumulado integralmente.\n- [ ] `total_spaces` acima de MAX_SPACES retorna 422.\n- [ ] `spaces` acima do limite é rejeitado.\n- [ ] Testes cobrem servidor HTTP e camada de aplicação.')]
f=findings[4]; story += [issue_block(4,issues[3][1],issues[3][2],f['why'],f['loc']+'\n'+f['evidence'],'Execução arbitrária de código local se o arquivo CarParkPos for adulterado.',f['fix'],'- [ ] Nenhum dos três scripts usa `pickle.load` para CarParkPos.\n- [ ] Formato substituto aceita somente coordenadas inteiras válidas.\n- [ ] Arquivo malformado falha de forma segura.\n- [ ] Testes cobrem leitura válida e inválida.')]

story += [Spacer(1,.2*cm),Paragraph('<b>Fim do relatório.</b>',styles['Bodyx'])]
doc.build(story,onFirstPage=header_footer,onLaterPages=header_footer)
print(OUT)
