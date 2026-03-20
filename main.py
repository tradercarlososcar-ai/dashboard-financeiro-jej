import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# 1. SISTEMA DE SEGURANÇA (SENHA)
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Acesso Restrito - JEJ")
        st.text_input("Digite a senha de acesso para visualizar o painel:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Acesso Restrito - JEJ")
        st.text_input("Digite a senha de acesso para visualizar o painel:", type="password", on_change=password_entered, key="password")
        st.error("😕 Senha incorreta. Tente novamente.")
        return False
    else:
        return True

if not check_password():
    st.stop() # Interrompe o carregamento se a senha estiver errada

# 2. CONFIGURAÇÃO VISUAL DO PAINEL
st.set_page_config(page_title="Gestão Financeira JEJ", layout="wide")

# Estilo para os Cards (Métricas)
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; font-weight: bold; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #e1e4e8; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXÃO COM O SUPABASE
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

@st.cache_data(ttl=600) # Atualiza os dados a cada 10 minutos
def load_data():
    try:
        response = supabase.table("fluxo_caixa_ofx").select("*").execute()
        df = pd.DataFrame(response.data)
        if df.empty:
            return df
        
        # Converte tipos e datas
        df['data_transacao'] = pd.to_datetime(df['data_transacao'])
        df['valor'] = pd.to_numeric(df['valor'])
        df['ano'] = df['data_transacao'].dt.year
        df['mes_nome'] = df['data_transacao'].dt.month_name()
        return df
    except Exception as e:
        st.error(f"Erro ao carregar dados do banco: {e}")
        return pd.DataFrame()

df_raw = load_data()

# 4. INTERFACE E FILTROS
if df_raw.empty:
    st.warning("⚠️ O banco de dados está vazio ou inacessível.")
else:
    st.title("📊 Painel Gestão Financeira JEJ")
    
    # Linha de Filtros (Ano e Mês)
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        ano_sel = st.selectbox("Selecione o Ano", sorted(df_raw['ano'].unique(), reverse=True))
    
    with col_f2:
        # Dicionário para tradução dos meses
        meses_pt = {"January": "Janeiro", "February": "Fevereiro", "March": "Março", "April": "Abril", "May": "Maio", "June": "Junho", "July": "Julho", "August": "Agosto", "September": "Setembro", "October": "Outubro", "November": "Novembro", "December": "Dezembro"}
        
        # Filtra meses que possuem dados para o ano selecionado
        meses_disponiveis_eng = df_raw[df_raw['ano'] == ano_sel]['mes_nome'].unique()
        lista_meses_exibir = [meses_pt[m] for m in meses_pt if m in meses_disponiveis_eng]
        
        mes_filt = st.selectbox("Selecione o Mês", lista_meses_exibir)

    # Filtragem Final dos Dados conforme seleção do usuário
    mes_eng_final = [k for k, v in meses_pt.items() if v == mes_filt][0]
    df_mes = df_raw[(df_raw['ano'] == ano_sel) & (df_raw['mes_nome'] == mes_eng_final)].copy()

    # 5. CARDS DE RESULTADOS (MÉTRICAS)
    receitas = df_mes[df_mes['valor'] > 0]['valor'].sum()
    despesas = df_mes[df_mes['valor'] < 0]['valor'].sum()
    saldo = receitas + despesas

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Receitas", f"R$ {receitas:,.2f}")
    c2.metric("Total Despesas", f"R$ {abs(despesas):,.2f}")
    c3.metric("Saldo Líquido", f"R$ {saldo:,.2f}", delta=f"{saldo:,.2f}")

    st.divider()

    # 6. GRÁFICOS INTERATIVOS
    g1, g2 = st.columns(2)

    with g1:
        st.subheader("📌 Por Área de Gestão")
        # Agrupa apenas despesas para o gráfico de gestão
        df_gestao = df_mes[df_mes['valor'] < 0].groupby('gestao')['valor'].sum().abs().reset_index()
        fig_gestao = px.bar(df_gestao.sort_values('
