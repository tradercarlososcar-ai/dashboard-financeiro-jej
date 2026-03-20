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

# Função para carregar dados (sem cache para o editor refletir mudanças na hora)
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

# 4. INTERFACE COM ABAS
st.title("📊 Sistema de Gestão Financeira JEJ")
tab_dashboard, tab_editor = st.tabs(["📈 Dashboard de Análise", "🛠️ Editor de Lançamentos"])

meses_pt = {"January":"Janeiro","February":"Fevereiro","March":"Março","April":"Abril","May":"Maio","June":"Junho","July":"Julho","August":"Agosto","September":"Setembro","October":"Outubro","November":"Novembro","December":"Dezembro"}

# --- ABA 1: DASHBOARD ---
with tab_dashboard:
    if df_raw.empty:
        st.warning("Banco de dados vazio.")
    else:
        df_clean = df_raw[~df_raw['descricao_original'].str.contains('RENDE FÁCIL|RENDE FACIL', case=False, na=False)].copy()
        
        c_f1, c_f2 = st.columns(2)
        with c_f1: ano_sel = st.selectbox("Ano", sorted(df_clean['ano'].unique(), reverse=True), key="ano_dash")
        with c_f2:
            m_disp = df_clean[df_clean['ano']==ano_sel]['mes_nome'].unique()
            lista_m = [meses_pt[m] for m in meses_pt if m in m_disp]
            mes_filt = st.selectbox("Mês", lista_m, key="mes_dash")

        m_eng = [k for k,v in meses_pt.items() if v==mes_filt][0]
        df = df_clean[(df_clean['ano']==ano_sel) & (df_clean['mes_nome']==m_eng)].copy()

        rec = df[df['valor'] > 0]['valor'].sum()
        desp = df[df['valor'] < 0]['valor'].sum()
        saldo = rec + desp

        k1, k2, k3 = st.columns(3)
        k1.metric("Receitas Reais", f"R$ {rec:,.2f}")
        k2.metric("Despesas Reais", f"R$ {abs(desp):,.2f}")
        k3.metric("Saldo Líquido", f"R$ {saldo:,.2f}")

        st.divider()

        # Gráficos (Lógica anterior de barras horizontais e cores pretas)
        def criar_fig(df_in, col, titulo, total_r, colors):
            temp = df_in[df_in['valor'] < 0].groupby(col)['valor'].sum().abs().reset_index().sort_values('valor')
            temp['pct'] = (temp['valor'] / total_r * 100) if total_r > 0 else 0
            temp['txt'] = temp.apply(lambda x: f"R$ {x['valor']:,.2f} ({x['pct']:.1f}%)", axis=1)
            fig = px.bar(temp, x='valor', y=col, text='txt', color=col, color_discrete_sequence=colors, title=titulo)
            fig.update_traces(textposition='outside', textfont=dict(color='black', size=13), cliponaxis=False)
            fig.update_layout(showlegend=False, margin=dict(l=10, r=150, t=50, b=10), xaxis_title=None, yaxis_title=None, xaxis=dict(showticklabels=False, showgrid=False))
            return fig

        st.plotly_chart(criar_fig(df, 'gestao', "📌 Despesas por Gestão", rec, px.colors.qualitative.Prism), use_container_width=True)
        st.plotly_chart(criar_fig(df, 'categoria', "🏷️ Despesas por Categoria", rec, px.colors.qualitative.Safe), use_container_width=True)

# --- ABA 2: EDITOR (ONDE VOCÊ RESOLVE O PROBLEMA DA GESTÃO DE PESSOAS) ---
with tab_editor:
    st.subheader("🔍 Localizar e Corrigir Lançamentos")
    
    # Filtro rápido para o editor
    busca = st.text_input("Filtrar por descrição (ex: nome de funcionário):")
    df_edit = df_raw.copy()
    if busca:
        df_edit = df_edit[df_edit['descricao_original'].str.contains(busca, case=False)]

    st.write(f"Exibindo {len(df_edit)} registros encontrados.")
    
    # Seleção de linha para editar
    selected_row = st.selectbox("Selecione a transação para editar/excluir:", 
                                options=df_edit.index, 
                                format_func=lambda x: f"{df_edit.loc[x, 'data_transacao'].strftime('%d/%m/%Y')} | {df_edit.loc[x, 'descricao_original']} | R$ {df_edit.loc[x, 'valor']}")

    if not df_edit.empty:
        row = df_edit.loc[selected_row]
        
        col_ed1, col_ed2, col_ed3 = st.columns(3)
        with col_ed1:
            nova_gestao = st.selectbox("Mudar Gestão para:", 
                                      ["Gestão de Pessoas", "Gestão Operacional", "Gestão de Financiamentos", "Infraestrutura e Governança", "Outras Receitas"],
                                      index=["Gestão de Pessoas", "Gestão Operacional", "Gestão de Financiamentos", "Infraestrutura e Governança", "Outras Receitas"].index(row['gestao']) if row['gestao'] in ["Gestão de Pessoas", "Gestão Operacional", "Gestão de Financiamentos", "Infraestrutura e Governança", "Outras Receitas"] else 0)
        with col_ed2:
            nova_cat = st.text_input("Mudar Categoria para:", value=row['categoria'])
        
        c_btn1, c_btn2 = st.columns(2)
        with c_btn1:
            if st.button("💾 Salvar Alterações"):
                supabase.table("fluxo_caixa_ofx").update({"gestao": nova_gestao, "categoria": nova_cat}).eq("id", row['id']).execute()
                st.success("Alterado com sucesso! Recarregue a página.")
                st.rerun()
        with c_btn2:
            if st.button("🗑️ EXCLUIR REGISTRO"):
                supabase.table("fluxo_caixa_ofx").delete().eq("id", row['id']).execute()
                st.warning("Registro excluído!")
                st.rerun()

    st.divider()
    st.write("### Visualização Completa do Banco")
    st.dataframe(df_edit[['data_transacao', 'descricao_original', 'valor', 'categoria', 'gestao']], use_container_width=True)
