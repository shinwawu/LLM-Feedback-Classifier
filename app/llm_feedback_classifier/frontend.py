import streamlit as st
import requests
import time
import os

# configuração da URL da nossa API local

API_URL = os.getenv("API_URL", "http://localhost:8000")

# configuração da página Streamlit
st.set_page_config(page_title="Classificador de feedback", layout="centered")

st.title("🤖 Classificador de Feedback com LLM")
st.markdown("Valide os feedbacks classificados pela LLM e aprove as respostas.")
st.divider()


# usamos o session_state para não perder os dados quando a tela recarregar
if "analise_atual" not in st.session_state:
    st.session_state.analise_atual = None


# 1. Entrada do comentário e envio para análise


novo_comentario = st.text_area(
    "Insira o comentário do cliente para análise:", height=100
)

if st.button("Analisar com IA", type="primary"):
    if novo_comentario.strip() == "":
        st.warning("Por favor, insira um comentário válido.")
    else:
        with st.spinner("Enviando para a fila de processamento"):
            # 1. Manda a requisição para iniciar o trabalho assíncrono
            resposta = requests.post(
                f"{API_URL}/analyze", json={"comentario": novo_comentario}
            )

            if resposta.status_code == 200:
                task_id = resposta.json()["task_id"]
                st.toast("Tarefa na fila. Aguardando a LLM")

                # 2. Inicia a verificação do status da tarefa em loop
                status_concluido = False

                # Barra de progresso visual enquanto espera
                with st.spinner(
                    "A LLM está analisando o sentimento e redigindo o rascunho..."
                ):
                    while not status_concluido:
                        time.sleep(2)
                        # verifica a cada 2 segundos se a tarefa já foi concluída
                        req_status = requests.get(f"{API_URL}/status/{task_id}")

                        if req_status.status_code == 200:
                            dados_status = req_status.json()

                            if dados_status["status"] == "CONCLUIDO":
                                # pega o resultado de dentro da memoria
                                st.session_state.analise_atual = dados_status[
                                    "resultado"
                                ]
                                status_concluido = True

                            elif dados_status["status"] == "ERRO":
                                st.error(
                                    f"erro no processamento da llm: {dados_status.get('detalhe')}"
                                )
                                break
                        else:
                            st.error("Erro ao checar o status no servidor.")
                            break
            else:
                st.error(f"Erro na API: {resposta.text}")

# 2. exibição dos Resultados e Validação Humana
if st.session_state.analise_atual:
    dados = st.session_state.analise_atual

    st.subheader("📊 Classificação da LLM")
    col1, col2 = st.columns(2)

    with col1:
        cor_sentimento = (
            "🟢"
            if dados["sentimento"].lower() == "positivo"
            else "🔴" if dados["sentimento"].lower() == "negativo" else "⚪"
        )
        st.info(f"**Sentimento:** {cor_sentimento} {dados['sentimento']}")

    with col2:
        cor_prioridade = (
            "🚨"
            if dados["prioridade"].lower() == "alta"
            else "⚠️" if dados["prioridade"].lower() == "média" else "✅"
        )
        st.warning(f"**Prioridade:** {cor_prioridade} {dados['prioridade']}")

    st.subheader("Modelo de Resposta gerada pela LLM")
    st.markdown(
        "Você pode editar o rascunho sugerido pelo modelo ou pedir para ela reescrever."
    )

    # o modelo de resposta sugerida pelo modelo
    resposta_editada = st.text_area(
        "Resposta Final:", value=dados["resposta_sugerida"], height=200
    )

    # ==========================================
    # botoes para validar ou pedir para refazer
    # ==========================================
    col_aprovar, col_refazer = st.columns(2)

    with col_aprovar:
        if st.button("✅ Aprovar e Enviar", type="primary", use_container_width=True):
            with st.spinner("Enviando..."):
                req_validacao = requests.post(
                    f"{API_URL}/validate",
                    json={"resposta_final_aprovada": resposta_editada},
                )
                if req_validacao.status_code == 200:
                    st.success("✅ Resposta aprovada e enviada com sucesso!")
                    st.balloons()
                    st.session_state.analise_atual = None
                else:
                    st.error("Erro ao validar.")

    with col_refazer:
        if st.button("🔄 Refazer Rascunho", type="secondary", use_container_width=True):
            with st.spinner("A LLM está reescrevendo a resposta"):
                req_redraft = requests.post(
                    f"{API_URL}/redraft",
                    json={
                        "comentario": dados["comentario_cliente"],
                        "sentimento": dados["sentimento"],
                        "prioridade": dados["prioridade"],
                    },
                )

                if req_redraft.status_code == 200:
                    # substitui a resposta antiga pela nova no cache da sessão
                    st.session_state.analise_atual["resposta_sugerida"] = (
                        req_redraft.json()["nova_resposta"]
                    )
                    # recarrega a telapara mostrar o novo texto dentro do text_area
                    st.rerun()
                else:
                    st.error("Erro ao tentar refazer o rascunho.")
