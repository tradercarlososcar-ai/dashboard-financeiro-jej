import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
 
# 1. CONFIGURAÇÕES DE PÁGINA E CONEXÃO
st.set_page_config(page_title="Gestão Financeira J&J", layout="wide", initial_sidebar_state="expanded")

# --- CSS CUSTOMIZADO PARA CORES DOS BOTÕES (VERMELHO E CINZA) ---
st.markdown("""
    <style>
    /* Padronização dos Títulos dos Cards */
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
    
    /* Customização das Pills (Botões da Sidebar) */
    /* Estágio Selecionado: Vermelho J&J */
    div[data-testid="stBaseButton-pillsActive"] {
        background-color: #FF4B4B !important;
        color: white !important;
        border: 1px solid #FF4B4B !important;
    }
    
    /* Estágio Não Selecionado: Cinza Suave */
    div[data-testid="stBaseButton-pills"] {
        background-color: #F0F2F6 !important;
        color: #31333F !important;
        border: 1px solid #DDE1E7 !important;
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
 
# 2. MOTOR DE DADOS COM CACHE (MANTENDO TRADUÇÃO)
@st.cache_data(ttl=60)
def load_data():
    try:
        res = supabase.table("fluxo_caixa_ofx").select("*").execute()
        df = pd.DataFrame(res.data)
        if df.empty: return df
            
        df['data_transacao_dt'] = pd.to_datetime(df['data_transacao'], errors='coerce')
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0)
        df['ano'] = df['data_transacao_dt'].dt.year.fillna(0).astype(int)
        
        meses_map = {
            'January': 'Janeiro', 'February': 'Fevereiro', 'March': 'Março', 
            'April': 'Abril', 'May': 'Maio', 'June': 'Junho', 
            'July': 'Julho', 'August': 'Agosto', 'September': 'Setembro', 
            'October': 'Outubro', 'November': 'Novembro', 'December': 'Dezembro'
        }
        df['mes_nome'] = df['data_transacao_dt'].dt.month_name().map(meses_map)
        if 'classificacao' not in df.columns: df['classificacao'] = None
        return df
    except Exception as e:
        st.error(f"Erro na conexão: {e}")
        return pd.DataFrame()
 
df_raw = load_data()
 
# 3. BARRA LATERAL REFORMULADA (LÓGICA "TODOS")
st.sidebar.title("Filtros de Navegação")
 
if not df_raw.empty:
    # Filtro de Ano
    anos = sorted(df_raw['ano'].unique(), reverse=True)
    st.sidebar.write("**Ano de Referência**")
    ano_sel = st.sidebar.pills("Ano", anos, selection_mode="single", default=anos[0], label_visibility="collapsed")
    
    # Filtro de Meses com Opção "Todos"
    meses_ordem = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    meses_existentes = [m for m in meses_ordem if m in df_raw[df_raw['ano'] == ano_sel]['mes_nome'].unique()]
    
    # Inclusão da opção "Todos"
    opcoes_meses = ["Todos"] + meses_existentes
    
    st.sidebar.write("**Meses**")
    mes_sel_bruto = st.sidebar.pills("Meses", opcoes_meses, selection_mode="multi", default=["Todos"], label_visibility="collapsed")

    # Lógica de seleção inteligente
    if "Todos" in mes_sel_bruto or not mes_sel_bruto:
        mes_final = meses_existentes
    else:
        mes_final = mes_sel_bruto

    # Filtro de Classificação
    st.sidebar.write("**Tipo de Transação**")
    tipos_no_banco = [t for t in df_raw['classificacao'].unique().tolist() if t is not None]
    if not tipos_no_banco: tipos_no_banco = ["Receita", "Despesa"]
    tipo_sel = st.sidebar.pills("Tipo", tipos_no_banco, selection_mode="multi", default=tipos_no_banco, label_visibility="collapsed")
    
    # Filtro Final
    mask = (df_raw['ano'] == ano_sel) & (df_raw['mes_nome'].isin(mes_final))
    if any(df_raw['classificacao'].notnull()):
        mask = mask & (df_raw['classificacao'].isin(tipo_sel))
    df = df_raw[mask]
else:
    df = df_raw
    st.sidebar.warning("Nenhum dado encontrado.")
 
# 4. TÍTULO E ABAS (MANTENDO O QUE ESTÁ FUNCIONANDO)
st.title("📊 Painel de Gestão Financeira")
st.markdown("#### **J&J PERFURAÇÕES MND**")
st.divider()
 
aba1, aba2 = st.tabs(["📈 Dashboard Executivo", "📂 Gestão de Dados"])
 
with aba1:
    if not df.empty:
        # KPIs (Receita/Despesa/Saldo) - Inalterado para manter precisão
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
 
        # Grid de Gestão (Cards Semafóricos baseados no PDF)
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
                    color = "#FF4B4B" if pct > 40 else "#FFAA00" if pct > 15 else "#FFE000" if pct > 5 else "#00CC96"
                    with slot:
                        with st.container(border=True):
                            st.markdown(f'<div class="card-title">{nome}</div>', unsafe_allow_html=True)
                            st.metric(label=f"{pct:.1f}% do total", value=f"R$ {valor:,.2f}")
                            st.markdown(f'''<div style="background-color:#e0e0e0;border-radius:10px;height:6px;width:100%;"><div style="background-color:{color};height:8px;width:{pct}%;border-radius:10px;"></div></div>''', unsafe_allow_html=True)
                else: slot.empty()
        st.divider()
 
        # Gráfico Top Categorias
        st.write("### 🏷️ Despesas por Categorias (Top 10)")
        top_categorias = df_gastos.groupby('categoria')['valor_abs'].sum().nlargest(10).reset_index()
        if not top_categorias.empty:
            fig = px.bar(top_categorias, x='valor_abs', y='categoria', orientation='h', color='valor_abs', color_continuous_scale='Reds', text_auto=',.2f')
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False, height=450)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nenhum dado para os filtros selecionados.")
 
with aba2:
    st.data_editor(df_raw, use_container_width=True, num_rows="dynamic")
