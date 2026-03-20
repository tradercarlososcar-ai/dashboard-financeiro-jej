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

# 2. CONFIGURAÇÃO
st.set_page_config(page_title="Gestão JEJ", layout="wide")

# Função para criar os cards coloridos
def caixa_indicador(titulo, valor, cor_fundo, cor_borda):
    st.markdown(f"""
        <div style="
            background-color: {cor_fundo};
            border: 2px solid {cor_borda};
            padding: 15px;
            border-radius: 15px;
            text-align: left;
            margin-bottom: 10px;
            height: 160px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        ">
            <p style="color: #333; margin: 0; font-size: 14px; font-weight: bold; line-height: 1.2;">{titulo}</p>
            <h2 style="color: #000; margin-top: 10px; margin-bottom: 0; font-size: 22px; white-space: nowrap;">{valor}</h2>
        </div>
    """, unsafe_allow_html=True)

# 3. CONEXÃO
url, key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

@st.cache_data(ttl=60)
def load_data():
    try:
        res = supabase.table("fluxo_caixa_ofx").select("*").execute()
        df = pd.DataFrame(res.data)
        if df.empty: return df
        
        # Converte para data, mas NÃO deleta a linha se falhar (errors='coerce' vira NaT)
        df['data_transacao_dt'] = pd.to_datetime(df['data_transacao'], errors='coerce')
        df['valor'] = pd.to_numeric(df['valor'], errors='coerce').fillna(0)
        
        # Cria colunas de filtro apenas para datas válidas, senão usa padrão
        df['ano'] = df['data_transacao_dt'].dt.year.fillna(0).astype(int)
        df['mes_nome'] = df['data_transacao_dt'].dt.month_name().fillna("Sem Data")
        
        return df
    except:
        return pd.DataFrame()

df_raw = load_data()

# 4. INTERFACE
st.title("📊 Painel de Gestão Financeira - JEJ")
tab1, tab2 = st.tabs(["📈 Dashboard", "🛠️ Editor"])

meses_pt = {"January":"Janeiro","February":"Fevereiro","March":"Março","April":"Abril","May":"Maio","June":"Junho","July":"Julho","August":"Agosto","September":"Setembro","October":"Outubro","November":"Novembro","December":"Dezembro", "Sem Data": "Sem Data"}

with tab1:
    # Filtro visual para o Dashboard
    df_clean = df_raw[~df_raw['descricao_original'].str.contains('RENDE FÁCIL|RENDE FACIL', case=False, na=False)].copy()
    
    if not df_clean.empty:
        with st.sidebar:
            st.header("Seleção")
            anos_disponiveis = sorted(df_clean['ano'].unique(), reverse=True)
            ano = st.selectbox("Ano", anos_disponiveis)
            
            m_disp = df_clean[df_clean['ano']==ano]['mes_nome'].unique()
            lista_meses = [meses_pt[m] for m in meses_pt if m in m_disp]
            mes = st.selectbox("Mês", lista_meses)

        m_eng = [k for k,v in meses_pt.items() if v==mes][0]
        df = df_clean[(df_clean['ano']==ano) & (df_clean['mes_nome']==m_eng)].copy()

        st.subheader(f"📌 Resumo de {mes}/{ano}")
        rec = df[df['valor'] > 0]['valor'].sum()
        desp = df[df['valor'] < 0]['valor'].sum()
        saldo = rec + desp

        c1, c2, c3 = st.columns(3)
        with c1: caixa_indicador("Receitas", f"R$ {rec:,.2f}", "#E3F2FD", "#2196F3")
        with c2: caixa_indicador("Despesas", f"R$ {abs(desp):,.2f}", "#FFEBEE", "#EF5350")
        with c3: caixa_indicador("Saldo Líquido", f"R$ {saldo:,.2f}", "#F1F8E9", "#689F38")

        st.write("")
        st.subheader("📂 Despesas por Área de Gestão")
        
        def v_gest_info(n, total_r):
            valor = abs(df[(df['valor'] < 0) & (df['gestao'] == n)]['valor'].sum())
            pct = (valor / total_r * 100) if total_r > 0 else 0
            return f"{n}<br>({pct:.1f}%)", f"R$ {valor:,.2f}"

        g1, g2, g3, g4 = st.columns(4)
        with g1: 
            t1, v1 = v_gest_info('Gestão de Pessoas', rec)
            caixa_indicador(t1, v1, "#FFFDE7", "#FBC02D")
        with g2: 
            t2, v2 = v_gest_info('Gestão Operacional', rec)
            caixa_indicador(t2, v2, "#FFFDE7", "#FBC02D")
        with g3: 
            t3, v3 = v_gest_info('Gestão de Financiamentos', rec)
            caixa_indicador(t3, v3, "#FFFDE7", "#FBC02D")
        with g4: 
            t4, v4 = v_gest_info('Infraestrutura e Governança', rec)
            caixa_indicador(t4, v4, "#FFFDE7", "#FBC02D")

        st.divider()

        temp_cat = df[df['valor'] < 0].groupby('categoria')['valor'].sum().abs().reset_index().sort_values('valor')
        if not temp_cat.empty:
            fig = px.bar(temp_cat, x='valor', y='categoria', text_auto='.2s', title="🏷️ Detalhe por Categoria", orientation='h')
            st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("🛠️ Editor de Transações")
    search = st.text_input("Buscar transação (descrição):")
    df_s = df_raw[df_raw['descricao_original'].str.contains(search, case=False, na=False)] if search else df_raw
    
    if not df_s.empty:
        # Mostra a data bruta se a conversão falhar, evitando erro visual
        sel = st.selectbox(
            "Selecione para editar:", 
            options=df_s.index, 
            format_func=lambda x: f"{df_s.loc[x,'data_transacao']} | {df_s.loc[x,'descricao_original']} | R$ {df_s.loc[x,'valor']}"
        )
        
        r = df_s.loc[sel]
        c_e1, c_e2 = st.columns(2)
        with c_e1: n_g = st.selectbox("Gestão:", ["Gestão de Pessoas", "Gestão Operacional", "Gestão de Financiamentos", "Infraestrutura e Governança", "Outras Receitas", "Não Classificado"], index=0)
        with c_e2: n_c = st.text_input("Categoria:", value=str(r['categoria']))
        
        if st.button("💾 Gravar Alteração"):
            supabase.table("fluxo_caixa_ofx").update({"gestao": n_g, "categoria": n_c}).eq("id", r['id']).execute()
            st.success("Alteração gravada!")
            st.rerun()
            
    st.dataframe(df_s[['data_transacao', 'descricao_original', 'valor', 'gestao', 'categoria']], use_container_width=True)
