import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# Configuração da Página
st.set_page_config(page_title="Gestão Financeira JEJ", layout="wide")

# Conexão com Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# Função de carregamento sem cache forçado para teste
def load_data():
    try:
        # Busca os dados
        response = supabase.table("fluxo_caixa_ofx").select("*").execute()
        df = pd.DataFrame(response.data)
        
        if df.empty:
            return df
            
        # Tratamento de datas e tipos
        df['data_transacao'] = pd.to_datetime(df['data_transacao'])
        df['valor'] = pd.to_numeric(df['valor'])
        df['ano'] = df['data_transacao'].dt.year
        df['mes_nome'] = df['data_transacao'].dt.month_name()
        return df
    except Exception as e:
        st.error(f"Erro ao conectar com o banco: {e}")
        return pd.DataFrame()

df_raw = load_data()

if df_raw.empty:
    st.warning("Nenhum dado encontrado na tabela 'fluxo_caixa_ofx'. Verifique se há registros no Supabase.")
else:
    # Filtros
    st.title("📊 Painel Financeiro JEJ")
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        ano_sel = st.selectbox("Selecione o Ano", sorted(df_raw['ano'].unique(), reverse=True))
    
    with col_f2:
        meses_pt = {"January": "Janeiro", "February": "Fevereiro", "March": "Março", "April": "Abril", "May": "Maio", "June": "Junho", "July": "Julho", "August": "Agosto", "September": "Setembro", "October": "Outubro", "November": "Novembro", "December": "Dezembro"}
        lista_meses_disponiveis = [meses_pt[m] for m in df_raw[df_raw['ano'] == ano_sel]['mes_nome'].unique()]
        mes_filt = st.selectbox("Selecione o Mês", lista_meses_disponiveis)

    # Filtragem Final
    mes_eng = [k for k, v in meses_pt.items() if v == mes_filt][0]
    df = df_raw[(df_raw['ano'] == ano_sel) & (df_raw['mes_nome'] == mes_eng)].copy()

    # Cards
    receitas = df[df['valor'] > 0]['valor'].sum()
    despesas = df[df['valor'] < 0]['valor'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Receitas", f"R$ {receitas:,.2f}")
    c2.metric("Total Despesas", f"R$ {abs(despesas):,.2f}")
    c3.metric("Saldo Líquido", f"R$ {(receitas + despesas):,.2f}")

    st.divider()

    # Gráficos
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Por Área de Gestão")
        df_gestao = df[df['valor'] < 0].groupby('gestao')['valor'].sum().abs().reset_index()
        fig_gestao = px.bar(df_gestao, x='valor', y='gestao', orientation='h', color_discrete_sequence=['#2C3E50'])
        st.plotly_chart(fig_gestao, use_container_width=True)

    with g2:
        st.subheader("Por Categoria")
        df_cat = df[df['valor'] < 0].groupby('categoria')['valor'].sum().abs().reset_index()
        fig_cat = px.pie(df_cat, values='valor', names='categoria', hole=0.4)
        st.plotly_chart(fig_cat, use_container_width=True)
