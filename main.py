import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px

# 1. SEGURANÇA E LOGIN
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

# 2. CONFIGURAÇÃO E ESTILO (Layout em Linhas e Caixas Discretas)
st.set_page_config(page_title="Gestão JEJ", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    div[data-testid="stMetric"] { background-color: #ffffff; border: 1px solid #eeeeee; padding: 15px; border-radius: 8px; }
    .chart-box { border: 1px solid #eeeeee; padding: 25px; border-radius: 8px; background-color: #ffffff; margin-bottom: 25px; }
    /* Ajuste para garantir que o texto do eixo Y (nomes longos) não corte */
    .js-plotly-plot .plotly .ticktext { font-size: 13px !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. CONEXÃO COM O SUPABASE
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

# 4. PROCESSAMENTO E REGRAS DO EXCEL
if not df_raw.empty:
    # Filtro "Rende Fácil" (conforme sua lógica de conciliação)
    df_clean = df_raw[~df_raw['descricao_original'].str.contains('RENDE FÁCIL|RENDE FACIL', case=False, na=False)].copy()

    # Filtros na Lateral (Sidebar)
    with st.sidebar:
        st.header("Período de Análise")
        ano_sel = st.selectbox("Selecione o Ano", sorted(df_clean['ano'].unique(), reverse=True))
        meses_pt = {"January":"Janeiro","February":"Fevereiro","March":"Março","April":"Abril","May":"Maio","June":"Junho","July":"Julho","August":"Agosto","September":"Setembro","October":"Outubro","November":"Novembro","December":"Dezembro"}
        m_disp = df_clean[df_clean['ano']==ano_sel]['mes_nome'].unique()
        lista_m = [meses_pt[m] for m in meses_pt if m in m_disp]
        mes_filt = st.selectbox("Selecione o Mês", lista_m)

    m_eng = [k for k,v in meses_pt.items() if v==mes_filt][0]
    df = df_clean[(df_clean['ano']==ano_sel) & (df_clean['mes_nome']==m_eng)].copy()

    # MÉTRICAS EXECUTIVAS
    rec = df[df['valor'] > 0]['valor'].sum()
    desp = df[df['valor'] < 0]['valor'].sum()
    saldo = rec + desp

    st.title("📊 Painel Gestão Financeira JEJ")
    c1, c2, c3 = st.columns(3)
    c1.metric("Receitas Reais (A)", f"R$ {rec:,.2f}")
    c2.metric("Despesas Reais (B)", f"R$ {abs(desp):,.2f}")
    # Delta mostra o saldo como percentual da receita (Análise Vertical Global)
    delta_text = f"{(saldo/rec*100):.1f}% da Receita" if rec > 0 else "N/A"
    c3.metric("Saldo Líquido (A-B)", f"R$ {saldo:,.2f}", delta=delta_text)

    st.divider()

    # 5. ANÁLISE VERTICAL (PERCENTUAIS E CORES DIVERSAS) - LAYOUT EM LINHAS

    # Função para preparar dados com % sobre a Receita
    def prep_df_pct(df_input, coluna_grupo, total_receita):
        # Filtra apenas despesas e agrupa
        temp = df_input[df_input['valor'] < 0].groupby(coluna_grupo)['valor'].sum().abs().reset_index()
        # Ordena do menor para o maior valor (para as barras maiores ficarem em cima no gráfico H)
        temp = temp.sort_values('valor', ascending=True)
        # Cálculo da Análise Vertical
        temp['pct'] = (temp['valor'] / total_receita * 100) if total_receita > 0 else 0
        # Formata o texto do rótulo: R$ Valor (Percentual %)
        temp['texto_rotulo'] = temp.apply(lambda x: f"R$ {x['valor']:,.2f} ({x['pct']:.1f}%)", axis=1)
        return temp

    # Função Genérica para Criar Gráfico de Barras Horizontais com Texto Preto
    def criar_grafico_h(df_data, x_col, y_col, color_col, colorscale, titulo_grafico):
        fig = px.bar(df_data, x=x_col, y=y_col, orientation='h', text='texto_rotulo',
                     color=color_col, color_discrete_sequence=colorscale, title=titulo_grafico)
        
        # AJUSTES TÉCNICOS CRUCIAIS:
        fig.update_traces(
            textposition='outside', # Texto para fora da barra
            textfont=dict(color='black', size=13), # FORÇA COR PRETA (BLACK) E AUMENTA O TAMANHO
            cliponaxis=False # IMPEDE O CORTE DO TEXTO NAS BORDAS
        )
        
        fig.update_layout(
            showlegend=False, # Remove legenda repetitiva
            # Aumenta a margem direita (r=150) para dar espaço ao texto longo
            margin=dict(l=10, r=150, t=50, b=10), 
            height=450, # Aumenta a altura para caber mais itens e nomes longos
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            xaxis_title=None, 
            yaxis_title=None,
            xaxis=dict(showticklabels=False, showgrid=False) # Esconde o eixo X (valores duplicados)
        )
        return fig

    # --- LINHA 1: GRÁFICO DE GESTÃO (LARGURA TOTAL) ---
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    df_g = prep_df_pct(df, 'gestao', rec)
    if not df_g.empty:
        fig_gestao = criar_grafico_h(df_g, 'valor', 'gestao', 'gestao', 
                                    px.colors.qualitative.Prism, "📌 Despesas por Área de Gestão (% sobre Receita)")
        st.plotly_chart(fig_gestao, use_container_width=True)
    else:
        st.info("Não há despesas registradas para este mês/ano.")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- LINHA 2: GRÁFICO DE CATEGORIA (LARGURA TOTAL) ---
    st.markdown('<div class="chart-box">', unsafe_allow_html=True)
    df_c = prep_df_pct(df, 'categoria', rec)
    if not df_c.empty:
        # Aumenta um pouco mais a altura para Categorias (que costumam ter mais itens)
        fig_cat = criar_grafico_h(df_c, 'valor', 'categoria', 'categoria', 
                                  px.colors.qualitative.Safe, "🏷️ Despesas por Categoria (% sobre Receita)")
        fig_cat.update_layout(height=550) 
        st.plotly_chart(fig_cat, use_container_width=True)
    else:
        st.info("Não há despesas categorizadas para este mês/ano.")
    st.markdown('</div>', unsafe_allow_html=True)
