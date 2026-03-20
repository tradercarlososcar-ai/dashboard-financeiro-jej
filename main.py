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

# 3. CONEXÃO
url, key = st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

def load_data_fresh():
    res = supabase.table("fluxo_caixa_ofx").select("*").execute()
    df = pd.DataFrame(res.data)
    if df.empty: return df
    df['data_transacao'] = pd.to_datetime(df['data_transacao'])
    df['valor'] = pd.to_numeric(df['valor'])
    df['ano'] = df['data_transacao'].dt.year
    df['mes_nome'] = df['data_transacao'].dt.month_name()
    return df

df_raw = load_data_fresh()

# 4. INTERFACE
st.title("📊 Gestão Financeira JEJ")
tab1, tab2 = st.tabs(["📈 Dashboard Limpo", "🛠️ Limpeza e Edição de Dados"])

meses_pt = {"January":"Janeiro","February":"Fevereiro","March":"Março","April":"Abril","May":"Maio","June":"Junho","July":"Julho","August":"Agosto","September":"Setembro","October":"Outubro","November":"Novembro","December":"Dezembro"}

# --- ABA 1: DASHBOARD (IGNORA TOTALMENTE RENDE FÁCIL) ---
with tab1:
    # FILTRO RIGOROSO: Remove aplicações financeiras da visualização
    df_dashboard = df_raw[~df_raw['descricao_original'].str.contains('RENDE FÁCIL|RENDE FACIL', case=False, na=False)].copy()
    
    if df_dashboard.empty:
        st.info("Aguardando dados (ou todos os dados atuais são Rende Fácil).")
    else:
        c1, c2 = st.columns(2)
        with c1: ano = st.selectbox("Ano", sorted(df_dashboard['ano'].unique(), reverse=True), key="a1")
        with c2:
            m_disp = df_dashboard[df_dashboard['ano']==ano]['mes_nome'].unique()
            mes = st.selectbox("Mês", [meses_pt[m] for m in meses_pt if m in m_disp], key="m1")

        m_eng = [k for k,v in meses_pt.items() if v==mes][0]
        df = df_dashboard[(df_dashboard['ano']==ano) & (df_dashboard['mes_nome']==m_eng)].copy()

        # Métricas
        rec = df[df['valor'] > 0]['valor'].sum()
        desp = df[df['valor'] < 0]['valor'].sum()
        st.columns(3)[0].metric("Receitas Reais", f"R$ {rec:,.2f}")
        st.columns(3)[1].metric("Despesas Reais", f"R$ {abs(desp):,.2f}")
        st.columns(3)[2].metric("Saldo Operacional", f"R$ {(rec+desp):,.2f}")

        # Gráficos
        def plot_h(df_in, col, titulo, total_r, colors):
            temp = df_in[df_in['valor'] < 0].groupby(col)['valor'].sum().abs().reset_index().sort_values('valor')
            temp['pct'] = (temp['valor'] / total_r * 100) if total_r > 0 else 0
            temp['txt'] = temp.apply(lambda x: f"R$ {x['valor']:,.2f} ({x['pct']:.1f}%)", axis=1)
            fig = px.bar(temp, x='valor', y=col, text='txt', color=col, color_discrete_sequence=colors, title=titulo)
            fig.update_traces(textposition='outside', textfont=dict(color='black', size=12), cliponaxis=False)
            fig.update_layout(showlegend=False, margin=dict(l=10, r=150, t=50, b=10), xaxis=dict(showticklabels=False))
            return fig

        st.plotly_chart(plot_h(df, 'gestao', "📌 Gestão", rec, px.colors.qualitative.Prism), use_container_width=True)
        st.plotly_chart(plot_h(df, 'categoria', "🏷️ Categoria", rec, px.colors.qualitative.Safe), use_container_width=True)

# --- ABA 2: EDITOR E LIMPEZA (PARA APAGAR O QUE NÃO DEVERIA ESTAR LÁ) ---
with tab2:
    st.subheader("🧹 Faxina no Banco de Dados")
    st.write("Use esta aba para excluir transações de 'Rende Fácil' ou corrigir erros da IA.")
    
    search = st.text_input("Buscar transação (ex: Rende Fácil):", value="Rende Fácil")
    df_search = df_raw[df_raw['descricao_original'].str.contains(search, case=False, na=False)]
    
    if not df_search.empty:
        st.warning(f"Foram encontrados {len(df_search)} registros com esse termo.")
        selected = st.selectbox("Selecione o registro para DELETAR ou EDITAR:", 
                                options=df_search.index,
                                format_func=lambda x: f"{df_search.loc[x,'data_transacao'].strftime('%d/%m')} | {df_search.loc[x,'descricao_original']} | R$ {df_search.loc[x,'valor']}")
        
        row = df_search.loc[selected]
        
        c_ed1, c_ed2 = st.columns(2)
        with c_ed1:
            if st.button("🗑️ EXCLUIR DEFINITIVAMENTE"):
                supabase.table("fluxo_caixa_ofx").delete().eq("id", row['id']).execute()
                st.rerun()
        with c_ed2:
            nova_g = st.selectbox("Corrigir Gestão para:", ["Gestão de Pessoas", "Gestão Operacional", "Gestão de Financiamentos", "Infraestrutura e Governança"])
            if st.button("💾 SALVAR CORREÇÃO"):
                supabase.table("fluxo_caixa_ofx").update({"gestao": nova_g}).eq("id", row['id']).execute()
                st.rerun()
    
    st.dataframe(df_search[['data_transacao', 'descricao_original', 'valor', 'gestao']], use_container_width=True)
