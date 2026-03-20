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

# 2. CONFIGURAÇÃO E ESTILO PERSONALIZADO (CAIXAS COLORIDAS)
st.set_page_config(page_title="Gestão JEJ", layout="wide")

st.markdown("""
    <style>
    /* Container geral das métricas para evitar a escadinha */
    [data-testid="stHorizontalBlock"] {
        align-items: center;
    }
    
    /* Caixa de Receita (Azul) */
    div[data-testid="stMetric"]:nth-child(1) {
        background-color: #E3F2FD;
        border: 2px solid #2196F3;
        padding: 15px;
        border-radius: 15px;
        color: #0D47A1;
    }
    
    /* Caixa de Despesa (Vermelha) */
    div[data-testid="stMetric"]:nth-child(2) {
        background-color: #FFEBEE;
        border: 2px solid #EF5350;
        padding: 15px;
        border-radius: 15px;
        color: #B71C1C;
    }
    
    /* Caixa de Saldo (Verde Musgo) */
    div[data-testid="stMetric"]:nth-child(3) {
        background-color: #F1F8E9;
        border: 2px solid #689F38;
        padding: 15px;
        border-radius: 15px;
        color: #33691E;
    }

    .chart-box { border: 1px solid #eeeeee; padding: 20px; border-radius: 12px; background-color: #ffffff; margin-bottom: 25px; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXÃO
url, key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def load_data_fresh():
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

df_raw = load_data_fresh()

# 4. INTERFACE
st.title("📊 Gestão Financeira JEJ")
tab1, tab2 = st.tabs(["📈 Dashboard", "🛠️ Editor e Limpeza"])

meses_pt = {"January":"Janeiro","February":"Fevereiro","March":"Março","April":"Abril","May":"Maio","June":"Junho","July":"Julho","August":"Agosto","September":"Setembro","October":"Outubro","November":"Novembro","December":"Dezembro"}

with tab1:
    # Filtro Rende Fácil (Segunda camada de proteção)
    df_dashboard = df_raw[~df_raw['descricao_original'].str.contains('RENDE FÁCIL|RENDE FACIL', case=False, na=False)].copy()
    
    if not df_dashboard.empty:
        with st.sidebar:
            st.header("Filtros")
            ano = st.selectbox("Ano", sorted(df_dashboard['ano'].unique(), reverse=True))
            m_disp = df_dashboard[df_dashboard['ano']==ano]['mes_nome'].unique()
            mes = st.selectbox("Mês", [meses_pt[m] for m in meses_pt if m in m_disp])

        m_eng = [k for k,v in meses_pt.items() if v==mes][0]
        df = df_dashboard[(df_dashboard['ano']==ano) & (df_dashboard['mes_nome']==m_eng)].copy()

        # MÉTRICAS LADO A LADO
        rec = df[df['valor'] > 0]['valor'].sum()
        desp = df[df['valor'] < 0]['valor'].sum()
        saldo = rec + desp

        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Receitas Reais", f"R$ {rec:,.2f}")
        col_m2.metric("Despesas Reais", f"R$ {abs(desp):,.2f}")
        col_m3.metric("Saldo Líquido", f"R$ {saldo:,.2f}")

        st.divider()

        # Funções de Gráfico (Barras horizontais, Texto Preto, Largura Total)
        def plot_h(df_in, col, titulo, total_r, colors):
            temp = df_in[df_in['valor'] < 0].groupby(col)['valor'].sum().abs().reset_index().sort_values('valor')
            temp['pct'] = (temp['valor'] / total_r * 100) if total_r > 0 else 0
            temp['txt'] = temp.apply(lambda x: f"R$ {x['valor']:,.2f} ({x['pct']:.1f}%)", axis=1)
            fig = px.bar(temp, x='valor', y=col, text='txt', color=col, color_discrete_sequence=colors, title=titulo)
            fig.update_traces(textposition='outside', textfont=dict(color='black', size=13), cliponaxis=False)
            fig.update_layout(showlegend=False, margin=dict(l=10, r=150, t=50, b=10), height=450, xaxis=dict(showticklabels=False, showgrid=False), yaxis_title=None, xaxis_title=None)
            return fig

        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.plotly_chart(plot_h(df, 'gestao', "📌 Despesas por Área de Gestão", rec, px.colors.qualitative.Prism), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="chart-box">', unsafe_allow_html=True)
        st.plotly_chart(plot_h(df, 'categoria', "🏷️ Despesas por Categoria", rec, px.colors.qualitative.Safe), use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --- ABA 2: EDITOR (MANTIDA PARA AJUSTES MANUAIS) ---
with tab2:
    st.subheader("🛠️ Editor de Lançamentos")
    search = st.text_input("Buscar transação:")
    df_search = df_raw[df_raw['descricao_original'].str.contains(search, case=False, na=False)] if search else df_raw
    
    if not df_search.empty:
        selected = st.selectbox("Selecione para editar:", options=df_search.index,
                                format_func=lambda x: f"{df_search.loc[x,'data_transacao'].strftime('%d/%m')} | {df_search.loc[x,'descricao_original']} | R$ {df_search.loc[x,'valor']}")
        row = df_search.loc[selected]
        if st.button("🗑️ EXCLUIR REGISTRO"):
            supabase.table("fluxo_caixa_ofx").delete().eq("id", row['id']).execute()
            st.rerun()
    st.dataframe(df_search[['data_transacao', 'descricao_original', 'valor', 'gestao', 'categoria']], use_container_width=True)
