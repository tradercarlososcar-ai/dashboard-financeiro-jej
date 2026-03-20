import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# 1. Configuração da Página e Paleta de Cores
st.set_page_config(page_title="Gestão Financeira JEJ", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #F8F9FA; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# 2. Conexão com Supabase (As credenciais serão configuradas no próximo passo)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

@st.cache_data(ttl=600)
def load_data():
    response = supabase.table("fluxo_caixa_ofx").select("*").execute()
    df = pd.DataFrame(response.data)
    df['data_transacao'] = pd.to_datetime(df['data_transacao'])
    df['ano'] = df['data_transacao'].dt.year
    df['mes'] = df['data_transacao'].dt.month_name()
    return df

df_raw = load_data()

# 3. Cabeçalho e Filtros
st.title("📊 Painel Financeiro JEJ")
col_f1, col_f2 = st.columns(2)
with col_f1:
    ano_sel = st.selectbox("Selecione o Ano", sorted(df_raw['ano'].unique(), reverse=True))
with col_f2:
    meses_pt = {"January": "Janeiro", "February": "Fevereiro", "March": "Março", "April": "Abril", "May": "Maio", "June": "Junho", "July": "Julho", "August": "Agosto", "September": "Setembro", "October": "Outubro", "November": "Novembro", "December": "Dezembro"}
    mes_filt = st.selectbox("Selecione o Mês", list(meses_pt.values()))

# Filtragem dos dados
mes_eng = [k for k, v in meses_pt.items() if v == mes_filt][0]
df = df_raw[(df_raw['ano'] == ano_sel) & (df_raw['mes'] == mes_eng)].copy()

# 4. Cards de Resumo
receitas = df[df['valor'] > 0]['valor'].sum()
despesas = df[df['valor'] < 0]['valor'].sum()
saldo = receitas + despesas

c1, c2, c3 = st.columns(3)
c1.metric("Total Receitas", f"R$ {receitas:,.2f}")
c2.metric("Total Despesas", f"R$ {abs(despesas):,.2f}", delta_color="inverse")
c3.metric("Saldo Líquido", f"R$ {saldo:,.2f}")

st.divider()

# 5. Gráficos
g1, g2 = st.columns(2)

with g1:
    st.subheader("Por Área de Gestão")
    fig_gestao = px.bar(df[df['valor'] < 0].groupby('gestao')['valor'].sum().abs().reset_index(), 
                        x='valor', y='gestao', orientation='h', color_discrete_sequence=['#2C3E50'])
    st.plotly_chart(fig_gestao, use_container_width=True)

with g2:
    st.subheader("Por Categoria")
    fig_cat = px.pie(df[df['valor'] < 0].groupby('categoria')['valor'].sum().abs().reset_index(), 
                     values='valor', names='categoria', hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe)
    st.plotly_chart(fig_cat, use_container_width=True)

# 6. Tabela Detalhada
st.subheader("Extrato Detalhado")
df_view = df[['data_transacao', 'descricao_original', 'categoria', 'gestao', 'valor']].copy()
df_view['data_transacao'] = df_view['data_transacao'].dt.strftime('%d/%m/%Y')
st.dataframe(df_view, use_container_width=True)
