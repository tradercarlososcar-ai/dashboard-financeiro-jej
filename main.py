import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# 1. CONFIGURAÇÕES DE PÁGINA E CONEXÃO
st.set_page_config(page_title="Gestão Financeira J&J", layout="wide", initial_sidebar_state="expanded")

# Inicialização do Supabase através das Secrets do Streamlit
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error(f"Erro ao carregar credenciais do Supabase: {e}")
    st.stop()

# 2. MOTOR DE DADOS COM CACHE
@st.cache_data(ttl=60)
def load_data():
    try:
        res = supabase.table("fluxo_caixa_ofx").select("*").execute()
        df = pd.DataFrame(res.data)
        
        if df.empty:
            return df
            
        # Tratamento de tipos de dados
        df['data_transacao_dt'] = pd.to_datetime(df['data_transacao'], errors='coerce')
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0)
        
        # Colunas de apoio para filtros
        df['ano'] = df['data_transacao_dt'].dt.year.fillna(0).astype(int)
        df['mes_nome'] = df['data_transacao_dt'].dt.month_name()
        
        return df
    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()

# Carga inicial
df_raw = load_data()

# 3. BARRA LATERAL E FILTROS
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/5571/5571404.png", width=100)
st.sidebar.title("Filtros")

if not df_raw.empty:
    anos = sorted(df_raw['ano'].unique(), reverse=True)
    ano_sel = st.sidebar.selectbox("Ano de Referência", anos)
    
    meses_disponiveis = df_raw[df_raw['ano'] == ano_sel]['mes_nome'].unique()
    mes_sel = st.sidebar.multiselect("Meses", meses_disponiveis, default=meses_disponiveis)
    
    # DataFrame Filtrado para o Dashboard
    df = df_raw[(df_raw['ano'] == ano_sel) & (df_raw['mes_nome'].isin(mes_sel))]
else:
    df = df_raw
    st.sidebar.warning("Nenhum dado encontrado no banco.")

# 4. TÍTULO PRINCIPAL
st.title("📊 Painel de Gestão Financeira")
st.markdown("#### **J&J PERFURAÇÕES MND**")
st.divider()

# DEFINIÇÃO DAS ABAS
aba1, aba2 = st.tabs(["📈 Dashboard Executivo", "📂 Gestão de Dados"])

with aba1:
    if not df.empty:
        # --- LINHA 1: KPIS DE ALTO NÍVEL ---
        receitas = df[df['valor'] > 0]['valor'].sum()
        despesas = df[df['valor'] < 0]['valor'].sum()
        saldo = receitas + despesas
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("RECEITA TOTAL", f"R$ {receitas:,.2f}")
        with c2:
            st.metric("DESPESA TOTAL", f"R$ {abs(despesas):,.2f}", delta=f"-{abs(despesas):,.2f}", delta_color="inverse")
        with c3:
            st.metric("RESULTADO LÍQUIDO", f"R$ {saldo:,.2f}", delta="Saldo no Período", delta_color="normal" if saldo >= 0 else "inverse")
        
        st.divider()

        # --- LINHA 2: MELHORIA SIGNIFICATIVA - ÁREAS DE GESTÃO ---
        st.write("### 🏗️ Despesas por Área de Gestão")
        
        df_gastos = df[df['valor'] < 0].copy()
        df_gastos['valor_abs'] = df_gastos['valor'].abs()
        resumo_gestao = df_gastos.groupby('gestao')['valor_abs'].sum().sort_values(ascending=False)
        total_periodo = df_gastos['valor_abs'].sum()

        if not resumo_gestao.empty:
            colunas = st.columns(len(resumo_gestao))
            for i, (nome, valor) in enumerate(resumo_gestao.items()):
                with colunas[i]:
                    pct = (valor / total_periodo) * 100
                    
                    # Lógica de Cor Inovadora (Semafórica)
                    if pct > 50: color = "#FF4B4B" # Vermelho (Crítico)
                    elif pct > 20: color = "#FFAA00" # Laranja (Atenção)
                    else: color = "#00CC96" # Verde (Controlado)
                    
                    with st.container(border=True):
                        st.markdown(f"**{nome.upper()}**")
                        st.metric(label=f"{pct:.1f}% do total", value=f"R$ {valor:,.2f}")
                        # Barra de progresso customizada em HTML/CSS
                        st.markdown(f'''
                            <div style="background-color: #e0e0e0; border-radius: 10px; height: 8px; width: 100%;">
                                <div style="background-color: {color}; height: 8px; width: {pct}%; border-radius: 10px;"></div>
                            </div>
                        ''', unsafe_allow_html=True)
                        st.caption("Participação nos gastos")
        
        st.divider()

        # --- LINHA 3: GRÁFICO DE CATEGORIAS ---
        st.write("### 🏷️ Despesas por Categorias (Top 10)")
        top_categorias = df_gastos.groupby('categoria')['valor_abs'].sum().nlargest(10).reset_index()
        
        fig = px.bar(
            top_categorias, 
            x='valor_abs', 
            y='categoria', 
            orientation='h',
            color='valor_abs',
            color_continuous_scale='Reds',
            text_auto=',.2f'
        )
        fig.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, height=450)
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Selecione um período nos filtros laterais para visualizar o dashboard.")

with aba2:
    st.write("### 📝 Tabela de Movimentações")
    if not df_raw.empty:
        # Editor de dados interativo
        st.data_editor(
            df_raw,
            column_order=("data_transacao", "descricao_original", "valor", "gestao", "categoria"),
            column_config={
                "data_transacao": "Data",
                "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
                "gestao": st.column_config.SelectboxColumn("Área", options=["Operacional", "Administrativo", "Pessoal", "Financeiro"]),
                "categoria": "Categoria"
            },
            disabled=["data_transacao", "valor", "descricao_original"],
            use_container_width=True,
            num_rows="dynamic"
        )
        st.button("💾 Sincronizar Alterações")
    else:
        st.warning("Sem dados para exibir na tabela.")
