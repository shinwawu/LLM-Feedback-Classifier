from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from llm_feedback_classifier.graph import app_graph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
import uuid
from tenacity import retry, wait_exponential, stop_after_attempt
import logging

app = FastAPI(title="Customer Feedback API")
banco_de_tarefas = {}


# modelos de dados para entrada e saida da api
class FeedbackRequest(BaseModel):
    comentario: str


class AnalysisResponse(BaseModel):
    comentario_original: str
    sentimento: str
    prioridade: str
    resposta_sugerida: str
    validado_por_humano: bool


class ValidationRequest(BaseModel):
    resposta_final_aprovada: str


class RedraftRequest(BaseModel):
    comentario: str
    sentimento: str
    prioridade: str


# funcoes da api


@app.post("/analyze")
def analyze_async(request: FeedbackRequest, background_tasks: BackgroundTasks):
    """
    recebe o feedback do cliente, gera um id unico para a tarefa e registra no banco de memoria com o status processando.
    depois de processar o feedback, atualiza o banco com o resultado da llm ou com o erro caso tenha dado problema.
    """
    # gera um id unico
    task_id = str(uuid.uuid4())

    # registra o status como "PROCESSANDO"
    banco_de_tarefas[task_id] = {"status": "PROCESSANDO", "resultado": None}

    # processa o feedback em queue, de modo assincrono. Podendo lidar com varias requisicoes.
    background_tasks.add_task(processar_feedback_na_fila, task_id, request.comentario)

    # devolve a resposta instantaneamente para o usuário
    return {
        "task_id": task_id,
        "mensagem": "Feedback recebido e enviado para processamento",
    }


@app.get("/status/{task_id}")
def check_status(task_id: str):
    """
    verifica se a tarefa ja foi concluida ou se esta sendo processado ainda
    """
    if task_id not in banco_de_tarefas:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return banco_de_tarefas[task_id]


@app.post("/validate")
def validate_feedback(request: ValidationRequest):
    print(f"\nresposta aprovada e enviada:\n{request.resposta_final_aprovada}\n")
    return {"status": "sucesso", "resposta_enviada": request.resposta_final_aprovada}


@app.post("/redraft")
def redraft_feedback(request: RedraftRequest):
    # criacao de um modelo com maior temperatura para gerar uma resposta diferente da anterior
    llm_criativo = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.7)

    # criacao do prompt para a llm
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Você é um analista de atendimento sênior. O atendente humano rejeitou seu rascunho anterior. "
                "Escreva uma NOVA resposta para o cliente com uma abordagem diferente, mudando as palavras, mas "
                "mantendo o profissionalismo. Sentimento: {sentimento} | Prioridade: {prioridade}. "
                "O contato da equipe que irá entrar em contato é equipecostumerservice@washin.com"
                "Assine como 'Equipe de Costumer Service Washin'.",
            ),
            ("human", "Comentário do cliente: {comentario}"),
        ]
    )
    # chamada da llm para gerar um novo rascunho de resposta
    chain = prompt | llm_criativo
    resultado = chain.invoke(
        {
            "sentimento": request.sentimento,
            "prioridade": request.prioridade,
            "comentario": request.comentario,
        }
    )

    return {"nova_resposta": resultado.content}


# funcao para fazer retry
@retry(wait=wait_exponential(multiplier=2, min=2, max=10), stop=stop_after_attempt(3))
def invocar_ia_com_tentativas(estado_inicial):
    """
    chamada para classificar o feedback
    """
    return app_graph.invoke(estado_inicial)


def processar_feedback_na_fila(task_id: str, comentario: str):
    """
    para cada feedback, processa utilizando fila e funcao de retry para lidar com chamadas para api da google
    """
    try:
        estado_inicial = {
            "comentario_cliente": comentario,
            "validado_por_humano": False,
        }

        # chamada pelo retry
        resultado = invocar_ia_com_tentativas(estado_inicial)

        # att na memoria com o resultado
        banco_de_tarefas[task_id] = {"status": "CONCLUIDO", "resultado": resultado}

    except Exception as e:
        # mostra o erro no log para debug
        if hasattr(e, "last_attempt"):
            erro = e.last_attempt.exception()
        else:
            erro = e

        print(f"erro na tarefa {task_id}:")
        print(f"error: {erro}\n")

        banco_de_tarefas[task_id] = {
            "status": "ERRO",
            "detalhe": "modelo de llm indisponível. verifique os custos.",
        }
