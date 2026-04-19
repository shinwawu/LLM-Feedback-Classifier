import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from llm_feedback_classifier.state import FeedbackState, ClassificacaoFeedback

# load da env
load_dotenv()

# selecao do model e temperatura = 0 para respostas mais consistentes
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)


def classificar_comentario(state: FeedbackState):
    """
    classificacao do comentario do cliente usando a LLM, identificando a nota do feedback (positivo, negativo ou neutro) e a prioridade que deve ser dado
    (alta, media ou baixa).
    """
    print("o nó de classificar o comentário ativado")

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Você é um analista de customer success especialista em classificar feedbacks de clientes.",
            ),
            ("human", "Classifique o seguinte comentário:\n\n{comentario}"),
        ]
    )

    # fornecendo a estrutura de saída esperada para o LLM, para garantir que ele responda com os campos corretos e de forma consistente.
    llm_com_estrutura = llm.with_structured_output(ClassificacaoFeedback)

    # a chamada da llm
    chain = prompt | llm_com_estrutura

    # extrai o campo comentario_cliente e salva no prompt para a LLM, e depois retorna os campos sentimento e prioridade que a LLM classificou
    resultado = chain.invoke({"comentario": state["comentario_cliente"]})

    return {"sentimento": resultado.sentimento, "prioridade": resultado.prioridade}


def redigir_resposta(state: FeedbackState):
    """
    o modelo cria uma sugestao de resposta para que o humano possa revisar e aprovar, levando em consideração o sentimento e a prioridade do feedback.
    """
    print("o nó de redigir a resposta ativado")

    # construcao do prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Você é um analista de atendimento ao cliente sênior. Escreva uma resposta curta, educada e profissional "
                "para o cliente. Leve em consideração que o sentimento do cliente é {sentimento} e a prioridade é {prioridade}. "
                "Se for negativo, seja empático, peça desculpas e foque na resolução. O contato da equipe que irá entrar em contato é equipecostumerservice@washin.com "
                "Assine como 'Equipe de Costumer Service Washin'.",
            ),
            ("human", "Comentário do cliente: {comentario}"),
        ]
    )

    # a chamada da llm
    chain = prompt | llm

    # extrai os campos sentimento, prioridade e comentario_cliente do estado para o prompt, e depois retorna a resposta sugerida pela LLM para o cliente.
    resultado = chain.invoke(
        {
            "sentimento": state["sentimento"],
            "prioridade": state["prioridade"],
            "comentario": state["comentario_cliente"],
        }
    )

    return {"resposta_sugerida": resultado.content}
