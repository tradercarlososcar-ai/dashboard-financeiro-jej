import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
 
# 1. CONFIGURAÇÕES DE PÁGINA E CONEXÃO
st.set_page_config(page_title="Gestão Financeira J&J", layout="wide", initial_sidebar_state="expanded")

# --- ESTILIZAÇÃO CSS PARA PADRONIZAR OS CARDS ---
st.markdown("""
    <style>
    /* Reduz a fonte do título do card e fixa a altura para evitar desalinhamento */
    .card-title {
        font-size: 11px !important;
        font-weight: bold;
        height: 35px;
        display: flex;
        align-items: center;
        line-height: 1.2;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    /* Padroniza o container do metric */
    [data-testid="stMetricValue"] {
        font-size: 1.4rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
    }
    </style>
    """, unsafe_allow_html=True)
 
# Inicialização do Supabase
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
            
        df['data_transacao_dt'] = pd.to_datetime(df['data_transacao'], errors='coerce')
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0)
        df['ano'] = df['data_transacao_dt'].dt.year.fillna(0).astype(int)
        df['mes_nome'] = df['data_transacao_dt'].dt.month_name()
        
        if 'classificacao' not in df.columns:
            df['classificacao'] = None
            
        return df
    except Exception as e:
        st.error(f"Erro na conexão com o banco: {e}")
        return pd.DataFrame()
 
df_raw = load_data()
 
# 3. BARRA LATERAL E FILTROS
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/5571/5571404.png", width=100)
st.sidebar.title("Filtros")
 
if not df_raw.empty:
    anos = sorted(df_raw['ano'].unique(), reverse=True)
    ano_sel = st.sidebar.selectbox("Ano de Referência", anos)
    
    meses_disponiveis = df_raw[df_raw['ano'] == ano_sel]['mes_nome'].unique()
    mes_sel = st.sidebar.multiselect("Meses", meses_disponiveis, default=meses_disponiveis)

    tipos_no_banco = df_raw['classificacao'].unique().tolist()
    tipos_filtros = [t for t in tipos_no_banco if t is not None]
    if not tipos_filtros: tipos_filtros = ["Receita", "Despesa"]
        
    tipo_sel = st.sidebar.multiselect("Tipo de Transação", tipos_filtros, default=tipos_filtros)
    
    mask = (df_raw['ano'] == ano_sel) & (df_raw['mes_nome'].isin(mes_sel))
    if any(df_raw['classificacao'].notnull()):
        mask = mask & (df_raw['classificacao'].isin(tipo_sel))
        
    df = df_raw[mask]
else:
    df = df_raw
    st.sidebar.warning("Nenhum dado encontrado.")
 
# 4. TÍTULO PRINCIPAL
st.title("📊 Painel de Gestão Financeira")
st.markdown("#### **J&J PERFURAÇÕES MND**")
st.divider()
 
aba1, aba2 = st.tabs(["📈 Dashboard Executivo", "📂 Gestão de Dados"])
 
with aba1:
    if not df.empty:
        # --- LINHA 1: KPIS ---
        if 'classificacao' in df.columns and df['classificacao'].notnull().any():
            receitas = df[df['classificacao'] == 'Receita']['valor'].sum()
            despesas = df[df['classificacao'] == 'Despesa']['valor'].sum()
        else:
            receitas = df[df['valor'] > 0]['valor'].sum()
            despesas = df[df['valor'] < 0]['valor'].sum()
            
        saldo = receitas + despesas
        
        c1, c2, c3 = st.columns(3)
        c1.metric("RECEITA TOTAL", f"R$ {receitas:,.2f}")
        c2.metric("DESPESA TOTAL", f"R$ {abs(despesas):,.2f}", delta=f"-{abs(despesas):,.2f}", delta_color="inverse")
        c3.metric("RESULTADO LÍQUIDO", f"R$ {saldo:,.2f}", delta="Saldo no Período", delta_color="normal" if saldo >= 0 else "inverse")
        
        st.divider()
 
        # --- LINHA 2: GRID DE GESTÃO (COM CSS PADRONIZADO) ---
        st.write("### 🏗️ Despesas por Gestão")
        
        df_gastos = df[df['valor'] < 0].copy()
        df_gastos['valor_abs'] = df_gastos['valor'].abs()
        resumo_gestao = df_gastos.groupby('gestao')['valor_abs'].sum().sort_values(ascending=False)
        total_periodo = df_gastos['valor_abs'].sum()
 
        if not resumo_gestao.empty:
            rows = [st.columns(4), st.columns(4)]
            todos_slots = rows[0] + rows[1]
            
            for i, slot in enumerate(todos_slots):
                if i < len(resumo_gestao):
                    nome, valor = resumo_gestao.index[i], resumo_gestao.values[i]
                    pct = (valor / total_periodo) * 100 if total_periodo > 0 else 0
                    
                    # Cores baseadas nas Regras do PDF [cite: 2, 3, 5, 7]
                    if pct > 40: color = "#FF4B4B"
                    elif pct > 15: color = "#FFAA00"
                    elif pct > 5: color = "#FFE000"
                    else: color = "#00CC96"
                    
                    with slot:
                        with st.container(border=True):
                            # Título com classe CSS customizada para manter o tamanho igual
                            st.markdown(f'<div class="card-title">{nome}</div>', unsafe_allow_html=True)
                            st.metric(label=f"{pct:.1f}% do total", value=f"R$ {valor:,.2f}")
                            st.markdown(f'''<div style="background-color:#e0e0e0;border-radius:10px;height:6px;width:100%;"><div style="background-color:{color};height:8px;width:{pct}%;border-radius:10px;"></div></div>''', unsafe_allow_html=True)
                else:
                    slot.empty()
 
        st.divider()
 
        # --- LINHA 3: GRÁFICO ---
        st.write("### 🏷️ Despesas por Categorias (Top 10)")
        top_categorias = df_gastos.groupby('categoria')['valor_abs'].sum().nlargest(10).reset_index()
        if not top_categorias.empty:
            fig = px.bar(top_categorias, x='valor_abs', y='categoria', orientation='h', color='valor_abs', color_continuous_scale='Reds', text_auto=',.2f')
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, height=450)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aguardando seleção de filtros...")
 
with aba2:
    st.write("### 📝 Tabela de Movimentações")
    if not df_raw.empty:
        st.data_editor(
            df_raw,
            column_order=("data_transacao", "descricao_original", "valor", "classificacao", "gestao", "categoria"),
            column_config={
                "data_transacao": "Data",
                "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
                "classificacao": st.column_config.SelectboxColumn("Tipo", options=["Receita", "Despesa"]),
                "gestao": st.column_config.SelectboxColumn("Gestão", options=["Gestão de Financiamentos", "Gestão de Operacional", "Gestão de Pessoas", "Infraestrutura e Governança", "Classificar"]),
                "categoria": "Categoria"
            },
            disabled=["data_transacao", "valor", "descricao_original"],
            use_container_width=True,
            num_rows="dynamic"
        )
        st.button("💾 Sincronizar Alterações")
