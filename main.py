import streamlit as st
@st.cache_data(ttl=60)
def sua_funcao_aqui():
@st.cache_data(ttl=60)
def load_data():
    try:
        res = supabase.table("fluxo_caixa_ofx").select("*").execute()
        df = pd.DataFrame(res.data)
        if df.empty: return df
        
        # Garante que as colunas existam antes de manipular
        for col in ['data_transacao', 'valor', 'descricao_original', 'gestao', 'categoria']:
            if col not in df.columns: df[col] = None

        df['data_transacao_dt'] = pd.to_datetime(df['data_transacao'], errors='coerce')
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0)
        df['ano'] = df['data_transacao_dt'].dt.year.fillna(0).astype(int)
        df['mes_nome'] = df['data_transacao_dt'].dt.month_name().fillna("Sem Data")
        
        return df
    except Exception as e:
        st.error(f"Erro ao carregar: {e}")
        return pd.DataFrame()
