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

# 2. CONFIGURAÇÃO E ESTILO
st.set_page_config(page_title="Gestão JEJ", layout="wide")
st.markdown("""
    <style>
    div[data-testid="stMetric"] { background-color: #ffffff; border: 1px solid #eeeeee; padding: 15px; border-radius: 8px; }
    .chart-box { border: 1px solid #eeeeee; padding: 20px; border-radius: 8px; background-color: #ffffff; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXÃO
url, key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

@st.cache_data(ttl=300)
def load_data():
    try:
        res = supabase.table("fluxo_caixa_ofx").select("*").execute()
        df = pd.DataFrame(res.data)
        if df.empty: return df
        df['data_transacao'] = pd.to_datetime(df['data_transacao'])
        df['valor'] = pd.to_numeric(df['valor'])
        df['ano'] = df['data_transacao'].dt.year
        df['mes_nome'] = df['data_transacao'].dt.month_name()
        return df
    except: return pd.DataFrame()

df_raw = load_data()

# 4. PROCESSAMENTO
if not df_raw.empty:
    # Filtro Rende Fácil (conforme seu Power Query)
    df_clean = df_raw[~df_raw['descricao_original'].str.contains('RENDE FÁCIL|RENDE FACIL', case=False, na=False)].copy()

    with st.sidebar:
        st.header("Filtros")
        ano_sel = st.selectbox("Ano", sorted(df_clean['ano'].unique(), reverse=True))
        meses_pt = {"January":"Janeiro","February":"Fevereiro","March":"Março","April":"Abril","May":"Maio","June":"Junho","July":"Julho","August":"Agosto","September":"Setembro","October":"Outubro","November":"Novembro","December":"Dezembro"}
        m_disp = df_clean[df_clean['ano']==ano_sel]['mes_nome'].unique()
        lista_m = [meses_pt[m] for m in meses_pt if m in m_disp]
        mes_filt = st.selectbox("Mês", lista_m)

    m_eng = [k for k,v in meses_pt.items() if v==mes_filt][0]
    df = df_clean[(df_clean['ano']==ano_sel) & (df_clean['mes_nome']==m_eng)].copy()

    # MÉTRICAS
    rec = df[df['valor'] > 0]['valor'].sum()
    desp = df[df['valor'] < 0]['valor'].sum()
    saldo = rec + desp

    st.title("📊 Gestão Financeira JEJ")
    c1, c2, c3 = st.columns(3)
    c1.metric("Receitas Reais", f"R$ {rec:,.2f}")
    c2.metric("Despesas Reais", f"R$ {abs(desp):,.2f}")
    c3.metric("Saldo Líquido", f"R$ {saldo:,.2f}")

    st.divider()

    # 5. GRÁFICOS COM PERCENTUAIS E CORES DIVERSAS
    col1, col2 = st.columns(2)

    # Função para preparar dados com % (Análise Vertical)
    def prep_df_pct(df_input, coluna_grupo, total_receita):
        temp = df_input[df_input['valor'] < 0].groupby(coluna_grupo)['valor'].sum().abs().reset_index()
        temp = temp.sort_values('valor', ascending=True)
        # Cálculo da representatividade sobre a Receita
        temp['pct'] = (temp['valor'] / total_receita * 100) if total_receita > 0 else 0
        temp['texto'] = temp.apply(lambda x: f"R$ {x['valor']:,.2f} ({x['pct']:.1f}%)", axis=1)
        return temp

    with col1:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.subheader("📌 Despesas por Gestão (% sobre Receita)")
        df_g = prep_df_pct(df, 'gestao', rec)
        # Cores diversas usando escala qualitativa
        fig1 = px.bar(df_g, x='valor', y='gestao', orientation='h', text='texto',
                      color='gestao', color_discrete_sequence=px.colors.qualitative.Prism)
        fig1.update_traces(textposition='outside')
        fig1.update_layout(showlegend=False, margin=dict(l=0, r=50, t=10, b=0), height=350, 
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig1, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.subheader("🏷️ Despesas por Categoria (% sobre Receita)")
        df_c = prep_df_pct(df, 'categoria', rec)
        fig2 = px.bar(df_c, x='valor', y='categoria', orientation='h', text='texto',
                      color='categoria', color_discrete_sequence=px.colors.qualitative.Safe)
        fig2.update_traces(textposition='outside')
        fig2.update_layout(showlegend=False, margin=dict(l=0, r=50, t=10, b=0), height=350,
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title=None, yaxis_title=None)
        st.plotly_chart(fig2, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
