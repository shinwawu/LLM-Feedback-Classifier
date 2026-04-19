from langgraph.graph import StateGraph, END
from llm_feedback_classifier.state import FeedbackState
from llm_feedback_classifier.nodes import classificar_comentario, redigir_resposta


def criar_grafo():
    # inicializacao do grafo e definicao do estado inicial,
    # passando a estrutura do objeto que contém os campos que serão usados e construídos ao longo do processo (comentário, sentimento, prioridade, resposta sugerida e se foi validado por humano ou não).
    workflow = StateGraph(FeedbackState)

    # construindo o fluxo do grafo, adicionando os funções entre eles.
    workflow.add_node("classificador", classificar_comentario)
    workflow.add_node("redator", redigir_resposta)

    # o fluxo definido = Entrada -> Classificador -> Redator -> Fim
    workflow.set_entry_point("classificador")
    workflow.add_edge("classificador", "redator")
    workflow.add_edge("redator", END)

    # compila e retorna o fluxo
    return workflow.compile()


# grafo compilado pronta para uso
app_graph = criar_grafo()
