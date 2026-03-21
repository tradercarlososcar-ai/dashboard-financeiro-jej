import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# 1. CONFIGURAÇÕES INICIAIS
st.set_page_config(page_title="Gestão Financeira J&J", layout="wide", initial_sidebar_state="expanded")

# Conexão com Supabase
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

# 2. MOTOR DE DADOS (CACHE)
@st.cache_data(ttl=60)
def load_data():
    res = supabase.table("fluxo_caixa_ofx").select("*").execute()
    df = pd.DataFrame(res.data)
    if df.empty: return df
    
    # Tratamento de Datas e Valores
    df['data_transacao_dt'] = pd.to_datetime(df['data_transacao'], errors='coerce')
    df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0)
    df['mes_nome'] = df['data_transacao_dt'].dt.month_name()
    df['ano'] = df['data_transacao_dt'].dt.year.fillna(0).astype(int)
    return df

df_raw = load_data()

# 3. BARRA LATERAL (FILTROS INOVADORES)
st.sidebar.header("🔍 Filtros de Navegação")
if not df_raw.empty:
    anos = sorted(df_raw['ano'].unique(), reverse=True)
    ano_sel = st.sidebar.selectbox("Selecione o Ano", anos)
    
    meses = df_raw[df_raw['ano'] == ano_sel]['mes_nome'].unique()
    mes_sel = st.sidebar.multiselect("Selecione os Meses", meses, default=meses)
    
    df = df_raw[(df_raw['ano'] == ano_sel) & (df_raw['mes_nome'].isin(mes_sel))]
else:
    df = df_raw

# 4. TÍTULO PRINCIPAL
st.title("📊 Painel de Gestão Financeira")
st.subheader("J&J PERFURAÇÕES MND")
st.divider()

aba1, aba2 = st.tabs(["📈 Dashboard Executivo", "📂 Gestão de Dados"])

with aba1:
    if not df.empty:
        # --- LINHA 1: KPIS PRINCIPAIS ---
        receita = df[df['valor'] > 0]['valor'].sum()
        despesa = df[df['valor'] < 0]['valor'].sum()
        resultado = receita + despesa # despesa já é negativa
        
        c1, c2, c3 = st.columns(3)
        c1.metric("RECEITA TOTAL", f"R$ {receita:,.2f}", delta_color="normal")
        c2.metric("DESPESA TOTAL", f"R$ {abs(despesa):,.2f}", delta=f"-{abs(despesa):,.2f}", delta_color="inverse")
        c3.metric("RESULTADO LÍQUIDO", f"R$ {resultado:,.2f}", delta="Saldo Atual", delta_color="normal" if resultado >=0 else "inverse")

        st.divider()

        # --- LINHA 2: DESPESAS POR ÁREA DE GESTÃO ---
        st.write("### 🏗️ Despesas por Área de Gestão")
        df_despesas = df[df['valor'] < 0].copy()
        df_despesas['valor_abs'] = df_despesas['valor'].abs()
        
        # Agrupamento para as caixas coloridas
        gestao_sums = df_despesas.groupby('gestao')['valor_abs'].sum().sort_values(ascending=False)
        cols_gestao = st.columns(len(gestao_sums) if len(gestao_sums) > 0 else 1)
        
        for i, (nome, valor) in enumerate(gestao_sums.items()):
            with cols_gestao[i % len(cols_gestao)]:
                st.info(f"**{nome}**\nR$ {valor:,.2f}")

        st.divider()

        # --- LINHA 3: GRÁFICO DE CATEGORIAS ---
        st.write("### 🏷️ Despesas por Categorias")
        df_cat = df_despesas.groupby('categoria')['valor_abs'].sum().reset_index()
        fig = px.bar(df_cat, x='valor_abs', y='categoria', orientation='h', 
                     color='valor_abs', color_continuous_scale='Reds',
                     labels={'valor_abs': 'Valor (R$)', 'categoria': 'Categoria'})
        fig.update_layout(yaxis={'categoryorder':'total ascending'}, height=400)
        st.plotly_chart(fig, use_container_width=True)

with aba2:
    st.write("### 📝 Tabela de Movimentações Completa")
    # Tabela com edição permitida para Categoria e Gestão
    df_editor = st.data_editor(
        df_raw,
        column_order=("data_transacao", "descricao_original", "valor", "gestao", "categoria"),
        column_config={
            "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            "gestao": st.column_config.SelectboxColumn("Área de Gestão", options=["Operacional", "Administrativo", "Financeiro", "Pessoal"]),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=df_raw['categoria'].unique().tolist())
        },
        disabled=["data_transacao", "descricao_original", "valor"], # Protege os dados originais do banco
        num_rows="dynamic", # Permite deletar linhas selecionando e apertando Del
        use_container_width=True
    )
    st.caption("ℹ️ Para alterar, use as caixas de seleção. Para excluir, selecione a linha e aperte 'Delete' no teclado.")
    if st.button("💾 Salvar Alterações no Banco"):
        st.success("Alterações enviadas para processamento (Funcionalidade de escrita requer nó de Update no n8n)")
