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
        st.text_input("Senha:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Acesso Restrito - JEJ")
        st.text_input("Senha:", type="password", on_change=password_entered, key="password")
        st.error("Senha incorreta.")
        return False
    return True

if not check_password():
    st.stop()

# 2. CONFIGURAÇÃO E CONEXÃO
st.set_page_config(page_title="Gestão Financeira JEJ", layout="wide")
url, key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

@st.cache_data(ttl=600)
def load_data():
    try:
        res = supabase.table("fluxo_caixa_ofx").select("*").execute()
        df = pd.DataFrame(res.data)
        if df.empty: return df
        df['data_transacao'] = pd.to_datetime(df['data_transacao'])
        df['valor'] = pd.to_numeric(df['valor'])
        df['ano'] = df['data_transacao'].dt.year
        df['mes_nome'] = df['data_transacao'].dt.month_name()
        return df
    except: return pd.DataFrame()

df_raw = load_data()

# 3. INTERFACE E FILTROS
if df_raw.empty:
    st.warning("⚠️ Sem dados no banco.")
else:
    st.title("📊 Gestão Financeira JEJ")
    c_f1, c_f2 = st.columns(2)
    
    meses_pt = {"January":"Janeiro","February":"Fevereiro","March":"Março","April":"Abril","May":"Maio","June":"Junho","July":"Julho","August":"Agosto","September":"Setembro","October":"Outubro","November":"Novembro","December":"Dezembro"}
    
    with c_f1:
        ano_sel = st.selectbox("Ano", sorted(df_raw['ano'].unique(), reverse=True))
    with c_f2:
        m_disp = df_raw[df_raw['ano']==ano_sel]['mes_nome'].unique()
        lista_m = [meses_pt[m] for m in meses_pt if m in m_disp]
        mes_filt = st.selectbox("Mês", lista_m)

    m_eng = [k for k,v in meses_pt.items() if v==mes_filt][0]
    df = df_raw[(df_raw['ano']==ano_sel) & (df_raw['mes_nome']==m_eng)].copy()

    # --- LÓGICA DE CÁLCULO CORRIGIDA ---
    # Filtra apenas o que não é transferência interna (BB RENDE FÁCIL) se desejar um saldo real de operação
    # Para este código, manteremos a soma simples de tudo que está no banco:
    receitas = df[df['valor'] > 0]['valor'].sum()
    despesas = df[df['valor'] < 0]['valor'].sum()
    saldo_real = receitas + despesas

    # MÉTRICAS
    k1, k2, k3 = st.columns(3)
    k1.metric("Receitas", f"R$ {receitas:,.2f}")
    k2.metric("Despesas", f"R$ {abs(despesas):,.2f}", delta_color="inverse")
    k3.metric("Saldo Líquido", f"R$ {saldo_real:,.2f}", delta=f"{saldo_real:,.2f}")

    st.divider()

    # GRÁFICOS
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("📌 Despesas por Gestão")
        df_g = df[df['valor'] < 0].groupby('gestao')['valor'].sum().abs().reset_index()
        fig1 = px.bar(df_g, x='valor', y='gestao', orientation='h', color_discrete_sequence=['#E74C3C'])
        st.plotly_chart(fig1, use_container_width=True)
    with g2:
        st.subheader("🍩 Despesas por Categoria")
        df_c = df[df['valor'] < 0].groupby('categoria')['valor'].sum().abs().reset_index()
        fig2 = px.pie(df_c, values='valor', names='categoria', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig2, use_container_width=True)
