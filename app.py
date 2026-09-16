import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Page Setup
st.set_page_config(
    page_title="Renewable Energy Dashboard", page_icon="⚡", layout="wide"
)

# Login Check
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Renewable Energy Dashboard Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log In"):
            valid_users = st.secrets.get("passwords", {})
            if username in valid_users and valid_users[username] == password:
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Invalid Username or Password")
    st.stop()

# Data Connection
conn = st.connection("gsheets", type=GSheetsConnection)


@st.cache_data(ttl=5)
def load_data():
    df_p = conn.read(worksheet="Projects", ttl=5)
    df_m = conn.read(worksheet="Milestones_Master", ttl=5)
    df_t = conn.read(worksheet="Tasks", ttl=5)
    return df_p, df_m, df_t


try:
    df_projects, df_milestones, df_tasks = load_data()
except Exception as e:
    st.error(f"Failed to load data from Google Sheets: {e}")
    st.stop()

# Navigation
st.sidebar.title(f"👤 User: {st.session_state['username']}")
if st.sidebar.button("Log Out"):
    st.session_state["authenticated"] = False
    st.rerun()

mode = st.sidebar.radio(
    "Navigation",
    [
        "📊 Executive Summary",
        "🔍 Project Deep-Dive & Tasks",
        "⚙️ Management Portal",
    ],
)

# Executive Summary View
if mode == "📊 Executive Summary":
    st.title("⚡ Portfolio Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Active Projects", len(df_projects))
    col2.metric("Total Tasks", len(df_tasks))

    completed_count = 0
    if "Status" in df_tasks.columns:
        completed_count = len(
            df_tasks[df_tasks["Status"].astype(str).str.upper() == "COMPLETED"]
        )
    col3.metric("Completed Tasks", completed_count)

    st.markdown("---")
    st.dataframe(df_projects, use_container_width=True)

# Project Deep-Dive View
elif mode == "🔍 Project Deep-Dive & Tasks":
    st.title("🔍 Project Deep-Dive & Task Updates")
    selected_proj = st.selectbox(
        "Select Project", df_projects["Project_Name"].unique()
    )
    p_tasks = df_tasks[df_tasks["Project_Name"] == selected_proj]

    if not p_tasks.empty:
        st.dataframe(p_tasks, use_container_width=True)
    else:
        st.info("No tasks recorded for this project yet.")

# Management Portal View
elif mode == "⚙️ Management Portal":
    st.title("⚙️ Management Portal")
    st.subheader("Add New Task")
    with st.form("add_task_form"):
        proj = st.selectbox(
            "Project", df_projects["Project_Name"].unique()
        )
        stage = st.selectbox(
            "Stage", df_milestones["Stage_Name"].unique()
        )
        filtered_ms = df_milestones[
            df_milestones["Stage_Name"] == stage
        ]["Milestone_Name"].unique()
        ms = st.selectbox("Milestone", filtered_ms)
        desc = st.text_area("Task Description")
        assigned = st.text_input("Assigned To")
        if st.form_submit_button("Submit Task"):
            st.success("Task submitted!")
