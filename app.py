import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_option_menu import option_menu

# Page Setup
st.set_page_config(
    page_title="Renewable Energy Dashboard", page_icon="⚡", layout="wide"
)

# Custom Yellow & Black Theme + Sidebar Flex CSS Injection
st.markdown(
    """
    <style>
    /* Configure Sidebar as vertical flexbox container */
    [data-testid="stSidebarUserContent"] {
        display: flex !important;
        flex-direction: column !important;
        height: calc(100vh - 60px) !important;
    }
    
    /* Spacer pushes elements below it to the bottom */
    .sidebar-spacer {
        flex-grow: 1 !important;
    }

    /* Primary buttons styling */
    div.stButton > button {
        background-color: #FFD700 !important;
        color: #000000 !important;
        font-weight: bold !important;
        border-radius: 6px !important;
        border: none !important;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #E6C200 !important;
        color: #000000 !important;
    }
    
    /* Input fields and containers styling */
    .stTextInput>div>div>input, .stSelectbox>div>div, .stTextArea>div>div>textarea, .stDateInput>div>div>input {
        background-color: #1A1A1A !important;
        color: #FFFFFF !important;
        border: 1px solid #333333 !important;
    }
    
    /* Metric Card Styling */
    [data-testid="stMetricValue"] {
        color: #FFD700 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
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

    # Clean leading/trailing spaces from string columns
    for df in [df_p, df_m, df_t]:
        if df is not None and not df.empty:
            df.columns = df.columns.str.strip()
            for col in df.select_dtypes(include="object").columns:
                df[col] = df[col].astype(str).str.strip()

    return df_p, df_m, df_t


try:
    df_projects, df_milestones, df_tasks = load_data()
except Exception as e:
    st.error(f"Failed to load data from Google Sheets: {e}")
    st.stop()

# Sidebar Navigation Header
with st.sidebar:
    # 1. Bold & Large Dashboard Title
    st.markdown(
        "<h1 style='color: #FFD700; font-size: 26px; font-weight: 900; margin-bottom: 0px; line-height: 1.2;'>⚡ RE Project Dashboard</h1>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # 2. Navigation Menu
    mode = option_menu(
        menu_title="Navigation",
        options=["Executive Summary", "Project Deep-Dive", "Management Portal"],
        icons=["speedometer2", "search", "gear"],
        menu_icon="compass",
        default_index=0,
        styles={
            "container": {
                "padding": "0!important",
                "background-color": "transparent",
            },
            "icon": {"color": "#FFD700", "font-size": "18px"},
            "nav-link": {
                "font-size": "14px",
                "text-align": "left",
                "margin": "4px 0px",
                "color": "#FFFFFF",
                "--hover-color": "#262626",
            },
            "nav-link-selected": {
                "background-color": "#FFD700",
                "color": "#000000",
                "font-weight": "bold",
            },
        },
    )

    # 3. Dynamic Spacer pushes profile & logout to bottom
    st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)

    # 4. User Info & Logout Button at BOTTOM
    st.markdown("---")
    st.markdown(f"### 👤 User: `{st.session_state['username']}`")
    if st.button("Log Out"):
        st.session_state["authenticated"] = False
        st.rerun()

# Executive Summary View
if mode == "Executive Summary":
    st.title("⚡ Portfolio Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Active Projects", len(df_projects))
    col2.metric("Total Tasks", len(df_tasks))

    completed_count = 0
    if "Status" in df_tasks.columns:
        completed_count = len(
            df_tasks[df_tasks["Status"].str.upper() == "COMPLETED"]
        )
    col3.metric("Completed Tasks", completed_count)

    st.markdown("---")
    st.dataframe(df_projects, use_container_width=True)

# Project Deep-Dive View
elif mode == "Project Deep-Dive":
    st.title("🔍 Project Deep-Dive & Task Updates")
    selected_proj = st.selectbox(
        "Select Project", df_projects["Project_Name"].unique()
    )

    p_tasks = df_tasks[
        df_tasks["Project_Name"].str.lower() == str(selected_proj).lower()
    ]

    if not p_tasks.empty:
        st.dataframe(p_tasks, use_container_width=True)
    else:
        st.info("No tasks recorded for this project yet.")

# Management Portal View
elif mode == "Management Portal":
    st.title("⚙️ Management Portal")

    # Display persistent success banner post-reload
    if "task_success_msg" in st.session_state:
        st.success(st.session_state.pop("task_success_msg"))

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

        col_start, col_due = st.columns(2)
        with col_start:
            start_date = st.date_input("Start Date")
        with col_due:
            due_date = st.date_input("Due Date")

        if st.form_submit_button("Submit Task"):
            if not desc or not assigned:
                st.warning(
                    "Please fill in both the Task Description and Assigned To fields."
                )
            elif due_date < start_date:
                st.error("Due Date cannot be earlier than Start Date.")
            else:
                try:
                    next_id = f"T{len(df_tasks) + 1:03d}"

                    new_row = pd.DataFrame(
                        [
                            {
                                "Task_ID": next_id,
                                "Project_Name": proj,
                                "Stage_Name": stage,
                                "Milestone_Name": ms,
                                "Task_Description": desc,
                                "Assigned_To": assigned,
                                "Start_Date": start_date.strftime("%d/%m/%Y"),
                                "Due_Date": due_date.strftime("%d/%m/%Y"),
                                "Status": "On-going",
                                "Risks_Issues_Remarks": "",
                            }
                        ]
                    )

                    updated_tasks = pd.concat(
                        [df_tasks, new_row], ignore_index=True
                    )
                    conn.update(worksheet="Tasks", data=updated_tasks)

                    st.cache_data.clear()

                    st.session_state["task_success_msg"] = (
                        f"✅ Task **{next_id}** has been successfully assigned to **{assigned}** and submitted!"
                    )
                    st.rerun()

                except Exception as err:
                    st.error(f"Error updating sheet: {err}")
