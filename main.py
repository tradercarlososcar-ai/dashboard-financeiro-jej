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

# 2. CONFIGURAÇÃO E CSS (CORES FIXAS E LADO A LADO)
st.set_page_config(page_title="Gestão JEJ", layout="wide")

st.markdown("""
    <style>
    /* Forçar alinhamento e cores das métricas */
    [data-testid="stMetric"] {
        padding: 20px !important;
        border-radius: 15px !important;
        border: 2px solid rgba(0,0,0,0.1) !important;
    }
    /* Receita - Azul */
    [data-testid="stHorizontalBlock"] > div:nth-child(1) [data-testid="stMetric"] {
        background-color: #E3F2FD !important;
        border-color: #2196F3 !important;
    }
    /* Despesa - Vermelho */
    [data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stMetric"] {
        background-color: #FFEBEE !important;
        border-color: #EF5350 !important;
    }
    /* Saldo - Verde Musgo */
    [data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stMetric"] {
        background-color: #F1F8E9 !important;
        border-color: #689F38 !important;
    }
    [data-testid="stMetricLabel"] { color: #333333 !important; font-weight: bold !important; }
    [data-testid="stMetricValue"] { color: #000000 !important; }
    
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
tab1, tab2 = st.tabs(["📈 Dashboard", "🛠️ Importar e Editar"])

meses_pt = {"January":"Janeiro","February":"Fevereiro","March":"Março","April":"Abril","May":"Maio","June":"Junho","July":"Julho","August":"Agosto","September":"Setembro","October":"Outubro","November":"Novembro","December":"Dezembro"}

with tab1:
    df_dashboard = df_raw[~df_raw['descricao_original'].str.contains('RENDE FÁCIL|RENDE FACIL', case=False, na=False)].copy()
    
    if not df_dashboard.empty:
        with st.sidebar:
            st.header("Filtros")
            ano = st.selectbox("Ano", sorted(df_dashboard['ano'].unique(), reverse=True))
            m_disp = df_dashboard[df_dashboard['ano']==ano]['mes_nome'].unique()
            mes = st.selectbox("Mês", [meses_pt[m] for m in meses_pt if m in m_disp])

        m_eng = [k for k,v in meses_pt.items() if v==mes][0]
        df = df_dashboard[(df_dashboard['ano']==ano) & (df_dashboard['mes_nome']==m_eng)].copy()

        rec, desp = df[df['valor'] > 0]['valor'].sum(), df[df['valor'] < 0]['valor'].sum()
        saldo = rec + desp

        # MÉTRICAS LADO A LADO COM CORES CORRIGIDAS
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Receitas Reais", f"R$ {rec:,.2f}")
        col_m2.metric("Despesas Reais", f"R$ {abs(desp):,.2f}")
        col_m3.metric("Saldo Líquido", f"R$ {saldo:,.2f}")

        st.divider()

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

# --- ABA 2: IMPORTAR E EDITAR ---
with tab2:
    st.subheader("📥 Importar Novo Arquivo OFX")
    st.info("Nota: Para processamento com IA (Gemini), use o formulário do n8n. Este upload aqui é para conferência direta se necessário.")
    uploaded_file = st.file_uploader("Escolha o arquivo .ofx", type="ofx")
    
    st.divider()
    st.subheader("🛠️ Editor de Lançamentos")
    search = st.text_input("Buscar transação (ex: nome de fornecedor):")
    df_search = df_raw[df_raw['descricao_original'].str.contains(search, case=False, na=False)] if search else df_raw
    
    if not df_search.empty:
        selected = st.selectbox("Selecione para editar/excluir:", options=df_search.index,
                                format_func=lambda x: f"{df_search.loc[x,'data_transacao'].strftime('%d/%m')} | {df_search.loc[x,'descricao_original']} | R$ {df_search.loc[x,'valor']}")
        row = df_search.loc[selected]
        
        col_ed1, col_ed2 = st.columns(2)
        with col_ed1:
            nova_g = st.selectbox("Corrigir Área de Gestão:", ["Gestão de Pessoas", "Gestão Operacional", "Gestão de Financiamentos", "Infraestrutura e Governança", "Outras Receitas"], 
                                  index=0 if row['gestao'] not in ["Gestão de Pessoas", "Gestão Operacional", "Gestão de Financiamentos", "Infraestrutura e Governança", "Outras Receitas"] else ["Gestão de Pessoas", "Gestão Operacional", "Gestão de Financiamentos", "Infraestrutura e Governança", "Outras Receitas"].index(row['gestao']))
        with col_ed2:
            nova_c = st.text_input("Corrigir Categoria:", value=row['categoria'])
            
        btn_s, btn_e = st.columns(2)
        with btn_s:
            if st.button("💾 Salvar Alteração"):
                supabase.table("fluxo_caixa_ofx").update({"gestao": nova_g, "categoria": nova_c}).eq("id", row['id']).execute()
                st.success("Atualizado!")
                st.rerun()
        with btn_e:
            if st.button("🗑️ EXCLUIR DEFINITIVAMENTE"):
                supabase.table("fluxo_caixa_ofx").delete().eq("id", row['id']).execute()
                st.warning("Excluído!")
                st.rerun()
                
    st.dataframe(df_search[['data_transacao', 'descricao_original', 'valor', 'gestao', 'categoria']], use_container_width=True)
