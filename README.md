<a id="readme-top"></a>

<div align="center">
  <h1 align="center">Classificador de Feedback com LLM</h1>
  <p align="center">
    Sistema assíncrono de triagem, classificação e redação de respostas automatizadas utilizando Python, LangGraph, FastAPI e Streamlit.
    <br />
    <br />
  </p>
</div>

<details>
  <summary>Tabela de Conteúdos</summary>
  <ol>
    <li><a href="#sobre-o-projeto">Sobre o Projeto</a></li>
    <li><a href="#organizacao-e-estrutura">Organização e Estrutura</a></li>
    <li><a href="#arquitetura-e-fluxos">Arquitetura e Fluxos</a></li>
    <li><a href="#configuracao-de-ambiente">Configuração de Ambiente</a></li>
    <li><a href="#autor">Autor</a></li>
    <li><a href="#ideias">Melhorias possíveis</a></li>
  </ol>
</details>

---
<a name="sobre-o-projeto"></a>
## Sobre o Projeto

Este projeto automatiza a leitura, triagem e sugestão de respostas a feedbacks de clientes. Utilizando um fluxo assíncrono, o sistema envia o comentário para a LLM (Google Gemini via LangGraph), classifica o sentimento e a prioridade, e gera um rascunho de resposta que pode ser validado e aprovado por um atendente humano na interface web.

## <a id="organizacao-e-estrutura"></a>📂 Organização e Estrutura


Este projeto segue uma estrutura padronizada para garantir reprodutibilidade.

> **Nota sobre Convenção de Nomes:**
> O código foi modularizado para separar a interface do utilizador, a API de serviços e a lógica de inteligência artificial (grafos e nós).

```text
.
├── config/                 # Configurações e variáveis de ambiente
│   └── .env.example        # Template com as variáveis necessárias (substitua pelo .env)
│
├── llm_feedback_classifier/# Módulo principal da aplicação
│   ├── api.py              # Backend FastAPI (Rotas, Webhooks e Fila Assíncrona)
│   ├── frontend.py         # Frontend Streamlit (Interface Human-in-the-Loop)
│   ├── graph.py            # Orquestrador do LangGraph (Nodes e Edges)
│   ├── nodes.py            # Funções de classificação e redação com LLM
│   └── state.py            # Definições de tipos e esquemas Pydantic
│
├── .gitignore              # Arquivos a serem ignorados pelo git
├── LICENSE                 # Licença do projeto
├── pyproject.toml          # Dependências e config (UV workspace)
└── README.md               # Documentação principal
``` 

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>
## <a id="arquitetura-e-fluxos"></a>🧠 Arquitetura e Fluxos

O sistema funciona com uma arquitetura assíncrona e Human-in-the-Loop. Ele divide-se em três camadas principais que trabalham em conjunto:

Front-end (Interface- Streamlit): Onde o usuário insere o feedback do cliente. O front-end não trava à espera da IA; ele envia o texto e faz polling (verificação da task) a cada 2 segundos até a sugestão de resposta estar pronto.

Back-end (API - FastAPI): Recebe o feedback e coloca a tarefa numa fila de processamento em segundo plano (BackgroundTasks). A API possui um sistema de resiliência usando a biblioteca Tenacity, que aplica wait para evitar bloqueios por limite de quota na API da Google.

Orquestrador de IA (LangGraph + Gemini): o workflow é gerido por um grafo (StateGraph) composto por dois nós sequenciais:

Nó Classificador: Lê o comentário e, forçando uma saída estruturada (Pydantic), extrai o Sentimento (Positivo, Negativo, Neutro) e a Prioridade (Alta, Média, Baixa).

Nó Redator: Utiliza as informações do nó anterior para redigir uma resposta de atendimento empática e personalizada com algumas instruções.

Após a LLM devolver o resultado ao front-end, o usuário pode ler, editar o texto livremente na caixa de texto e aprovar (bate na api /validate), ou clicar em "Refazer Rascunho" (bate na api/redraft) para a LLM gerar uma nova versão instantaneamente, ao gerar uma outra versão, é instanciado um modelo com temperatura um pouco maior.


### 🔄 Fluxos e Caminhos Possíveis (Arquitetura em Grafo)

O sistema foi desenhado para lidar tanto com o cenário ideal (*Happy Path*) quanto com exceções, falhas na API e intervenção humana. Abaixo estão os mapas de fluxo para cada cenário:

#### 1. O Caminho Ideal 
Fluxo padrão onde tudo ocorre sem interrupções e o usuário aprova o texto da IA de primeira.

```text
[Atendente Insere Texto] 
       │
       ▼
[FastAPI: Rota /analyze] ──(cria a id da tarefa)──> [Streamlit: Inicia Polling]
       │                                                 ▲
       ▼                                                 │
[Background Task]                                        │ (Pergunta a cada 2s se está concluido)
       │                                                 │
       ▼                                                 │
[LangGraph: Nó Classificador]                            │
       │                                                 │
       ▼                                                 │
[LangGraph: Nó Redator]                                  │
       │                                                 │
       ▼                                                 │
[Memória: Status = CONCLUIDO] ───────────────────────────┘
       │
       ▼
[Streamlit: Exibe Rascunho] ──> [usuário clica "Aprovar"] ──> [FIM]
```
### 🔄 Fluxos e Caminhos Possíveis (Arquitetura em Grafo)

O sistema foi desenhado para lidar tanto com o cenário ideal (*Happy Path*) quanto com exceções, falhas na API e intervenção humana. Abaixo estão os mapas de fluxo para cada cenário:

#### 2. O Caminho com reescrita 
Fluxo padrão onde o usuário não aprovou e gostaria de reescrever o texto da IA de primeira.

```text
[Atendente Insere Texto] 
       │
       ▼
[FastAPI: Rota /analyze] ──(cria a id da tarefa)──> [Streamlit: Inicia Polling]
       │                                                 ▲
       ▼                                                 │
[Background Task]                                        │ (Pergunta a cada 2s se está concluido)
       │                                                 │
       ▼                                                 │
[LangGraph: Nó Classificador]                            │
       │                                                 │
       ▼                                                 │
[LangGraph: Nó Redator]                                  │
       │                                                 │
       ▼                                                 │
[Memória: Status = CONCLUIDO] ───────────────────────────┘
       │
       ▼
[Streamlit: Exibe Rascunho] ──> [usuário clica "Refazer Rascunho"]
       ▲                                   │
       │                                   │  
[FastAPI: Rota /redraft]<──────────────────┘
       │
       ▼
[usuário clica "Aprovar"] ──> [FIM]

``` 

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>
## <a id="configuracao-de-ambiente"></a>🚀 Configuração de Ambiente (Como Executar)

Este projeto utiliza o gestor de pacotes uv para uma execução rápida e com dependências isoladas.

1. Configurar as Variáveis de Ambiente
O projeto necessita de uma chave de API válida do Google AI Studio. Na raiz do projeto, crie o ficheiro .env baseado no modelo fornecido:

| Variável | Descrição |
|----------|-----------|
| `GOOGLE_API_KEY` | A Chave da API |

### Opção A: Execução via Docker 
O projeto contém com um docker-compose.yml configurado para subir a API e o Front-end simultaneamente em redes isoladas.

Certifique-se de que o Docker Desktop está instalado e a correr na sua máquina.

Na raiz do projeto, execute:
```
Bash
docker compose up --build
```
Acesse a aplicação:

Front-end (Painel do Usuário): http://localhost:8501

Back-end (Swagger UI / Docs da API): http://localhost:8000/docs


### Opção B: Execução Local / Manual (com uv) 
Se preferir rodar os processos diretamente na sua máquina local para desenvolvimento focado:

Certifique-se de ter o uv instalado.

Abra dois terminais na raiz do projeto.

Terminal 1 (Back-end FastAPI):
```
Bash
uv run uvicorn llm_feedback_classifier.api:app --reload
```

Terminal 2 (Front-end Streamlit):

```
Bash
uv run streamlit run llm_feedback_classifier/frontend.py

```

## <a id="autor"></a> 👤 Autor

| Nome | Email |
|------|-------|
| **Washington Wu** |  washingtonying@hotmail.com |

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>


## <a id="ideias"></a> Ideias 🖥️

- Melhoria na Interface do Streamlit para melhorar a experiência do usuário
- Uma página de métricas
- Testes unitários automatizados com pytest
- Um Agente validador do rascunho, automatizando a verificação do rascunho
- Cache semântico, para casos o feedbacks forem idênticos, já reaproveitamos a resposta gerada anteriormente

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>
