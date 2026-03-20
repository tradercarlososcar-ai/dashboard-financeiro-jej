import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# 1. SEGURANÇA (LOGIN)
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.title("🔒 Acesso Restrito - JEJ")
        st.text_input("Digite a senha de acesso:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Digite a senha de acesso:", type="password", on_change=password_entered, key="password")
        st.error("😕 Senha incorreta.")
        return False
    return True

if not check_password():
    st.stop()

# 2. CONFIGURAÇÃO VISUAL E ESTILO (CAIXAS DISCRETAS)
st.set_page_config(page_title="Gestão Financeira JEJ", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #eeeeee;
        padding: 15px;
        border-radius: 8px;
    }
    .chart-container {
        border: 1px solid #eeeeee;
        padding: 20px;
        border-radius: 8px;
        background-color: #ffffff;
        margin-bottom: 20px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXÃO COM O SUPABASE
url, key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

@st.cache_data(ttl=300)
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

# 4. REGRAS DE NEGÓCIO (POWER QUERY LOGIC)
if df_raw.empty:
    st.warning("⚠️ O banco de dados está vazio.")
else:
    # FILTRO: Remover "RENDE FÁCIL" conforme lógica de conciliação do seu Excel
    df_clean = df_raw[~df_raw['descricao_original'].str.contains('RENDE FÁCIL|RENDE FACIL', case=False, na=False)].copy()

    st.title("📊 Painel Gestão Financeira JEJ")
    
    # Filtros na Barra Lateral (Sidebar) para limpar a tela principal
    with st.sidebar:
        st.header("Configurações de Filtro")
        ano_sel = st.selectbox("Selecione o Ano", sorted(df_clean['ano'].unique(), reverse=True))
        
        meses_pt = {"January":"Janeiro","February":"Fevereiro","March":"Março","April":"Abril","May":"Maio","June":"Junho","July":"Julho","August":"Agosto","September":"Setembro","October":"Outubro","November":"Novembro","December":"Dezembro"}
        m_disp = df_clean[df_clean['ano']==ano_sel]['mes_nome'].unique()
        lista_m = [meses_pt[m] for m in meses_pt if m in m_disp]
        
        mes_filt = st.selectbox("Selecione o Mês", lista_m)

    m_eng = [k for k,v in meses_pt.items() if v==mes_filt][0]
    df = df_clean[(df_clean['ano']==ano_sel) & (df_clean['mes_nome']==m_eng)].copy()

    # MÉTRICAS TIPO "CARD"
    rec = df[df['valor'] > 0]['valor'].sum()
    desp = df[df['valor'] < 0]['valor'].sum()
    saldo = rec + desp

    c1, c2, c3 = st.columns(3)
    c1.metric("Receitas Reais", f"R$ {rec:,.2f}")
    c2.metric("Despesas Reais", f"R$ {abs(desp):,.2f}")
    c3.metric("Saldo Líquido", f"R$ {saldo:,.2f}", delta=f"R$ {saldo:,.2f}")

    st.divider()

    # 5. GRÁFICOS EM CAIXAS INDIVIDUAIS (BARRAS HORIZONTAIS)
    col1, col2 = st.columns(2)

    # Cores discretas (Azul Marinho / Cinza Ardósia)
    palette = ["#334155", "#475569", "#64748b", "#94a3b8"]

    with col1:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("📌 Despesas por Gestão")
        df_g = df[df['valor'] < 0].groupby('gestao')['valor'].sum().abs().reset_index().sort_values('valor')
        fig1 = px.bar(df_g, x='valor', y='gestao', orientation='h', height=320, color_discrete_sequence=[palette[0]])
        fig1.update_layout(margin=dict(l=0, r=10, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("🏷️ Despesas por Categoria")
        df_c = df[df['valor'] < 0].groupby('categoria')['valor'].sum().abs().reset_index().sort_values('valor')
        fig2 = px.bar(df_c, x='valor', y='categoria', orientation='h', height=320, color_discrete_sequence=[palette[2]])
        fig2.update_layout(margin=dict(l=0, r=10, t=10, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 6. TABELA DETALHADA DISCRETA
    st.divider()
    with st.expander("🔍 Ver Extrato Detalhado do Mês"):
        df_detalhe = df[['data_transacao', 'descricao_original', 'categoria', 'valor']].copy()
        df_detalhe['data_transacao'] = df_detalhe['data_transacao'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_detalhe.sort_values('data_transacao'), use_container_width=True)
