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

# 2. CONFIGURAÇÃO E CSS (MÉTRICAS COLORIDAS + NEUTRAS)
st.set_page_config(page_title="Gestão JEJ", layout="wide")

st.markdown("""
    <style>
    /* Estilo Geral das Métricas */
    [data-testid="stMetric"] {
        padding: 15px !important;
        border-radius: 12px !important;
        border: 1px solid rgba(0,0,0,0.1) !important;
    }
    /* LINHA 1 - CORES ESPECÍFICAS */
    /* Receita - Azul */
    [data-testid="stHorizontalBlock"]:nth-of-type(1) > div:nth-child(1) [data-testid="stMetric"] {
        background-color: #E3F2FD !important; border-color: #2196F3 !important;
    }
    /* Despesa - Vermelho */
    [data-testid="stHorizontalBlock"]:nth-of-type(1) > div:nth-child(2) [data-testid="stMetric"] {
        background-color: #FFEBEE !important; border-color: #EF5350 !important;
    }
    /* Saldo - Verde Musgo */
    [data-testid="stHorizontalBlock"]:nth-of-type(1) > div:nth-child(3) [data-testid="stMetric"] {
        background-color: #F1F8E9 !important; border-color: #689F38 !important;
    }
    
    /* LINHA 2 - CORES NEUTRAS (GESTÃO) */
    [data-testid="stHorizontalBlock"]:nth-of-type(2) [data-testid="stMetric"] {
        background-color: #F8F9FA !important; border-color: #DEE2E6 !important;
    }

    [data-testid="stMetricLabel"] { color: #333333 !important; font-size: 14px !important; }
    [data-testid="stMetricValue"] { color: #000000 !important; font-size: 20px !important; }
    .chart-box { border: 1px solid #eeeeee; padding: 20px; border-radius: 12px; background-color: #ffffff; margin-bottom: 25px; }
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
tab1, tab2 = st.tabs(["📈 Dashboard Executivo", "🛠️ Editor de Lançamentos"])

meses_pt = {"January":"Janeiro","February":"Fevereiro","March":"Março","April":"Abril","May":"Maio","June":"Junho","July":"Julho","August":"Agosto","September":"Setembro","October":"Outubro","November":"Novembro","December":"Dezembro"}

with tab1:
    df_dashboard = df_raw[~df_raw['descricao_original'].str.contains('RENDE FÁCIL|RENDE FACIL', case=False, na=False)].copy()
    
    if not df_dashboard.empty:
        with st.sidebar:
            st.header("Filtros de Período")
            ano = st.selectbox("Ano", sorted(df_dashboard['ano'].unique(), reverse=True))
            m_disp = df_dashboard[df_dashboard['ano']==ano]['mes_nome'].unique()
            mes = st.selectbox("Mês", [meses_pt[m] for m in meses_pt if m in m_disp])

        m_eng = [k for k,v in meses_pt.items() if v==mes][0]
        df = df_dashboard[(df_dashboard['ano']==ano) & (df_dashboard['mes_nome']==m_eng)].copy()

        # CÁLCULOS TOTAIS
        rec = df[df['valor'] > 0]['valor'].sum()
        desp = df[df['valor'] < 0]['valor'].sum()
        saldo = rec + desp

        # LINHA 1: MÉTRICAS PRINCIPAIS
        c1, c2, c3 = st.columns(3)
        c1.metric("Receitas Reais", f"R$ {rec:,.2f}")
        c2.metric("Despesas Reais", f"R$ {abs(desp):,.2f}")
        c3.metric("Saldo Líquido", f"R$ {saldo:,.2f}")

        # LINHA 2: DESPESAS POR GESTÃO (NEUTRAS)
        def get_v(g_name):
            val = df[(df['valor'] < 0) & (df['gestao'] == g_name)]['valor'].sum()
            return abs(val)

        st.write("") # Espaçador
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Gestão de Pessoas", f"R$ {get_v('Gestão de Pessoas'):,.2f}")
        g2.metric("Gestão Operacional", f"R$ {get_v('Gestão Operacional'):,.2f}")
        g3.metric("Financiamentos", f"R$ {get_v('Gestão de Financiamentos'):,.2f}")
        g4.metric("Infraestrutura", f"R$ {get_v('Infraestrutura e Governança'):,.2f}")

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
        st.plotly_chart(plot_h(df, 'gestao', "📌 Análise por Área de Gestão", rec, px.colors.qualitative.Prism), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.plotly_chart(plot_h(df, 'categoria', "🏷️ Detalhamento por Categoria", rec, px.colors.qualitative.Safe), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    st.subheader("🛠️ Ferramentas de Edição")
    search = st.text_input("Filtrar por descrição:")
    df_s = df_raw[df_raw['descricao_original'].str.contains(search, case=False, na=False)] if search else df_raw
    if not df_s.empty:
        sel = st.selectbox("Selecione a transação:", options=df_s.index, format_func=lambda x: f"{df_s.loc[x,'data_transacao'].strftime('%d/%m')} | {df_s.loc[x,'descricao_original']} | R$ {df_s.loc[x,'valor']}")
        r = df_s.loc[sel]
        c_e1, c_e2 = st.columns(2)
        with c_e1: n_g = st.selectbox("Nova Gestão:", ["Gestão de Pessoas", "Gestão Operacional", "Gestão de Financiamentos", "Infraestrutura e Governança", "Outras Receitas"])
        with c_e2: n_c = st.text_input("Nova Categoria:", value=r['categoria'])
        if st.button("💾 Atualizar Lançamento"):
            supabase.table("fluxo_caixa_ofx").update({"gestao": n_g, "categoria": n_c}).eq("id", r['id']).execute()
            st.rerun()
    st.dataframe(df_s[['data_transacao', 'descricao_original', 'valor', 'gestao', 'categoria']], use_container_width=True)
