import streamlit as st
import pandas as pd
from supabase import create_client

# 1. Configuração de conexão (Pega das 'Secrets' do Streamlit)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 2. Função de carregamento com Cache
@st.cache_data(ttl=60)
def load_data():
    try:
        # Busca os dados no banco
        res = supabase.table("fluxo_caixa_ofx").select("*").execute()
        df = pd.DataFrame(res.data)
        
        if df.empty:
            return df
            
        # Garante que as colunas essenciais existam
        cols_obrigatorias = ['data_transacao', 'valor', 'descricao_original', 'gestao', 'categoria']
        for col in cols_obrigatorias:
            if col not in df.columns:
                df[col] = None

        # Tratamento de tipos e criação de colunas de tempo
        df['data_transacao_dt'] = pd.to_datetime(df['data_transacao'], errors='coerce')
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0)
        df['ano'] = df['data_transacao_dt'].dt.year.fillna(0).astype(int)
        df['mes_nome'] = df['data_transacao_dt'].dt.month_name().fillna("Sem Data")
        
        return df
    except Exception as e:
        st.error(f"Erro técnico ao carregar dados: {e}")
        return pd.DataFrame()

# 3. Interface do Dashboard
st.set_page_config(page_title="Dashboard Financeiro", layout="wide")
st.title("📊 Gestão Financeira - Fluxo de Caixa")

# Chama a função para carregar os dados
df = load_data()

if not df.empty:
    st.write(f"Conexão bem-sucedida! {len(df)} transações encontradas.")
    # Aqui abaixo seguiria o restante do seu código de gráficos (st.plotly_chart, etc)
    st.dataframe(df.head()) # Mostra uma prévia dos dados para confirmar
else:
    st.warning("O banco de dados parece estar vazio ou não retornou dados.")
