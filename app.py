import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from streamlit_option_menu import option_menu

# ==========================================
# 1. PAGE SETUP & MODERN CSS THEMING
# ==========================================
st.set_page_config(
    page_title="Renewable Energy Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    /* Balanced top padding so header widgets don't overlap titles */
    .block-container {
        padding-top: 4.5rem !important;
        padding-bottom: 3rem !important;
    }

    [data-testid="stHeader"] {
        background-color: transparent !important;
        z-index: 100 !important;
    }

    [data-testid="stStatusWidget"] {
        top: 0.5rem !important;
    }

    /* Executive KPI Card Design */
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 16px 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 12px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
    }
    .kpi-title {
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 1.7rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.1;
    }
    .kpi-sub {
        font-size: 0.78rem;
        color: #10B981;
        font-weight: 600;
        margin-top: 4px;
    }

    /* Info Banner Header Card */
    .info-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        color: #FFFFFF;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15);
    }
    .info-banner-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #FFD700;
        margin-bottom: 12px;
    }
    .info-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 16px;
    }
    .info-item-label {
        font-size: 0.75rem;
        color: #94A3B8;
        text-transform: uppercase;
        font-weight: 600;
    }
    .info-item-val {
        font-size: 1.05rem;
        font-weight: 700;
        color: #F8FAFC;
    }

    /* Status Pill Badges */
    .badge-active {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 700;
    }
    .badge-completed {
        background-color: #FEF08A;
        color: #854D0E;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.78rem;
        font-weight: 700;
    }

    /* Primary buttons styling */
    div.stButton > button {
        background-color: #FFD700 !important;
        color: #000000 !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 8px 16px !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        background-color: #E6C200 !important;
        box-shadow: 0 4px 10px rgba(255, 215, 0, 0.4) !important;
    }

    /* Sidebar flexbox setup */
    [data-testid="stSidebarUserContent"] {
        display: flex !important;
        flex-direction: column !important;
        height: calc(100vh - 60px) !important;
    }
    .sidebar-spacer { flex-grow: 1 !important; }

    /* Streamlit Progress Bar Colors */
    .stProgress > div > div > div > div { background-color: #FFD700 !important; }

    /* Active navigation icon fix */
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
# 3. DATA CONNECTION & CACHED LOAD
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)


@st.cache_data(ttl=10)
def load_data():
    """Cached loader (ttl=10s) prevents hitting Google Sheets API rate limit (429)."""
    df_p = conn.read(worksheet="Projects", ttl=10)
    df_m = conn.read(worksheet="Milestones_Master", ttl=10)
    df_t = conn.read(worksheet="Tasks", ttl=10)

    try:
        df_cfg = conn.read(worksheet="Project_Milestone_Config", ttl=10)
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

    for df in [df_p, df_m, df_t, df_cfg]:
        if df is not None and not df.empty:
            df.columns = [str(col).strip() for col in df.columns]
            for col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.strip()

    return df_p, df_m, df_t, df_cfg


try:
    df_projects, df_milestones, df_tasks, df_configs = load_data()
except Exception as e:
    st.error(
        f"⚠️ Rate limit reached or connection issue with Google Sheets. "
        f"Please wait a few seconds and refresh. Error: {e}"
    )
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

            if status == "Excluded":
                ms_pct = None
            elif status == "Pre-Completed":
                ms_pct = 100.0
            else:
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
# 5. NAVIGATION SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown(
        """
        <div style="display: flex; align-items: center; gap: 12px; padding: 4px 0;">
            <span style="font-size: 42px; line-height: 1;">⚡</span>
            <div>
                <div style="font-size: 20px; font-weight: 800; color: #0F172A; line-height: 1.1;">
                    RE Dashboard
                </div>
                <div style="font-size: 12px; color: #64748B; font-weight: 600;">
                    Portfolio Tracker
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")

    mode = option_menu(
        menu_title=None,
        options=[
            "Summary",
            "Project Tracking",
            "Create New Project",
            "Configure Project Milestones",
            "Add & Manage Task",
        ],
        icons=["speedometer2", "search", "plus-circle", "sliders", "check2-square"],
        menu_icon=None,
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "transparent"},
            "icon": {"font-size": "17px"},
            "nav-link": {
                "font-size": "14px",
                "text-align": "left",
                "margin": "4px 0px",
                "border-radius": "8px",
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
    st.markdown(
        f"""
        <div style="background: #F1F5F9; padding: 12px; border-radius: 8px; margin-bottom: 12px;">
            <div style="font-size: 12px; color: #64748B; font-weight: 600;">LOGGED IN USER</div>
            <div style="font-size: 15px; color: #0F172A; font-weight: 800;">👤 {st.session_state['username']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Log Out"):
        st.session_state["authenticated"] = False
        st.rerun()

# ==========================================
# VIEW 1: SUMMARY (PORTFOLIO OVERVIEW)
# ==========================================
if mode == "Summary":
    st.markdown("## 📃 Portfolio Overview")
    st.caption("Real-time executive summary and progress across all renewable energy projects.")

    summary_rows = []
    completed_projects_count = 0
    total_target_capacity_mw = 0.0
    total_installed_capacity_mw = 0.0

    for _, p_row in df_projects.iterrows():
        p_name = p_row.get("Project_Name", "")
        metrics = calculate_project_metrics(p_name)

        is_completed = (metrics["current_stage"] == "Completed")
        if is_completed:
            completed_projects_count += 1

        cap_str = str(p_row.get("Capacity", "0")).lower().replace("mwp", "").replace("mw", "").strip()
        try:
            cap_val = float(cap_str)
        except ValueError:
            cap_val = 0.0

        total_target_capacity_mw += cap_val
        if is_completed:
            total_installed_capacity_mw += cap_val

        p_dict = p_row.to_dict()
        p_dict["Current Stage"] = metrics["current_stage"]
        p_dict["Total Tasks"] = metrics["total_tasks"]
        p_dict["Completed Tasks"] = metrics["completed_tasks"]
        p_dict["Completion %"] = round(metrics["overall_pct"], 1)
        summary_rows.append(p_dict)

    df_summary = pd.DataFrame(summary_rows)
    avg_portfolio_completion = (
        df_summary["Completion %"].mean() if not df_summary.empty else 0.0
    )

    # 1. Executive KPI Cards Row (5 Columns)
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Total Projects</div>
                <div class="kpi-value">{len(df_projects)}</div>
                <div class="kpi-sub">⚡ Active Portfolio</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Target Capacity</div>
                <div class="kpi-value">{total_target_capacity_mw:.0f} <span style="font-size:0.95rem; font-weight:600;">MWp</span></div>
                <div class="kpi-sub">🎯 Total Pipeline</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Installed Capacity</div>
                <div class="kpi-value">{total_installed_capacity_mw:.0f} <span style="font-size:0.95rem; font-weight:600;">MWp</span></div>
                <div class="kpi-sub">☀️ Fully Operational</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Avg Progress</div>
                <div class="kpi-value">{avg_portfolio_completion:.1f}%</div>
                <div class="kpi-sub">📈 Portfolio Average</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k5:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-title">Fully Completed</div>
                <div class="kpi-value">{completed_projects_count}</div>
                <div class="kpi-sub">🎉 Operational Projects</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Clean Full-Width Project Progress Comparison
    if not df_summary.empty:
        st.markdown("#### 📊 Project Progress Comparison")
        fig_bar = px.bar(
            df_summary,
            x="Project_Name",
            y="Completion %",
            color="Current Stage",
            text_auto=".1f",
            hover_data=["Capacity", "Project_Lead"],
            color_discrete_sequence=["#FFD700", "#0F172A", "#3B82F6", "#10B981"],
        )
        fig_bar.update_layout(
            template="plotly_white",
            xaxis_title="",
            yaxis_title="Completion (%)",
            yaxis_range=[0, 100],
            margin=dict(l=20, r=20, t=20, b=20),
            height=320,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 📋 Detailed Projects Summary Table")

    disp_rename = {
        "Project_ID": "Project ID",
        "Project_Name": "Project Name",
        "Capacity": "Capacity",
        "Project_Lead": "Project Lead",
        "Target_Completion_Date": "Target Completion Date",
        "Current Stage": "Current Stage",
        "Total Tasks": "Total Tasks",
        "Completed Tasks": "Completed Tasks",
        "Completion %": "Completion %",
    }
    df_disp = df_summary.rename(columns=disp_rename)

    st.dataframe(
        df_disp,
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
    st.markdown("## 🔍 Detailed Project Tracking")
    if not sorted_projects:
        st.info("No projects created yet.")
        st.stop()

    selected_proj = st.selectbox("Select Project to Inspect", sorted_projects)
    metrics = calculate_project_metrics(selected_proj)

    p_row = df_projects[
        df_projects["Project_Name"].astype(str).str.strip().str.lower()
        == str(selected_proj).strip().lower()
    ]
    p_lead = p_row.iloc[0].get("Project_Lead", "N/A") if not p_row.empty else "N/A"
    p_cap = p_row.iloc[0].get("Capacity", "N/A") if not p_row.empty else "N/A"
    p_target = p_row.iloc[0].get("Target_Completion_Date", "N/A") if not p_row.empty else "N/A"

    st.markdown(
        f"""
        <div class="info-banner">
            <div class="info-banner-title">⚡ {selected_proj}</div>
            <div class="info-grid">
                <div>
                    <div class="info-item-label">Overall Completion</div>
                    <div class="info-item-val" style="color: #FFD700; font-size: 1.4rem;">{metrics['overall_pct']:.1f}%</div>
                </div>
                <div>
                    <div class="info-item-label">Current Stage</div>
                    <div class="info-item-val">{metrics['current_stage']}</div>
                </div>
                <div>
                    <div class="info-item-label">Capacity</div>
                    <div class="info-item-val">{p_cap}</div>
                </div>
                <div>
                    <div class="info-item-label">Project Lead</div>
                    <div class="info-item-val">{p_lead}</div>
                </div>
                <div>
                    <div class="info-item-label">Target Completion</div>
                    <div class="info-item-val">{p_target}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.progress(metrics["overall_pct"] / 100.0)
    st.markdown("<br>", unsafe_allow_html=True)

    for stg_name, s_info in metrics["stages"].items():
        stg_pct = s_info["pct"]

        col_t, col_v = st.columns([3.8, 1.2])
        col_t.markdown(f"### 📁 {stg_name}")
        
        badge_html = (
            f'<span class="badge-completed">100% COMPLETE</span>'
            if stg_pct == 100.0
            else f'<span class="badge-active">{stg_pct:.1f}% COMPLETE</span>'
        )
        col_v.markdown(f"<div style='text-align:right; margin-top: 8px;'>{badge_html}</div>", unsafe_allow_html=True)
        
        st.progress(stg_pct / 100.0)

        for ms_name, m_info in s_info["milestones"].items():
            status = m_info["status"]
            ms_pct = m_info["pct"]
            custom_tag = " (⚡ Custom)" if m_info.get("is_custom") else ""

            if status == "Excluded":
                exp_title = f"🎯 {ms_name}{custom_tag} — 🚫 Excluded (N/A)"
            elif status == "Pre-Completed":
                exp_title = f"🎯 {ms_name}{custom_tag} — ⚡ 100% (Pre-Completed / Overridden)"
            else:
                exp_title = f"🎯 {ms_name}{custom_tag} — {ms_pct:.0f}% ({m_info['completed_tasks']}/{m_info['total_tasks']} Tasks Completed)"

            with st.expander(exp_title):
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
    st.markdown("## ➕ Create New Project")
    st.caption("Define new project parameters and set up custom/standard stage milestones.")

    if "proj_success" in st.session_state:
        st.success(st.session_state.pop("proj_success"))

    if "temp_custom_milestones" not in st.session_state:
        st.session_state["temp_custom_milestones"] = []

    next_id = f"P{len(df_projects) + 1:03d}"

    st.subheader("1. Project Details")
    c1, c2 = st.columns(2)
    p_name = c1.text_input("Project Name")
    capacity = c2.text_input("Capacity (e.g., 50 MWp)")

    c3, c4 = st.columns(2)
    p_lead = c3.text_input("Project Lead")
    target_date = c4.date_input("Target Completion Date")

    st.markdown("---")
    st.subheader("2. Milestone Configuration (Standard Master Milestones)")
    st.caption("Expand a stage below to configure status for its standard milestones.")

    std_cfg_inputs = {}

    for stage_name, stage_group in df_milestones.groupby("Stage_Name", sort=False):
        with st.expander(f"📁 {stage_name}", expanded=True):
            for idx, m_row in stage_group.iterrows():
                ms = m_row["Milestone_Name"]

                col_name, col_status, col_reason = st.columns([3, 1.5, 2.5])
                col_name.markdown(f"**{ms}**")
                status_val = col_status.selectbox(
                    "Status",
                    ["Active", "Pre-Completed", "Excluded"],
                    key=f"init_st_{idx}",
                )
                reason_val = col_reason.text_input("Notes / Reason", key=f"init_rs_{idx}")

                std_cfg_inputs[ms] = {
                    "stage": stage_name,
                    "status": status_val,
                    "reason": reason_val,
                }

    st.markdown("---")
    st.subheader("3. Add Custom Milestones (Optional)")
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

                st.cache_data.clear()
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
    st.markdown("## ⚙️ Configure Project Milestone Setup")
    if not sorted_projects:
        st.info("No projects available.")
        st.stop()

    proj = st.selectbox("Select Project to Configure", sorted_projects)
    st.caption("Update milestone settings or add custom milestones for this project.")

    p_configs = df_configs[
        df_configs["Project_Name"].astype(str).str.strip().str.lower()
        == str(proj).strip().lower()
    ]

    stg_ms_master = df_milestones[["Stage_Name", "Milestone_Name"]].drop_duplicates()
    custom_cfgs = p_configs[
        ~p_configs["Milestone_Name"].astype(str).str.strip().str.lower().isin(
            df_milestones["Milestone_Name"].astype(str).str.strip().str.lower()
        )
    ][["Stage_Name", "Milestone_Name"]].drop_duplicates()

    all_proj_ms = pd.concat([stg_ms_master, custom_cfgs], ignore_index=True)

    with st.form("edit_milestone_config_form"):
        updated_cfgs = {}

        for stage_name, stage_group in all_proj_ms.groupby("Stage_Name", sort=False):
            st.markdown(f"### 📁 {stage_name}")
            for idx, m_row in stage_group.iterrows():
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

                col1, col2, col3 = st.columns([3, 1.5, 2.5])
                col1.markdown(f"**{ms}**{c_tag}")
                new_st = col2.selectbox(
                    "Status", status_opts, index=s_idx, key=f"edit_st_{idx}"
                )
                new_rs = col3.text_input("Notes / Reason", value=default_reason, key=f"edit_rs_{idx}")

                updated_cfgs[ms] = {"stage": stage_name, "status": new_st, "reason": new_rs}

            st.markdown("---")

        if st.form_submit_button("Save Milestone Configurations"):
            try:
                clean_cfg = df_configs[
                    df_configs["Project_Name"].astype(str).str.strip().str.lower()
                    != str(proj).strip().lower()
                ]

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

                st.cache_data.clear()
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

                    st.cache_data.clear()
                    st.success(f"✅ Added custom milestone **{add_ms_name}** to **{proj}**!")
                    st.rerun()
                except Exception as err:
                    st.error(f"Error adding custom milestone: {err}")

# ==========================================
# VIEW 5: ADD & MANAGE TASK
# ==========================================
elif mode == "Add & Manage Task":
    st.markdown("## ⚙️ Task Management")
    if not sorted_projects:
        st.info("No projects available.")
        st.stop()

    if "task_success" in st.session_state:
        st.success(st.session_state.pop("task_success"))

    col_p, col_s, col_m = st.columns(3)
    proj = col_p.selectbox("Project", sorted_projects)
    stage = col_s.selectbox("Stage", df_milestones["Stage_Name"].unique())

    master_ms = df_milestones[
        df_milestones["Stage_Name"].astype(str).str.strip() == str(stage).strip()
    ]["Milestone_Name"].unique().tolist()

    proj_stage_cfgs = df_configs[
        (df_configs["Project_Name"].astype(str).str.strip().str.lower() == str(proj).strip().lower())
        & (df_configs["Stage_Name"].astype(str).str.strip().str.lower() == str(stage).strip().lower())
    ]["Milestone_Name"].unique().tolist()

    combined_ms = list(master_ms)
    for m in proj_stage_cfgs:
        if m.lower() not in [x.lower() for x in combined_ms]:
            combined_ms.append(m)

    ms = col_m.selectbox("Milestone", combined_ms)

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

                        st.cache_data.clear()
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

                        st.cache_data.clear()
                        st.session_state["task_success"] = f"✅ Task **{sel_id}** updated to {n_status}!"
                        st.rerun()
                    except Exception as err:
                        st.error(f"Error updating task: {err}")
