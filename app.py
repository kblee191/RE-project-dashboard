import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_option_menu import option_menu

# Page Setup
st.set_page_config(
    page_title="Renewable Energy Dashboard", page_icon="⚡", layout="wide"
)

# Custom Yellow & Black Theme + Adaptive CSS + Padding Fix
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 2rem !important;
    }
    [data-testid="stSidebarUserContent"] {
        display: flex !important;
        flex-direction: column !important;
        height: calc(100vh - 60px) !important;
    }
    .sidebar-spacer { flex-grow: 1 !important; }
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
    [data-testid="stMetricValue"] { color: #FFD700 !important; }
    .stProgress > div > div > div > div { background-color: #FFD700 !important; }
    .nav-link.active i, .nav-link-selected i, [class*="nav-link"][class*="active"] i {
        color: #000000 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Login Check
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    _, login_col, _ = st.columns([1, 1.2, 1])
    with login_col:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🔒 RE Dashboard Login")
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

    try:
        df_o = conn.read(worksheet="Milestone_Overrides", ttl=5)
    except Exception:
        df_o = pd.DataFrame(
            columns=[
                "Project_Name",
                "Milestone_Name",
                "Is_Overridden",
                "Override_Reason",
            ]
        )

    for df in [df_p, df_m, df_t, df_o]:
        if df is not None and not df.empty:
            df.columns = df.columns.astype(str).str.strip()
            # Fixed Pandas4Warning by passing a list to select_dtypes
            for col in df.select_dtypes(include=["object", "string"]).columns:
                df[col] = df[col].fillna("").astype(str).str.strip()

    return df_p, df_m, df_t, df_o


try:
    df_projects, df_milestones, df_tasks, df_overrides = load_data()
except Exception as e:
    st.error(f"Failed to load data from Google Sheets: {e}")
    st.stop()


def is_milestone_overridden(p_name, ms_name):
    """Helper to check if a milestone is overridden for a project."""
    if df_overrides is None or df_overrides.empty:
        return False, ""

    match = df_overrides[
        (
            df_overrides["Project_Name"].astype(str).str.strip().str.lower()
            == str(p_name).strip().lower()
        )
        & (
            df_overrides["Milestone_Name"].astype(str).str.strip().str.lower()
            == str(ms_name).strip().lower()
        )
        & (df_overrides["Is_Overridden"].astype(str).str.upper() == "TRUE")
    ]

    if not match.empty:
        reason = match.iloc[0].get("Override_Reason", "No reason provided")
        return True, str(reason)
    return False, ""


sorted_project_dropdown = (
    sorted(df_projects["Project_Name"].unique(), key=lambda x: str(x).lower())
    if "Project_Name" in df_projects.columns
    else []
)

# Sidebar Navigation Header
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 48px; line-height: 1;">⚡</span>
            <div style="font-size: 24px; font-weight: 900; line-height: 1.15;">
                RE Project Dashboard
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    mode = option_menu(
        menu_title="Navigation",
        options=[
            "Summary",
            "Project Tracking",
            "Create New Project",
            "Add & Manage Task",
        ],
        icons=["speedometer2", "search", "plus-circle", "check2-square"],
        menu_icon="compass",
        default_index=0,
        styles={
            "container": {
                "padding": "0!important",
                "background-color": "transparent",
            },
            "icon": {"font-size": "18px"},
            "nav-link": {
                "font-size": "14px",
                "text-align": "left",
                "margin": "4px 0px",
                "--hover-color": "rgba(128, 128, 128, 0.15)",
            },
            "nav-link-selected": {
                "background-color": "#FFD700",
                "color": "#000000",
                "font-weight": "bold",
            },
        },
    )

    st.markdown('<div class="sidebar-spacer"></div>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"### 👤 User: `{st.session_state['username']}`")
    if st.button("Log Out"):
        st.session_state["authenticated"] = False
        st.rerun()

# Summary View
if mode == "Summary":
    st.title("📃 Portfolio Overview")

    if "Stage_Order" in df_milestones.columns:
        ordered_stages = (
            df_milestones.sort_values("Stage_Order")["Stage_Name"]
            .unique()
            .tolist()
        )
    else:
        ordered_stages = df_milestones["Stage_Name"].unique().tolist()

    summary_rows = []
    completed_projects_count = 0

    for idx, p_row in df_projects.iterrows():
        p_name = p_row.get("Project_Name", "")

        p_tasks = df_tasks[
            df_tasks["Project_Name"].astype(str).str.strip().str.lower()
            == str(p_name).strip().lower()
        ]

        total_t = len(p_tasks)
        completed_t = (
            len(
                p_tasks[
                    p_tasks["Status"].astype(str).str.strip().str.upper() == "COMPLETED"
                ]
            )
            if total_t > 0
            else 0
        )
        ongoing_t = (
            len(
                p_tasks[
                    p_tasks["Status"].astype(str).str.strip().str.upper() == "ON-GOING"
                ]
            )
            if total_t > 0
            else 0
        )

        stage_percentages = []
        current_stage = None

        for stg in ordered_stages:
            stg_ms = df_milestones[
                df_milestones["Stage_Name"].astype(str).str.strip() == str(stg).strip()
            ]["Milestone_Name"].unique()

            ms_percentages = []

            for ms_name in stg_ms:
                overridden, _ = is_milestone_overridden(p_name, ms_name)
                if overridden:
                    m_pct = 100.0
                else:
                    ms_tasks = p_tasks[
                        p_tasks["Milestone_Name"].astype(str).str.strip().str.lower()
                        == str(ms_name).strip().lower()
                    ]
                    m_total = len(ms_tasks)
                    m_completed = (
                        len(
                            ms_tasks[
                                ms_tasks["Status"].astype(str).str.strip().str.upper()
                                == "COMPLETED"
                            ]
                        )
                        if m_total > 0
                        else 0
                    )
                    m_pct = (
                        (m_completed / m_total * 100.0) if m_total > 0 else 0.0
                    )

                ms_percentages.append(m_pct)

            stg_pct = (
                (sum(ms_percentages) / len(ms_percentages))
                if ms_percentages
                else 0.0
            )
            stage_percentages.append(stg_pct)

            if stg_pct < 100.0 and current_stage is None:
                current_stage = stg

        overall_pct = (
            (sum(stage_percentages) / len(stage_percentages))
            if stage_percentages
            else 0.0
        )

        if overall_pct >= 100.0 and len(ordered_stages) > 0:
            completed_projects_count += 1
            current_stage = "Completed"
        elif current_stage is None:
            current_stage = (
                ordered_stages[0] if ordered_stages else "Not Started"
            )

        p_dict = p_row.to_dict()
        p_dict["Current Stage"] = current_stage
        p_dict["Total Tasks"] = total_t
        p_dict["Completed Tasks"] = completed_t
        p_dict["Ongoing Tasks"] = ongoing_t
        p_dict["Completion %"] = round(overall_pct, 1)

        summary_rows.append(p_dict)

    df_summary = pd.DataFrame(summary_rows)

    col1, col2 = st.columns(2)
    col1.metric("Number of Projects", len(df_projects))
    col2.metric("Completed Projects", completed_projects_count)

    st.markdown("---")

    st.dataframe(
        df_summary,
        use_container_width=True,
        column_config={
            "Completion %": st.column_config.ProgressColumn(
                "Completion %",
                help="Overall project completion progress",
                format="%.1f%%",
                min_value=0,
                max_value=100,
            ),
        },
        hide_index=True,
    )

# Project Tracking View
elif mode == "Project Tracking":
    st.title("🔍 Project Progress Tracking")
    selected_proj = st.selectbox("Select Project", sorted_project_dropdown)

    proj_tasks = df_tasks[
        df_tasks["Project_Name"].astype(str).str.strip().str.lower()
        == str(selected_proj).strip().lower()
    ]

    if "Stage_Order" in df_milestones.columns:
        unique_stages = (
            df_milestones.sort_values("Stage_Order")["Stage_Name"]
            .unique()
            .tolist()
        )
    else:
        unique_stages = df_milestones["Stage_Name"].unique().tolist()

    stage_data = {}
    stage_percentages = []

    for stage_name in unique_stages:
        stg_milestones = df_milestones[
            df_milestones["Stage_Name"].astype(str).str.strip() == str(stage_name).strip()
        ]["Milestone_Name"].unique()

        ms_data = {}
        ms_percentages = []

        for ms_name in stg_milestones:
            overridden, reason = is_milestone_overridden(selected_proj, ms_name)

            if overridden:
                ms_pct = 100.0
                total_t = 0
                completed_t = 0
                ms_tasks = pd.DataFrame()
            else:
                ms_tasks = proj_tasks[
                    proj_tasks["Milestone_Name"].astype(str).str.strip().str.lower()
                    == str(ms_name).strip().lower()
                ]
                total_t = len(ms_tasks)
                completed_t = (
                    len(
                        ms_tasks[
                            ms_tasks["Status"].astype(str).str.strip().str.upper()
                            == "COMPLETED"
                        ]
                    )
                    if total_t > 0
                    else 0
                )
                ms_pct = (completed_t / total_t * 100) if total_t > 0 else 0.0

            ms_percentages.append(ms_pct)

            ms_data[ms_name] = {
                "pct": ms_pct,
                "total": total_t,
                "completed": completed_t,
                "tasks": ms_tasks,
                "overridden": overridden,
                "reason": reason,
            }

        stg_pct = (
            (sum(ms_percentages) / len(ms_percentages))
            if ms_percentages
            else 0.0
        )
        stage_percentages.append(stg_pct)

        stage_data[stage_name] = {"pct": stg_pct, "milestones": ms_data}

    overall_project_pct = (
        (sum(stage_percentages) / len(stage_percentages))
        if stage_percentages
        else 0.0
    )

    st.markdown(f"### Overall Project Completion: **{overall_project_pct:.1f}%**")
    st.progress(overall_project_pct / 100.0)
    st.markdown("---")

    for stage_name, s_info in stage_data.items():
        stg_pct = s_info["pct"]

        col_stg_title, col_stg_val = st.columns([4, 1])
        with col_stg_title:
            st.markdown(f"#### 📌 {stage_name}")
        with col_stg_val:
            st.markdown(f"**{stg_pct:.1f}% Complete**")

        st.progress(stg_pct / 100.0)

        for ms_name, m_info in s_info["milestones"].items():
            ms_pct = m_info["pct"]
            t_df = m_info["tasks"]

            if m_info["overridden"]:
                expander_title = (
                    f"🎯 {ms_name} — 100% (⚡ Overridden by Lead)"
                )
            else:
                expander_title = f"🎯 {ms_name} — {ms_pct:.0f}% ({m_info['completed']}/{m_info['total']} Tasks Completed)"

            with st.expander(expander_title):
                st.progress(ms_pct / 100.0)

                if m_info["overridden"]:
                    st.info(
                        f"**Milestone Overridden as Complete.**\n\n**Reason:** {m_info['reason']}"
                    )
                elif not t_df.empty:
                    display_cols = [
                        c
                        for c in [
                            "Task_ID",
                            "Task_Description",
                            "Assigned_To",
                            "Start_Date",
                            "Due_Date",
                            "Status",
                            "Risks_Issues_Remarks",
                        ]
                        if c in t_df.columns
                    ]
                    st.dataframe(
                        t_df[display_cols],
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.caption("No tasks created under this milestone yet.")

        st.markdown("---")

# Create New Project View
elif mode == "Create New Project":
    st.title("➕ Create New Project")

    if "project_success_msg" in st.session_state:
        st.success(st.session_state.pop("project_success_msg"))

    next_project_id = f"P{len(df_projects) + 1:03d}"

    date_col = next(
        (c for c in df_projects.columns if "target" in c.lower()),
        "Target_Completion_Date",
    )

    with st.form("add_project_form"):
        st.text_input("Project ID", value=next_project_id, disabled=True)
        proj_name = st.text_input("Project Name")
        capacity = st.text_input("Capacity (e.g., 50 MWp)")
        proj_lead = st.text_input("Project Lead")
        target_date = st.date_input("Target Completion Date")

        if st.form_submit_button("Create Project"):
            if not proj_name or not capacity or not proj_lead:
                st.warning("Please fill in all required fields.")
            else:
                try:
                    new_project_dict = {
                        "Project_ID": next_project_id,
                        "Project_Name": proj_name,
                        "Capacity": capacity,
                        "Project_Lead": proj_lead,
                        date_col: target_date.strftime("%d/%m/%Y"),
                    }

                    new_project_row = pd.DataFrame([new_project_dict])

                    updated_projects = pd.concat(
                        [df_projects, new_project_row], ignore_index=True
                    )[df_projects.columns]

                    conn.update(worksheet="Projects", data=updated_projects)

                    st.cache_data.clear()

                    st.session_state["project_success_msg"] = (
                        f"✅ Project **{proj_name}** (`{next_project_id}`) has been created successfully!"
                    )
                    st.rerun()

                except Exception as err:
                    st.error(f"Error updating Projects sheet: {err}")

# Add & Manage Task View
elif mode == "Add & Manage Task":
    st.title("⚙️ Task Management")

    if "task_success_msg" in st.session_state:
        st.success(st.session_state.pop("task_success_msg"))

    proj = st.selectbox("Project", sorted_project_dropdown)
    stage = st.selectbox("Stage", df_milestones["Stage_Name"].unique())

    filtered_ms = df_milestones[
        df_milestones["Stage_Name"].astype(str).str.strip() == str(stage).strip()
    ]["Milestone_Name"].unique()

    ms = st.selectbox("Milestone", filtered_ms)

    st.markdown("---")

    tab_add, tab_update, tab_override = st.tabs(
        ["➕ Add New Task", "📝 Update Task Status", "⚡ Override Milestone"]
    )

    with tab_add:
        with st.form("add_task_details_form"):
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
                                    "Start_Date": start_date.strftime(
                                        "%d/%m/%Y"
                                    ),
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
                            f"✅ Task **{next_id}** has been successfully created and assigned to **{assigned}**!"
                        )
                        st.rerun()

                    except Exception as err:
                        st.error(f"Error updating sheet: {err}")

    with tab_update:
        matching_tasks = df_tasks[
            (
                df_tasks["Project_Name"].astype(str).str.strip().str.lower()
                == str(proj).strip().lower()
            )
            & (
                df_tasks["Milestone_Name"].astype(str).str.strip().str.lower()
                == str(ms).strip().lower()
            )
        ]

        if matching_tasks.empty:
            st.info(
                f"No tasks currently exist under **{ms}** for project **{proj}**."
            )
        else:
            task_options = {
                f"{row['Task_ID']} - {row['Task_Description']} (Assigned to: {row['Assigned_To']})": row[
                    "Task_ID"
                ]
                for _, row in matching_tasks.iterrows()
            }

            selected_task_label = st.selectbox(
                "Select Task to Update", list(task_options.keys())
            )
            selected_task_id = task_options[selected_task_label]

            current_row = matching_tasks[
                matching_tasks["Task_ID"].astype(str) == str(selected_task_id)
            ].iloc[0]

            status_choices = ["On-going", "Completed", "Cancelled"]
            current_status = str(current_row.get("Status", "On-going"))
            status_index = (
                status_choices.index(current_status)
                if current_status in status_choices
                else 0
            )

            with st.form("update_status_form"):
                new_status = st.selectbox(
                    "Task Status", status_choices, index=status_index
                )
                new_remarks = st.text_area(
                    "Risks / Issues / Remarks",
                    value=str(
                        current_row.get("Risks_Issues_Remarks", "")
                    ).replace("nan", ""),
                )

                if st.form_submit_button("Update Task Status"):
                    try:
                        task_idx = df_tasks[
                            df_tasks["Task_ID"].astype(str) == str(selected_task_id)
                        ].index[0]
                        df_tasks.loc[task_idx, "Status"] = new_status
                        df_tasks.loc[task_idx, "Risks_Issues_Remarks"] = (
                            new_remarks
                        )

                        conn.update(worksheet="Tasks", data=df_tasks)

                        st.cache_data.clear()

                        st.session_state["task_success_msg"] = (
                            f"✅ Task **{selected_task_id}** updated to **{new_status}**!"
                        )
                        st.rerun()

                    except Exception as err:
                        st.error(f"Error updating task status: {err}")

    with tab_override:
        is_currently_overridden, current_reason = is_milestone_overridden(
            proj, ms
        )

        st.markdown(
            f"Set override status for **{ms}** on project **{proj}**:"
        )

        with st.form("override_milestone_form"):
            override_toggle = st.checkbox(
                "Mark Milestone as Fully Completed (Override)",
                value=is_currently_overridden,
            )
            override_reason_text = st.text_area(
                "Reason for Override",
                value=current_reason,
                placeholder="e.g., Pre-completed prior to project start or milestone not applicable.",
            )

            if st.form_submit_button("Save Override Setting"):
                try:
                    df_o_clean = df_overrides.copy()

                    # Drop existing override record if present (safely cast to string)
                    df_o_clean = df_o_clean[
                        ~(
                            (
                                df_o_clean["Project_Name"]
                                .astype(str)
                                .str.strip()
                                .str.lower()
                                == str(proj).strip().lower()
                            )
                            & (
                                df_o_clean["Milestone_Name"]
                                .astype(str)
                                .str.strip()
                                .str.lower()
                                == str(ms).strip().lower()
                            )
                        )
                    ]

                    if override_toggle:
                        new_o_row = pd.DataFrame(
                            [
                                {
                                    "Project_Name": proj,
                                    "Milestone_Name": ms,
                                    "Is_Overridden": "TRUE",
                                    "Override_Reason": override_reason_text,
                                }
                            ]
                        )
                        df_o_clean = pd.concat(
                            [df_o_clean, new_o_row], ignore_index=True
                        )

                    conn.update(
                        worksheet="Milestone_Overrides", data=df_o_clean
                    )

                    st.cache_data.clear()

                    st.session_state["task_success_msg"] = (
                        f"✅ Milestone **{ms}** override updated successfully!"
                    )
                    st.rerun()

                except Exception as err:
                    st.error(f"Error updating Milestone_Overrides sheet: {err}")
