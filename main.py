import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# 1. SEGURANÇA
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["PASSWORD"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.title("🔒 Login - JEJ")
        st.text_input("Senha:", type="password", on_change=password_entered, key="password")
        return False
    return True

if not check_password(): st.stop()

# 2. CONFIGURAÇÃO E CSS "BLINDADO" (PARA FORÇAR AS CORES)
st.set_page_config(page_title="Gestão JEJ", layout="wide")

st.markdown("""
    <style>
    /* Estilo para Subtítulos */
    .section-title {
        font-size: 22px; font-weight: bold; color: #1E1E1E;
        margin-top: 30px; margin-bottom: 15px;
        border-left: 6px solid #333; padding-left: 12px;
    }

    /* FORÇAR CORES NAS CAIXAS - SELETORES DE ALTA PRIORIDADE */
    
    /* BLOCO 1: RECEITA, DESPESA, SALDO */
    div[data-testid="stHorizontalBlock"]:nth-of-type(1) div[data-testid="stMetric"] {
        border-radius: 15px !important;
        padding: 20px !important;
    }
    /* Receita - Azul */
    div[data-testid="column"]:nth-of-type(1) div[data-testid="stMetric"] {
        background-color: #E3F2FD !important; border: 2px solid #2196F3 !important;
    }
    /* Despesa - Vermelho */
    div[data-testid="column"]:nth-of-type(2) div[data-testid="stMetric"] {
        background-color: #FFEBEE !important; border: 2px solid #EF5350 !important;
    }
    /* Saldo - Verde Musgo */
    div[data-testid="column"]:nth-of-type(3) div[data-testid="stMetric"] {
        background-color: #F1F8E9 !important; border: 2px solid #689F38 !important;
    }

    /* BLOCO 2: GESTÃO (Amarelo Creme) */
    /* Seleciona colunas a partir da quarta (início da segunda linha de métricas) */
    div[data-testid="stHorizontalBlock"]:nth-of-type(2) div[data-testid="stMetric"] {
        background-color: #FFFDE7 !important;
        border: 2px solid #FBC02D !important;
        border-radius: 15px !important;
        padding: 15px !important;
    }

    /* Títulos e Valores dentro das caixas */
    [data-testid="stMetricLabel"] p { color: #333 !important; font-weight: bold !important; font-size: 16px !important; }
    [data-testid="stMetricValue"] div { color: #000 !important; font-weight: 800 !important; }

    .chart-box { border: 1px solid #eeeeee; padding: 20px; border-radius: 12px; background-color: #ffffff; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXÃO
url, key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

@st.cache_data(ttl=60)
def load_data():
    res = supabase.table("fluxo_caixa_ofx").select("*").execute()
    df = pd.DataFrame(res.data)
    if df.empty: return df
    df['data_transacao'] = pd.to_datetime(df['data_transacao'])
    df['valor'] = pd.to_numeric(df['valor'])
    df['ano'] = df['data_transacao'].dt.year
    df['mes_nome'] = df['data_transacao'].dt.month_name()
    return df

df_raw = load_data()

# 4. INTERFACE
st.title("📊 Painel de Gestão Financeira - JEJ")
tab1, tab2 = st.tabs(["📈 Dashboard", "🛠️ Editor"])

meses_pt = {"January":"Janeiro","February":"Fevereiro","March":"Março","April":"Abril","May":"Maio","June":"Junho","July":"Julho","August":"Agosto","September":"Setembro","October":"Outubro","November":"Novembro","December":"Dezembro"}

with tab1:
    df_clean = df_raw[~df_raw['descricao_original'].str.contains('RENDE FÁCIL|RENDE FACIL', case=False, na=False)].copy()
    
    if not df_clean.empty:
        with st.sidebar:
            st.header("Seleção")
            ano = st.selectbox("Ano", sorted(df_clean['ano'].unique(), reverse=True))
            m_disp = df_clean[df_clean['ano']==ano]['mes_nome'].unique()
            mes = st.selectbox("Mês", [meses_pt[m] for m in meses_pt if m in m_disp])

        m_eng = [k for k,v in meses_pt.items() if v==mes][0]
        df = df_clean[(df_clean['ano']==ano) & (df_clean['mes_nome']==m_eng)].copy()

        # SEÇÃO 1: MAPA RECEITA X DESPESA
        st.markdown('<p class="section-title">📌 Mapa da Receita x Despesa</p>', unsafe_allow_html=True)
        rec = df[df['valor'] > 0]['valor'].sum()
        desp = df[df['valor'] < 0]['valor'].sum()
        saldo = rec + desp

        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.metric("Receitas Reais", f"R$ {rec:,.2f}")
        col_r2.metric("Despesas Reais", f"R$ {abs(desp):,.2f}")
        col_r3.metric("Saldo Líquido", f"R$ {saldo:,.2f}")

        # SEÇÃO 2: MAPA GESTÃO
        st.markdown('<p class="section-title">📂 Mapa das Despesas Por Área de Gestão</p>', unsafe_allow_html=True)
        
        def v_gest(n): return abs(df[(df['valor'] < 0) & (df['gestao'] == n)]['valor'].sum())

        col_g1, col_g2, col_g3, col_g4 = st.columns(4)
        col_g1.metric("Pessoas", f"R$ {v_gest('Gestão de Pessoas'):,.2f}")
        col_g2.metric("Operacional", f"R$ {v_gest('Gestão Operacional'):,.2f}")
        col_g3.metric("Financiamentos", f"R$ {v_gest('Gestão de Financiamentos'):,.2f}")
        col_g4.metric("Infraestrutura", f"R$ {v_gest('Infraestrutura e Governança'):,.2f}")

        st.divider()

        # GRÁFICOS
        def plot_h(df_in, col, titulo, total_r, colors):
            temp = df_in[df_in['valor'] < 0].groupby(col)['valor'].sum().abs().reset_index().sort_values('valor')
            temp['pct'] = (temp['valor'] / total_r * 100) if total_r > 0 else 0
            temp['txt'] = temp.apply(lambda x: f"R$ {x['valor']:,.2f} ({x['pct']:.1f}%)", axis=1)
            fig = px.bar(temp, x='valor', y=col, text='txt', color=col, color_discrete_sequence=colors, title=titulo)
            fig.update_traces(textposition='outside', textfont=dict(color='black', size=13), cliponaxis=False)
            fig.update_layout(showlegend=False, margin=dict(l=10, r=150, t=50, b=10), height=400, xaxis=dict(showticklabels=False, showgrid=False), yaxis_title=None, xaxis_title=None)
            return fig

        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.plotly_chart(plot_h(df, 'gestao', "📊 Análise Vertical por Área", rec, px.colors.qualitative.Prism), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.plotly_chart(plot_h(df, 'categoria', "🏷️ Detalhamento por Categoria", rec, px.colors.qualitative.Safe), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.subheader("🛠️ Editor")
    search = st.text_input("Buscar transação:")
    df_s = df_raw[df_raw['descricao_original'].str.contains(search, case=False, na=False)] if search else df_raw
    if not df_s.empty:
        sel = st.selectbox("Selecione:", options=df_s.index, format_func=lambda x: f"{df_s.loc[x,'data_transacao'].strftime('%d/%m')} | {df_s.loc[x,'descricao_original']} | R$ {df_s.loc[x,'valor']}")
        r = df_s.loc[sel]
        c_e1, c_e2 = st.columns(2)
        with c_e1: n_g = st.selectbox("Gestão:", ["Gestão de Pessoas", "Gestão Operacional", "Gestão de Financiamentos", "Infraestrutura e Governança", "Outras Receitas"])
        with c_e2: n_c = st.text_input("Categoria:", value=r['categoria'])
        if st.button("💾 Gravar"):
            supabase.table("fluxo_caixa_ofx").update({"gestao": n_g, "categoria": n_c}).eq("id", r['id']).execute()
            st.rerun()
    st.dataframe(df_s[['data_transacao', 'descricao_original', 'valor', 'gestao', 'categoria']], use_container_width=True)
