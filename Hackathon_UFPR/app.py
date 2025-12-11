import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import os

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Hackathon",
    page_icon="🥇",
    layout="wide"
)

# -----------------------------------------------------------------------------
# GENERAL SETTINGS AND FILES
# -----------------------------------------------------------------------------
# File mapping
FILES = {
    "In-person Course": "Hackathon_UFPR/Av_Disciplinas_Presenciais.csv",
    "Online Course": "Hackathon_UFPR/Av_Disciplinas_EAD.csv",
    "Program": "Hackathon_UFPR/Av_Curso.csv",
    "Institution": "Hackathon_UFPR/Av_Institucional.csv"
}

# -----------------------------------------------------------------------------
# MODULAR FUNCTIONS
# -----------------------------------------------------------------------------

@st.cache_data
def load_data(file_path):
    """
    Load data from the provided CSV file path.
    Fill missing values with 'No Response' for text columns.
    Try multiple encodings to avoid decoding errors.
    """
    # Fallback for testing: if the specific file is missing, try using 'Arquivo.csv'
    # Remove this logic in production if all files exist
    if not os.path.exists(file_path):
        if os.path.exists("Arquivo.csv"):
            # st.warning(f"File '{file_path}' not found. Using 'Arquivo.csv' for demonstration.")
            file_path = "Arquivo.csv"
        else:
            st.error(f"File not found: {file_path}")
            return None

    df = None
    # Try different encodings
    encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
    
    for encoding in encodings:
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            st.error(f"Error reading with encoding {encoding}: {e}")
            return None
            
    if df is None:
        st.error("Unable to read the file with the standard encodings.")
        return None

    try:
        # Basic null treatment
        # Fill nulls in object (text) columns with "No Response"
        object_cols = df.select_dtypes(include=['object']).columns
        df[object_cols] = df[object_cols].fillna('No Response')
        
        # Fill numeric nulls with 0 (adjust as needed)
        numeric_cols = df.select_dtypes(include=['number']).columns
        df[numeric_cols] = df[numeric_cols].fillna(0)
        
        return df
    except Exception as e:
        st.error(f"Error processing file: {e}")
        return None

def identify_questions(df):
    """
    Automatically identify which columns represent questions.
    Logic: treat 'object' (text) columns as categorical questions.
    Ignore columns that look like IDs or metadata if necessary.
    """
    if df is None:
        return []
    
    # Select text/category columns
    questions = df.select_dtypes(include=['object', 'category']).columns.tolist()
    
    # Optional: filter out columns that are not questions (e.g., ID, timestamp)
    # ignore_terms = ['id', 'data', 'time', 'nome']
    # questions = [q for q in questions if not any(term in q.lower() for term in ignore_terms)]
    
    return questions

def configure_sidebar():
    """
    Configure the sidebar with file selection and context-specific filters.
    Return the filtered DataFrame and the selected file name.
    """
    st.sidebar.header("Settings")
    
    # 1. File selection
    selected_file_name = st.sidebar.selectbox("Select evaluation", list(FILES.keys()))
    file_path = FILES[selected_file_name]
    
    # Carrega dados
    df = load_data(file_path)
    if df is None:
        return None, selected_file_name

    st.sidebar.markdown("---")
    st.sidebar.header("Filters")
    
    df_filtered = df.copy()
    
    # Helper to add a filter if the column exists
    def add_filter(df, col_name):
        if col_name in df.columns:
            options = sorted(df[col_name].astype(str).unique())
            selected = st.sidebar.multiselect(f"{col_name}", options, placeholder="Select...")
            if selected:
                return df[df[col_name].astype(str).isin(selected)]
        return df

    # 2. File-specific filters
    if selected_file_name in ["In-person Course", "Online Course"]:
        # Filters: Department, Program Area, Program, Course Name
        df_filtered = add_filter(df_filtered, "DEPARTAMENTO")
        df_filtered = add_filter(df_filtered, "SETOR_CURSO")
        df_filtered = add_filter(df_filtered, "CURSO")
        df_filtered = add_filter(df_filtered, "NOME_DISCIPLINA")
        
    elif selected_file_name == "Program":
        # Filters: Department, Program Area, Program
        df_filtered = add_filter(df_filtered, "DEPARTAMENTO")
        df_filtered = add_filter(df_filtered, "SETOR_CURSO")
        df_filtered = add_filter(df_filtered, "CURSO")
        
    elif selected_file_name == "Institution":
        # Filter: LOTACAO
        df_filtered = add_filter(df_filtered, "LOTACAO")
            
    return df_filtered, selected_file_name

def plot_bar(df, column_name, title=None, color_theme='blues', is_percent=False, show_labels=False):
    """
    Render a bar chart using Altair.
    """
    if column_name not in df.columns:
        return st.error(f"Column {column_name} not found.")

    # Prepara dados
    if is_percent:
        chart_data = df[column_name].value_counts(normalize=True).reset_index()
        chart_data.columns = ['Resposta', 'Valor']
        # Keep decimals and format the axis as percentage
        x_title = 'Percentage'
        x_format = '.0%'
        tooltip_format = '.1%'
    else:
        chart_data = df[column_name].value_counts().reset_index()
        chart_data.columns = ['Resposta', 'Valor']
        x_title = 'Count'
        x_format = 'd'
        tooltip_format = 'd'
    
    if title is None:
        title = f"Distribution: {column_name}"

    # Custom color logic
    def get_color(val):
        v = str(val).lower().strip()
        if v in ['concordo', 'sim']:
            return '#2ca02c' # Green (Tableau)
        elif v in ['discordo', 'não', 'nao']:
            return '#d62728' # Red (Tableau)
        else:
            return '#1f77b4' # Blue (Tableau)
            
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
# PAGES
# -----------------------------------------------------------------------------

def page_dashboard(df_filtered):
    # Detect whether the dataset is in long format
    cols_upper = [c.upper() for c in df_filtered.columns]
    is_long_format = 'PERGUNTA' in cols_upper and 'RESPOSTA' in cols_upper
    
    st.subheader("Response analysis")
    
    target_col = None
    df_chart = None
    
    if is_long_format:
        col_pergunta = next(c for c in df_filtered.columns if c.upper() == 'PERGUNTA')
        col_resposta = next(c for c in df_filtered.columns if c.upper() == 'RESPOSTA')
        
        questions = df_filtered[col_pergunta].unique()
        if len(questions) > 0:
            q1 = st.selectbox("Select question", questions, index=0, key='dash_q1')
            # Filter for the selected question
            df_chart = df_filtered[df_filtered[col_pergunta] == q1]
            target_col = col_resposta
        else:
            st.warning("No questions found in the filtered data.")
    else:
        questions = identify_questions(df_filtered)
        if not questions:
            st.warning("No text columns available.")
            return
        q1 = st.selectbox("Select column", questions, index=0, key='dash_q1')
        df_chart = df_filtered
        target_col = q1
        
    if df_chart is not None and not df_chart.empty:
        st.markdown("#### Engagement KPIs")
        
        # KPIs: Concordo, Discordo, Desconheço OR Sim, Não
        # Normalize to lowercase for matching
        series = df_chart[target_col].astype(str).str.lower().str.strip()
        total = len(series)
        
        if total > 0:
            # Check for Sim/Não versus Concordo/Discordo style answers
            unique_vals = set(series.unique())
            has_sim = 'sim' in unique_vals
            has_nao = 'não' in unique_vals or 'nao' in unique_vals
            has_concordo = any('concordo' in x for x in unique_vals)
            
            if (has_sim or has_nao) and not has_concordo:
                pct_sim = series.isin(['sim']).sum() / total
                pct_nao = series.isin(['não', 'nao']).sum() / total
                
                k1, k2 = st.columns(2)
                with k1: kpi_value("Yes", f"{pct_sim:.1%}")
                with k2: kpi_value("No", f"{pct_nao:.1%}")
            else:
                pct_concordo = series.str.contains('concordo').sum() / total
                pct_discordo = series.str.contains('discordo').sum() / total
                pct_desconheco = series.str.contains('desconheço').sum() / total
                
                k1, k2, k3 = st.columns(3)
                with k1: kpi_value("Agree", f"{pct_concordo:.1%}")
                with k2: kpi_value("Disagree", f"{pct_discordo:.1%}")
                with k3: kpi_value("Don't know", f"{pct_desconheco:.1%}")
        else:
            st.write("No data available for KPIs")
        
        st.markdown("---")
        
        # Percentage chart
        plot_bar(df_chart, target_col, color_theme='blues', is_percent=True)

def page_questions(df_filtered):
    # Detect whether the dataset is in long format (PERGUNTA/RESPOSTA columns)
    # Adjust casing as needed
    cols_upper = [c.upper() for c in df_filtered.columns]
    is_long_format = 'PERGUNTA' in cols_upper and 'RESPOSTA' in cols_upper
    
    if is_long_format:
        # Long-format logic (tidy data)
        # Locate the actual column names
        col_pergunta = next(c for c in df_filtered.columns if c.upper() == 'PERGUNTA')
        col_resposta = next(c for c in df_filtered.columns if c.upper() == 'RESPOSTA')
        
        unique_questions = df_filtered[col_pergunta].unique()
        
        st.markdown(f"Showing **{len(unique_questions)}** detected questions (long format).")
        st.markdown("---")
        
        for q in unique_questions:
            st.subheader(f"📌 {q}")
            
            # Filter data for the current question
            df_q = df_filtered[df_filtered[col_pergunta] == q]
            
            # Single chart (blue)
            st.caption("Response distribution")
            plot_bar(df_q, col_resposta, title="", color_theme='blues', is_percent=True, show_labels=True)
                
            st.divider()
            
    else:
        # Wide-format logic
        questions = identify_questions(df_filtered)
        
        if not questions:
            st.warning("No questions identified.")
            return

        st.markdown(f"Showing **{len(questions)}** identified columns.")
        st.markdown("---")

        for q in questions:
            st.subheader(f"📌 {q}")
            
            # Single chart (blue)
            st.caption("Overall distribution")
            plot_bar(df_filtered, q, title="", color_theme='blues', is_percent=True, show_labels=True)
                
            st.divider()

# -----------------------------------------------------------------------------
# MAIN EXECUTION
# -----------------------------------------------------------------------------

# Configure sidebar and load data (runs once)
df_filtered, file_name = configure_sidebar()

if df_filtered is not None:
    st.title("📊 Dashboard Hackathon")
    
    tab1, tab2 = st.tabs(["Question charts", "Main dashboard"])
    
    with tab1:
        page_questions(df_filtered)
        
    with tab2:
        page_dashboard(df_filtered)
