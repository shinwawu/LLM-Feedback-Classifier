from typing import TypedDict
from pydantic import BaseModel, Field


# o estado que vai passar por cada step/nó do grafo, com os campos que serão usados e construídos ao longo do processo.
class FeedbackState(TypedDict):
    comentario_cliente: str
    sentimento: str
    prioridade: str
    resposta_sugerida: str
    validado_por_humano: bool


# saida da LLM, passando a descrição de cada campo para o prompt do LLM e o seu retorno.
class ClassificacaoFeedback(BaseModel):
    sentimento: str = Field(
        description="Classifique como: Positivo, Negativo ou Neutro."
    )
    prioridade: str = Field(
        description="Classifique a prioridade de atendimento como: Alta, Média ou Baixa. Reclamações graves são Alta."
    )
