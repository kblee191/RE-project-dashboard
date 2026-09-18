import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_option_menu import option_menu

# ==========================================
# 1. PAGE SETUP & THEMING
# ==========================================
st.set_page_config(
    page_title="Renewable Energy Dashboard", page_icon="⚡", layout="wide"
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 3rem !important;
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

# ==========================================
# 2. AUTHENTICATION
# ==========================================
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

# ==========================================
# 3. DATA CONNECTION & LOADING
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)


def load_data():
    df_p = conn.read(worksheet="Projects", ttl=0)
    df_m = conn.read(worksheet="Milestones_Master", ttl=0)
    df_t = conn.read(worksheet="Tasks", ttl=0)

    try:
        df_cfg = conn.read(worksheet="Project_Milestone_Config", ttl=0)
    except Exception:
        df_cfg = pd.DataFrame(
            columns=[
                "Project_Name",
                "Stage_Name",
                "Milestone_Name",
                "Status",
                "Notes_Reason",
            ]
        )

    # Clean string types across all dataframes
    for df in [df_p, df_m, df_t, df_cfg]:
        if df is not None and not df.empty:
            df.columns = [str(col).strip() for col in df.columns]
            for col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.strip()

    return df_p, df_m, df_t, df_cfg


try:
    df_projects, df_milestones, df_tasks, df_configs = load_data()
except Exception as e:
    st.error(f"Failed to load data from Google Sheets: {e}")
    st.stop()

sorted_projects = (
    sorted(df_projects["Project_Name"].unique(), key=lambda x: str(x).lower())
    if "Project_Name" in df_projects.columns and not df_projects.empty
    else []
)

# ==========================================
# 4. PROGRESS CALCULATION ENGINE
# ==========================================
def calculate_project_metrics(p_name):
    """Calculates completion percentages based on master + custom milestones."""
    p_tasks = df_tasks[
        df_tasks["Project_Name"].astype(str).str.strip().str.lower()
        == str(p_name).strip().lower()
    ]
    p_configs = df_configs[
        df_configs["Project_Name"].astype(str).str.strip().str.lower()
        == str(p_name).strip().lower()
    ]

    if "Stage_Order" in df_milestones.columns:
        ordered_stages = (
            df_milestones.sort_values("Stage_Order")["Stage_Name"]
            .unique()
            .tolist()
        )
    else:
        ordered_stages = df_milestones["Stage_Name"].unique().tolist()

    stage_summary = {}
    valid_stage_pcts = []
    current_stage = None

    for stg in ordered_stages:
        stg_ms_master = df_milestones[
            df_milestones["Stage_Name"].astype(str).str.strip() == str(stg).strip()
        ]["Milestone_Name"].unique().tolist()

        # Combine master milestones with custom milestones in p_configs for this stage
        p_stg_cfgs = p_configs[
            p_configs["Stage_Name"].astype(str).str.strip().str.lower()
            == str(stg).strip().lower()
        ]

        stg_ms_all = list(stg_ms_master)
        for _, cfg_r in p_stg_cfgs.iterrows():
            m_n = cfg_r.get("Milestone_Name", "").strip()
            if m_n and m_n.lower() not in [x.lower() for x in stg_ms_all]:
                stg_ms_all.append(m_n)

        ms_summary = {}
        applicable_ms_pcts = []

        for ms_name in stg_ms_all:
            cfg_row = p_configs[
                p_configs["Milestone_Name"].astype(str).str.strip().str.lower()
                == str(ms_name).strip().lower()
            ]

            status = "Active"
            reason = ""
            if not cfg_row.empty:
                status = cfg_row.iloc[0].get("Status", "Active")
                reason = cfg_row.iloc[0].get("Notes_Reason", "")

            ms_tasks = p_tasks[
                p_tasks["Milestone_Name"].astype(str).str.strip().str.lower()
                == str(ms_name).strip().lower()
            ]
            t_total = len(ms_tasks)
            t_completed = (
                len(
                    ms_tasks[
                        ms_tasks["Status"].astype(str).str.strip().str.upper()
                        == "COMPLETED"
                    ]
                )
                if t_total > 0
                else 0
            )

            # Calculation Logic
            if status == "Excluded":
                ms_pct = None  # Excluded from calculation
            elif status == "Pre-Completed":
                ms_pct = 100.0  # Explicitly completed
            else:  # Active
                ms_pct = (t_completed / t_total * 100.0) if t_total > 0 else 0.0

            if ms_pct is not None:
                applicable_ms_pcts.append(ms_pct)

            ms_summary[ms_name] = {
                "pct": ms_pct,
                "status": status,
                "reason": reason,
                "total_tasks": t_total,
                "completed_tasks": t_completed,
                "tasks_df": ms_tasks,
                "is_custom": ms_name not in stg_ms_master,
            }

        stg_pct = (
            (sum(applicable_ms_pcts) / len(applicable_ms_pcts))
            if applicable_ms_pcts
            else 100.0
        )
        valid_stage_pcts.append(stg_pct)

        stage_summary[stg] = {"pct": stg_pct, "milestones": ms_summary}

        if stg_pct < 100.0 and current_stage is None:
            current_stage = stg

    overall_pct = (
        (sum(valid_stage_pcts) / len(valid_stage_pcts))
        if valid_stage_pcts
        else 0.0
    )

    if overall_pct >= 100.0:
        current_stage = "Completed"
    elif current_stage is None:
        current_stage = ordered_stages[0] if ordered_stages else "Not Started"

    return {
        "overall_pct": overall_pct,
        "current_stage": current_stage,
        "stages": stage_summary,
        "total_tasks": len(p_tasks),
        "completed_tasks": len(
            p_tasks[
                p_tasks["Status"].astype(str).str.strip().str.upper() == "COMPLETED"
            ]
        ),
    }


# ==========================================
# 5. NAVIGATION
# ==========================================
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 48px; line-height: 1;">⚡</span>
            <div style="font-size: 22px; font-weight: 900; line-height: 1.15;">
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
            "Configure Project Milestones",
            "Add & Manage Task",
        ],
        icons=["speedometer2", "search", "plus-circle", "sliders", "check2-square"],
        menu_icon="compass",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"font-size": "18px"},
            "nav-link": {
                "font-size": "14px",
                "text-align": "left",
                "margin": "4px 0px",
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

# ==========================================
# VIEW 1: SUMMARY
# ==========================================
if mode == "Summary":
    st.title("📃 Portfolio Overview")

    summary_rows = []
    completed_projects_count = 0

    for _, p_row in df_projects.iterrows():
        p_name = p_row.get("Project_Name", "")
        metrics = calculate_project_metrics(p_name)

        if metrics["current_stage"] == "Completed":
            completed_projects_count += 1

        p_dict = p_row.to_dict()
        p_dict["Current Stage"] = metrics["current_stage"]
        p_dict["Total Tasks"] = metrics["total_tasks"]
        p_dict["Completed Tasks"] = metrics["completed_tasks"]
        p_dict["Completion %"] = round(metrics["overall_pct"], 1)
        summary_rows.append(p_dict)

    df_summary = pd.DataFrame(summary_rows)

    col1, col2 = st.columns(2)
    col1.metric("Total Active Projects", len(df_projects))
    col2.metric("Fully Completed Projects", completed_projects_count)

    st.markdown("---")
    st.dataframe(
        df_summary,
        use_container_width=True,
        column_config={
            "Completion %": st.column_config.ProgressColumn(
                "Completion %", format="%.1f%%", min_value=0, max_value=100
            ),
        },
        hide_index=True,
    )

# ==========================================
# VIEW 2: PROJECT TRACKING
# ==========================================
elif mode == "Project Tracking":
    st.title("🔍 Detailed Project Tracking")
    if not sorted_projects:
        st.info("No projects created yet.")
        st.stop()

    selected_proj = st.selectbox("Select Project", sorted_projects)
    metrics = calculate_project_metrics(selected_proj)

    st.markdown(f"### Overall Completion: **{metrics['overall_pct']:.1f}%**")
    st.progress(metrics["overall_pct"] / 100.0)
    st.markdown("---")

    for stg_name, s_info in metrics["stages"].items():
        col_t, col_v = st.columns([4, 1])
        col_t.markdown(f"#### 📌 {stg_name}")
        col_v.markdown(f"**{s_info['pct']:.1f}% Complete**")
        st.progress(s_info["pct"] / 100.0)

        for ms_name, m_info in s_info["milestones"].items():
            status = m_info["status"]
            ms_pct = m_info["pct"]
            custom_tag = " (⚡ Custom Milestone)" if m_info.get("is_custom") else ""

            if status == "Excluded":
                expander_title = f"🎯 {ms_name}{custom_tag} — 🚫 Excluded (N/A)"
            elif status == "Pre-Completed":
                expander_title = f"🎯 {ms_name}{custom_tag} — ⚡ 100% (Pre-Completed / Overridden)"
            else:
                expander_title = f"🎯 {ms_name}{custom_tag} — {ms_pct:.0f}% ({m_info['completed_tasks']}/{m_info['total_tasks']} Tasks Completed)"

            with st.expander(expander_title):
                if status == "Excluded":
                    st.warning(
                        f"**Milestone Excluded.** Reason/Note: {m_info['reason'] or 'Not applicable for this project.'}"
                    )
                elif status == "Pre-Completed":
                    st.success(
                        f"**Milestone Pre-Completed / Overridden.** Note: {m_info['reason'] or 'Completed prior to setup.'}"
                    )
                else:
                    st.progress(ms_pct / 100.0)
                    t_df = m_info["tasks_df"]
                    if not t_df.empty:
                        disp_cols = [
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
                            t_df[disp_cols], use_container_width=True, hide_index=True
                        )
                    else:
                        st.caption("No tasks created under this milestone yet.")
        st.markdown("---")

# ==========================================
# VIEW 3: CREATE NEW PROJECT
# ==========================================
elif mode == "Create New Project":
    st.title("➕ Create New Project")

    if "proj_success" in st.session_state:
        st.success(st.session_state.pop("proj_success"))

    if "temp_custom_milestones" not in st.session_state:
        st.session_state["temp_custom_milestones"] = []

    next_id = f"P{len(df_projects) + 1:03d}"

    st.subheader("1. Project Details")
    p_name = st.text_input("Project Name")
    capacity = st.text_input("Capacity (e.g., 50 MWp)")
    p_lead = st.text_input("Project Lead")
    target_date = st.date_input("Target Completion Date")

    st.markdown("---")
    st.subheader("2. Milestone Configuration (Standard Master Milestones)")
    st.caption("Set status for standard milestones (Active, Pre-Completed, or Excluded).")

    # Standard Milestones Form
    std_cfg_inputs = {}
    for idx, m_row in df_milestones.iterrows():
        stg = m_row["Stage_Name"]
        ms = m_row["Milestone_Name"]

        c1, c2, c3 = st.columns([2.5, 1.5, 2])
        c1.markdown(f"**{ms}**<br><small>*{stg}*</small>", unsafe_allow_html=True)
        status_val = c2.selectbox(
            "Status",
            ["Active", "Pre-Completed", "Excluded"],
            key=f"init_st_{idx}",
        )
        reason_val = c3.text_input("Notes / Reason", key=f"init_rs_{idx}")

        std_cfg_inputs[ms] = {
            "stage": stg,
            "status": status_val,
            "reason": reason_val,
        }

    st.markdown("---")
    st.subheader("3. Add Custom Milestones (Optional)")
    st.caption("Need a custom milestone specific to this project?")

    with st.expander("➕ Add Custom Milestone"):
        c_stage = st.selectbox("Stage for Custom Milestone", df_milestones["Stage_Name"].unique())
        c_name = st.text_input("Custom Milestone Name")
        c_status = st.selectbox("Status", ["Active", "Pre-Completed", "Excluded"], key="c_st_sel")
        c_reason = st.text_input("Notes / Reason for Custom Milestone", key="c_rs_in")

        if st.button("Add Custom Milestone to Setup"):
            if not c_name.strip():
                st.warning("Please enter a custom milestone name.")
            else:
                st.session_state["temp_custom_milestones"].append(
                    {
                        "Stage_Name": c_stage,
                        "Milestone_Name": c_name.strip(),
                        "Status": c_status,
                        "Notes_Reason": c_reason,
                    }
                )
                st.success(f"Added custom milestone: **{c_name}** under **{c_stage}**!")

    if st.session_state["temp_custom_milestones"]:
        st.markdown("#### Currently Added Custom Milestones:")
        st.dataframe(pd.DataFrame(st.session_state["temp_custom_milestones"]), use_container_width=True)
        if st.button("Clear Custom Milestones"):
            st.session_state["temp_custom_milestones"] = []
            st.rerun()

    st.markdown("---")
    if st.button("🚀 Create Project & Save Complete Setup", type="primary"):
        if not p_name or not capacity or not p_lead:
            st.warning("Please fill in all required project fields.")
        else:
            try:
                # Save Project Metadata
                new_p = pd.DataFrame(
                    [
                        {
                            "Project_ID": next_id,
                            "Project_Name": p_name,
                            "Capacity": capacity,
                            "Project_Lead": p_lead,
                            "Target_Completion_Date": target_date.strftime("%d/%m/%Y"),
                        }
                    ]
                )
                updated_p = pd.concat([df_projects, new_p], ignore_index=True)
                conn.update(worksheet="Projects", data=updated_p)

                # Collect Standard Config Rows
                cfg_rows = []
                for ms_name, ms_data in std_cfg_inputs.items():
                    cfg_rows.append(
                        {
                            "Project_Name": p_name,
                            "Stage_Name": ms_data["stage"],
                            "Milestone_Name": ms_name,
                            "Status": ms_data["status"],
                            "Notes_Reason": ms_data["reason"],
                        }
                    )

                # Collect Custom Config Rows
                for c_item in st.session_state["temp_custom_milestones"]:
                    cfg_rows.append(
                        {
                            "Project_Name": p_name,
                            "Stage_Name": c_item["Stage_Name"],
                            "Milestone_Name": c_item["Milestone_Name"],
                            "Status": c_item["Status"],
                            "Notes_Reason": c_item["Notes_Reason"],
                        }
                    )

                new_cfg_df = pd.DataFrame(cfg_rows)
                updated_cfg = pd.concat([df_configs, new_cfg_df], ignore_index=True)
                conn.update(worksheet="Project_Milestone_Config", data=updated_cfg)

                # Clear temporary session state
                st.session_state["temp_custom_milestones"] = []
                st.session_state["proj_success"] = (
                    f"✅ Project **{p_name}** (`{next_id}`) created successfully!"
                )
                st.rerun()
            except Exception as err:
                st.error(f"Error saving project: {err}")

# ==========================================
# VIEW 4: CONFIGURE PROJECT MILESTONES
# ==========================================
elif mode == "Configure Project Milestones":
    st.title("⚙️ Configure Project Milestone Setup")
    if not sorted_projects:
        st.info("No projects available.")
        st.stop()

    proj = st.selectbox("Select Project to Configure", sorted_projects)
    st.caption("Update milestone settings or add custom milestones for this project.")

    p_configs = df_configs[
        df_configs["Project_Name"].astype(str).str.strip().str.lower()
        == str(proj).strip().lower()
    ]

    # Get master milestones + any existing custom milestones for this project
    stg_ms_master = df_milestones[["Stage_Name", "Milestone_Name"]].drop_duplicates()
    
    # Custom milestones already in config for this project
    custom_cfgs = p_configs[
        ~p_configs["Milestone_Name"].astype(str).str.strip().str.lower().isin(
            df_milestones["Milestone_Name"].astype(str).str.strip().str.lower()
        )
    ][["Stage_Name", "Milestone_Name"]].drop_duplicates()

    all_proj_ms = pd.concat([stg_ms_master, custom_cfgs], ignore_index=True)

    with st.form("edit_milestone_config_form"):
        updated_cfgs = {}
        for idx, m_row in all_proj_ms.iterrows():
            stg = m_row["Stage_Name"]
            ms = m_row["Milestone_Name"]

            curr_cfg = p_configs[
                p_configs["Milestone_Name"].astype(str).str.strip().str.lower()
                == str(ms).strip().lower()
            ]
            default_status = "Active"
            default_reason = ""

            if not curr_cfg.empty:
                default_status = curr_cfg.iloc[0].get("Status", "Active")
                default_reason = curr_cfg.iloc[0].get("Notes_Reason", "")

            status_opts = ["Active", "Pre-Completed", "Excluded"]
            s_idx = (
                status_opts.index(default_status)
                if default_status in status_opts
                else 0
            )

            is_custom = ms not in df_milestones["Milestone_Name"].values
            c_tag = " (⚡ Custom)" if is_custom else ""

            c1, c2, c3 = st.columns([2.5, 1.5, 2])
            c1.markdown(f"**{ms}**{c_tag}<br><small>*{stg}*</small>", unsafe_allow_html=True)
            new_st = c2.selectbox(
                "Status", status_opts, index=s_idx, key=f"edit_st_{idx}"
            )
            new_rs = c3.text_input("Notes / Reason", value=default_reason, key=f"edit_rs_{idx}")

            updated_cfgs[ms] = {"stage": stg, "status": new_st, "reason": new_rs}

        if st.form_submit_button("Save Milestone Configurations"):
            try:
                # Remove existing configs for project
                clean_cfg = df_configs[
                    df_configs["Project_Name"].astype(str).str.strip().str.lower()
                    != str(proj).strip().lower()
                ]

                # Append updated configs
                rows = [
                    {
                        "Project_Name": proj,
                        "Stage_Name": data["stage"],
                        "Milestone_Name": ms_k,
                        "Status": data["status"],
                        "Notes_Reason": data["reason"],
                    }
                    for ms_k, data in updated_cfgs.items()
                ]

                updated_df = pd.concat([clean_cfg, pd.DataFrame(rows)], ignore_index=True)
                conn.update(worksheet="Project_Milestone_Config", data=updated_df)
                st.success(f"✅ Milestone configuration for **{proj}** updated!")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating config: {e}")

    st.markdown("---")
    st.subheader("➕ Add a New Custom Milestone to this Project")
    with st.form("add_new_custom_ms_form"):
        add_stg = st.selectbox("Stage", df_milestones["Stage_Name"].unique(), key="add_c_stg")
        add_ms_name = st.text_input("Custom Milestone Name", key="add_c_name")
        add_status = st.selectbox("Status", ["Active", "Pre-Completed", "Excluded"], key="add_c_stat")
        add_reason = st.text_input("Notes / Reason", key="add_c_reas")

        if st.form_submit_button("Add Custom Milestone"):
            if not add_ms_name.strip():
                st.warning("Please enter a custom milestone name.")
            else:
                try:
                    new_cfg_row = pd.DataFrame(
                        [
                            {
                                "Project_Name": proj,
                                "Stage_Name": add_stg,
                                "Milestone_Name": add_ms_name.strip(),
                                "Status": add_status,
                                "Notes_Reason": add_reason,
                            }
                        ]
                    )
                    updated_cfg_df = pd.concat([df_configs, new_cfg_row], ignore_index=True)
                    conn.update(worksheet="Project_Milestone_Config", data=updated_cfg_df)
                    st.success(f"✅ Added custom milestone **{add_ms_name}** to **{proj}**!")
                    st.rerun()
                except Exception as err:
                    st.error(f"Error adding custom milestone: {err}")

# ==========================================
# VIEW 5: ADD & MANAGE TASK
# ==========================================
elif mode == "Add & Manage Task":
    st.title("⚙️ Task Management")
    if not sorted_projects:
        st.info("No projects available.")
        st.stop()

    if "task_success" in st.session_state:
        st.success(st.session_state.pop("task_success"))

    proj = st.selectbox("Project", sorted_projects)
    stage = st.selectbox("Stage", df_milestones["Stage_Name"].unique())

    # Get standard master milestones for stage
    master_ms = df_milestones[
        df_milestones["Stage_Name"].astype(str).str.strip() == str(stage).strip()
    ]["Milestone_Name"].unique().tolist()

    # Get custom milestones for project & stage
    proj_stage_cfgs = df_configs[
        (df_configs["Project_Name"].astype(str).str.strip().str.lower() == str(proj).strip().lower())
        & (df_configs["Stage_Name"].astype(str).str.strip().str.lower() == str(stage).strip().lower())
    ]["Milestone_Name"].unique().tolist()

    # Combine lists
    combined_ms = list(master_ms)
    for m in proj_stage_cfgs:
        if m.lower() not in [x.lower() for x in combined_ms]:
            combined_ms.append(m)

    ms = st.selectbox("Milestone", combined_ms)

    # Check status of selected milestone
    curr_ms_cfg = df_configs[
        (df_configs["Project_Name"].astype(str).str.strip().str.lower() == str(proj).strip().lower())
        & (df_configs["Milestone_Name"].astype(str).str.strip().str.lower() == str(ms).strip().lower())
    ]

    ms_status = curr_ms_cfg.iloc[0].get("Status", "Active") if not curr_ms_cfg.empty else "Active"

    if ms_status == "Excluded":
        st.warning(f"⚠️ Milestone **{ms}** is set as **Excluded (N/A)** for this project.")
    elif ms_status == "Pre-Completed":
        st.info(f"⚡ Milestone **{ms}** is set as **Pre-Completed / Overridden**. Tasks are optional.")

    st.markdown("---")

    tab_add, tab_update = st.tabs(["➕ Add New Task", "📝 Update Task Status"])

    with tab_add:
        with st.form("add_task_form"):
            desc = st.text_area("Task Description")
            assigned = st.text_input("Assigned To")
            col_s, col_d = st.columns(2)
            s_date = col_s.date_input("Start Date")
            d_date = col_d.date_input("Due Date")

            if st.form_submit_button("Submit Task"):
                if not desc or not assigned:
                    st.warning("Please fill in Description and Assigned To.")
                elif d_date < s_date:
                    st.error("Due Date cannot precede Start Date.")
                else:
                    try:
                        next_id = f"T{len(df_tasks) + 1:03d}"
                        new_t = pd.DataFrame(
                            [
                                {
                                    "Task_ID": next_id,
                                    "Project_Name": proj,
                                    "Stage_Name": stage,
                                    "Milestone_Name": ms,
                                    "Task_Description": desc,
                                    "Assigned_To": assigned,
                                    "Start_Date": s_date.strftime("%d/%m/%Y"),
                                    "Due_Date": d_date.strftime("%d/%m/%Y"),
                                    "Status": "On-going",
                                    "Risks_Issues_Remarks": "",
                                }
                            ]
                        )
                        updated_t = pd.concat([df_tasks, new_t], ignore_index=True)
                        conn.update(worksheet="Tasks", data=updated_t)
                        st.session_state["task_success"] = f"✅ Task **{next_id}** created!"
                        st.rerun()
                    except Exception as err:
                        st.error(f"Error saving task: {err}")

    with tab_update:
        matching_tasks = df_tasks[
            (df_tasks["Project_Name"].astype(str).str.strip().str.lower() == str(proj).strip().lower())
            & (df_tasks["Milestone_Name"].astype(str).str.strip().str.lower() == str(ms).strip().lower())
        ]

        if matching_tasks.empty:
            st.info(f"No tasks under **{ms}** for project **{proj}**.")
        else:
            task_options = {
                f"{r['Task_ID']} - {r['Task_Description']} ({r['Assigned_To']})": r["Task_ID"]
                for _, r in matching_tasks.iterrows()
            }
            sel_label = st.selectbox("Select Task to Update", list(task_options.keys()))
            sel_id = task_options[sel_label]
            curr_row = matching_tasks[matching_tasks["Task_ID"] == sel_id].iloc[0]

            opts = ["On-going", "Completed", "Cancelled"]
            curr_st = str(curr_row.get("Status", "On-going"))
            idx = opts.index(curr_st) if curr_st in opts else 0

            with st.form("update_task_form"):
                n_status = st.selectbox("Task Status", opts, index=idx)
                n_remarks = st.text_area(
                    "Risks / Remarks",
                    value=str(curr_row.get("Risks_Issues_Remarks", "")).replace("nan", ""),
                )

                if st.form_submit_button("Update Task"):
                    try:
                        t_idx = df_tasks[df_tasks["Task_ID"] == sel_id].index[0]
                        df_tasks.loc[t_idx, "Status"] = n_status
                        df_tasks.loc[t_idx, "Risks_Issues_Remarks"] = n_remarks
                        conn.update(worksheet="Tasks", data=df_tasks)
                        st.session_state["task_success"] = f"✅ Task **{sel_id}** updated to {n_status}!"
                        st.rerun()
                    except Exception as err:
                        st.error(f"Error updating task: {err}")
