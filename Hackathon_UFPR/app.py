import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import os

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Hackathon",
    page_icon="🥇",
    layout="wide"
)

st.write("Arquivos na raiz do deploy:", os.listdir("."))

# -----------------------------------------------------------------------------
# CONFIGURAÇÕES GERAIS E ARQUIVOS
# -----------------------------------------------------------------------------
# Mapeamento dos arquivos
FILES = {
    "Disciplina Presencial": "Hackathon_UFPR/Av_Disciplinas_Presenciais.csv",
    "Disciplina EAD": "Av_Disciplinas_EAD.csv",
    "Curso": "Av_Curso.csv",
    "Instituição": "Av_Institucional.csv"
}

# -----------------------------------------------------------------------------
# FUNÇÕES MODULARES
# -----------------------------------------------------------------------------

@st.cache_data
def load_data(file_path):
    """
    Carrega os dados do arquivo CSV especificado.
    Trata valores nulos preenchendo com 'Não Respondido' para colunas de texto.
    Tenta diferentes encodings para evitar erros de leitura.
    """
    # Fallback para teste se o arquivo específico não existir, tenta usar 'Arquivo.csv'
    # Remover essa lógica em produção se os arquivos existirem
    if not os.path.exists(file_path):
        if os.path.exists("Arquivo.csv"):
            # st.warning(f"Arquivo '{file_path}' não encontrado. Usando 'Arquivo.csv' para demonstração.")
            file_path = "Arquivo.csv"
        else:
            st.error(f"Arquivo não encontrado: {file_path}")
            return None

    df = None
    # Tenta ler com diferentes encodings
    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    
    for encoding in encodings:
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            st.error(f"Erro ao ler com encoding {encoding}: {e}")
            return None
            
    if df is None:
        st.error("Não foi possível ler o arquivo com nenhum dos encodings padrões.")
        return None

    try:
        # Tratamento básico de nulos
        # Preenche nulos em colunas de objeto (texto) com "Não Respondido"
        object_cols = df.select_dtypes(include=['object']).columns
        df[object_cols] = df[object_cols].fillna('Não Respondido')
        
        # Preenche nulos numéricos com 0 (ajuste conforme necessidade)
        numeric_cols = df.select_dtypes(include=['number']).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        return None

def identify_questions(df):
    """
    Identifica automaticamente quais colunas são perguntas.
    Lógica: Considera colunas do tipo 'object' (texto) como perguntas categóricas.
    Ignora colunas que parecem ser IDs ou Metadados se necessário.
    """
    if df is None:
        return []
    
    # Seleciona colunas de texto/categoria
    questions = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    # Opcional: Filtrar colunas que não são perguntas (ex: ID, Timestamp)
    # ignore_terms = ['id', 'data', 'time', 'nome']
    # questions = [q for q in questions if not any(term in q.lower() for term in ignore_terms)]
    
    return questions

def configure_sidebar():
    """
    Configura a barra lateral com seleção de arquivo e filtros específicos.
    Retorna o DataFrame filtrado e o nome do arquivo selecionado.
    """
    st.sidebar.header("Configurações")
    
    # 1. Seleção de Arquivo
    selected_file_name = st.sidebar.selectbox("Selecione a Avaliação", list(FILES.keys()))
    file_path = FILES[selected_file_name]
    
    # Carrega dados
    df = load_data(file_path)
    if df is None:
        return None, selected_file_name

    st.sidebar.markdown("---")
    st.sidebar.header("Filtros")
    
    df_filtered = df.copy()
    
    # Helper para criar filtro se a coluna existir
    def add_filter(df, col_name):
        if col_name in df.columns:
            options = sorted(df[col_name].astype(str).unique())
            selected = st.sidebar.multiselect(f"{col_name}", options, placeholder="Selecione...")
            if selected:
                return df[df[col_name].astype(str).isin(selected)]
        return df

    # 2. Filtros Específicos por Tipo de Arquivo
    if selected_file_name in ["Disciplina Presencial", "Disciplina EAD"]:
        # Filtros: Departamento, Setor Curso, Curso, Nome da Disciplina
        df_filtered = add_filter(df_filtered, "DEPARTAMENTO")
        df_filtered = add_filter(df_filtered, "SETOR_CURSO")
        df_filtered = add_filter(df_filtered, "CURSO")
        df_filtered = add_filter(df_filtered, "NOME_DISCIPLINA")
        
    elif selected_file_name == "Curso":
        # Filtros: Departamento, Setor Curso, Curso
        df_filtered = add_filter(df_filtered, "DEPARTAMENTO")
        df_filtered = add_filter(df_filtered, "SETOR_CURSO")
        df_filtered = add_filter(df_filtered, "CURSO")
        
    elif selected_file_name == "Instituição":
        # Filtro: Lotação
        df_filtered = add_filter(df_filtered, "LOTACAO")
            
    return df_filtered, selected_file_name

def plot_bar(df, column_name, title=None, color_theme='blues', is_percent=False, show_labels=False):
    """
    Gera um gráfico de barras usando Altair.
    """
    if column_name not in df.columns:
        return st.error(f"Coluna {column_name} não encontrada.")

    # Prepara dados
    if is_percent:
        chart_data = df[column_name].value_counts(normalize=True).reset_index()
        chart_data.columns = ['Resposta', 'Valor']
        # Multiplica por 100 para ficar mais legível se quiser, mas Altair formata bem com .0%
        # Vamos manter decimal e formatar no eixo
        x_title = 'Porcentagem'
        x_format = '.0%'
        tooltip_format = '.1%'
    else:
        chart_data = df[column_name].value_counts().reset_index()
        chart_data.columns = ['Resposta', 'Valor']
        x_title = 'Quantidade'
        x_format = 'd'
        tooltip_format = 'd'
    
    if title is None:
        title = f"Distribuição: {column_name}"

    # Lógica de Cores Personalizada
    def get_color(val):
        v = str(val).lower().strip()
        if v in ['concordo', 'sim']:
            return '#2ca02c' # Verde (Tableau Green)
        elif v in ['discordo', 'não', 'nao']:
            return '#d62728' # Vermelho (Tableau Red)
        else:
            return '#1f77b4' # Azul (Tableau Blue)
            
    chart_data['Color'] = chart_data['Resposta'].apply(get_color)

    base = alt.Chart(chart_data).encode(
        y=alt.Y('Resposta', sort='-x', title='Resposta'),
    )

    bars = base.mark_bar().encode(
        x=alt.X('Valor', title=x_title, axis=alt.Axis(format=x_format)),
        tooltip=['Resposta', alt.Tooltip('Valor', format=tooltip_format, title=x_title)],
        color=alt.Color('Color', scale=None, legend=None)
    )

    chart = bars

    if show_labels:
        text = base.mark_text(
            align='right',
            baseline='middle',
            dx=-3,  # Nudges text to left so it is inside the bar
            color='white'
        ).encode(
            x=alt.X('Valor'),
            text=alt.Text('Valor', format=tooltip_format)
        )
        chart = (bars + text)

    chart = chart.properties(
        title=title,
        height=300
    )
    
    st.altair_chart(chart, use_container_width=True)

def kpi_value(label, value, delta=None):
    """
    Exibe um KPI estilizado.
    """
    st.metric(label=label, value=value, delta=delta)

# -----------------------------------------------------------------------------
# PÁGINAS
# -----------------------------------------------------------------------------

def page_dashboard(df_filtered):
    # Verifica formato Longo
    cols_upper = [c.upper() for c in df_filtered.columns]
    is_long_format = 'PERGUNTA' in cols_upper and 'RESPOSTA' in cols_upper
    
    st.subheader("Análise de Respostas")
    
    target_col = None
    df_chart = None
    
    if is_long_format:
        col_pergunta = next(c for c in df_filtered.columns if c.upper() == 'PERGUNTA')
        col_resposta = next(c for c in df_filtered.columns if c.upper() == 'RESPOSTA')
        
        questions = df_filtered[col_pergunta].unique()
        if len(questions) > 0:
            q1 = st.selectbox("Selecione a Pergunta", questions, index=0, key='dash_q1')
            # Filtra para a pergunta selecionada
            df_chart = df_filtered[df_filtered[col_pergunta] == q1]
            target_col = col_resposta
        else:
            st.warning("Nenhuma pergunta encontrada nos dados filtrados.")
    else:
        questions = identify_questions(df_filtered)
        if not questions:
            st.warning("Sem colunas de texto.")
            return
        q1 = st.selectbox("Selecione a Variável", questions, index=0, key='dash_q1')
        df_chart = df_filtered
        target_col = q1
        
    if df_chart is not None and not df_chart.empty:
        st.markdown("#### KPIs de Adesão")
        
        # KPIs: Concordo, Discordo, Desconheço OU Sim, Não
        # Normaliza para minúsculo para busca
        series = df_chart[target_col].astype(str).str.lower().str.strip()
        total = len(series)
        
        if total > 0:
            # Verifica presença de Sim/Não vs Concordo/Discordo
            unique_vals = set(series.unique())
            has_sim = 'sim' in unique_vals
            has_nao = 'não' in unique_vals or 'nao' in unique_vals
            has_concordo = any('concordo' in x for x in unique_vals)
            
            if (has_sim or has_nao) and not has_concordo:
                pct_sim = series.isin(['sim']).sum() / total
                pct_nao = series.isin(['não', 'nao']).sum() / total
                
                k1, k2 = st.columns(2)
                with k1: kpi_value("Sim", f"{pct_sim:.1%}")
                with k2: kpi_value("Não", f"{pct_nao:.1%}")
            else:
                pct_concordo = series.str.contains('concordo').sum() / total
                pct_discordo = series.str.contains('discordo').sum() / total
                pct_desconheco = series.str.contains('desconheço').sum() / total
                
                k1, k2, k3 = st.columns(3)
                with k1: kpi_value("Concordo", f"{pct_concordo:.1%}")
                with k2: kpi_value("Discordo", f"{pct_discordo:.1%}")
                with k3: kpi_value("Desconheço", f"{pct_desconheco:.1%}")
        else:
            st.write("Sem dados para KPIs")
        
        st.markdown("---")
        
        # Gráfico de Porcentagem
        plot_bar(df_chart, target_col, color_theme='blues', is_percent=True)

def page_questions(df_filtered):
    # Verifica se o dataset está no formato longo (com colunas PERGUNTA e RESPOSTA)
    # Ajuste para maiúsculas/minúsculas conforme necessário
    cols_upper = [c.upper() for c in df_filtered.columns]
    is_long_format = 'PERGUNTA' in cols_upper and 'RESPOSTA' in cols_upper
    
    if is_long_format:
        # Lógica para formato Longo (Tidy Data)
        # Identifica os nomes reais das colunas
        col_pergunta = next(c for c in df_filtered.columns if c.upper() == 'PERGUNTA')
        col_resposta = next(c for c in df_filtered.columns if c.upper() == 'RESPOSTA')
        
        unique_questions = df_filtered[col_pergunta].unique()
        
        st.markdown(f"Exibindo análise para **{len(unique_questions)}** perguntas encontradas (Formato Longo).")
        st.markdown("---")
        
        for q in unique_questions:
            st.subheader(f"📌 {q}")
            
            # Filtra dados apenas para essa pergunta
            df_q = df_filtered[df_filtered[col_pergunta] == q]
            
            # Apenas um gráfico (azul)
            st.caption("Distribuição das Respostas")
            plot_bar(df_q, col_resposta, title="", color_theme='blues', is_percent=True, show_labels=True)
                
            st.divider()
            
    else:
        # Lógica Original (Formato Largo / Wide)
        questions = identify_questions(df_filtered)
        
        if not questions:
            st.warning("Nenhuma pergunta identificada.")
            return

        st.markdown(f"Exibindo análise para **{len(questions)}** colunas identificadas.")
        st.markdown("---")

        for q in questions:
            st.subheader(f"📌 {q}")
            
            # Apenas um gráfico (azul)
            st.caption("Distribuição Geral")
            plot_bar(df_filtered, q, title="", color_theme='blues', is_percent=True, show_labels=True)
                
            st.divider()

# -----------------------------------------------------------------------------
# EXECUÇÃO PRINCIPAL
# -----------------------------------------------------------------------------

# Configuração da Sidebar e Carregamento de Dados (Executado uma vez)
df_filtered, file_name = configure_sidebar()

if df_filtered is not None:
    st.title("📊 Dashboard Hackathon")
    
    tab1, tab2 = st.tabs(["Gráficos por Pergunta", "Dashboard Principal"])
    
    with tab1:
        page_questions(df_filtered)
        
    with tab2:
        page_dashboard(df_filtered)
