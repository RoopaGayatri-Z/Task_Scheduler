from datetime import date

import requests
import streamlit as st

# Set this in .streamlit/secrets.toml locally, and in Streamlit Cloud's
# "Secrets" settings when deployed. Falls back to localhost for local dev.
API_URL = st.secrets.get("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Student Task Scheduler", layout="wide")
st.title("📅 Student Task Scheduler")
st.caption("Conflict-aware task & revision tracker — backend REST API + Supabase Postgres")

tab1, tab2, tab3 = st.tabs(["📋 All Tasks", "➕ Add Task", "⚠️ Conflicts"])

# ---------------------------------------------------------------- Add Task
with tab2:
    st.subheader("Add a new task")
    with st.form("add_task_form", clear_on_submit=True):
        title = st.text_input("Title")
        description = st.text_area("Description", "")
        category = st.selectbox("Category", ["assignment", "revision", "general"])
        subject = st.text_input("Subject (only relevant for revision tasks, e.g. 'DBMS')", "")

        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start date", date.today())
        with col2:
            due_date = st.date_input("Due date", date.today())

        priority = st.selectbox("Priority", ["low", "medium", "high"])
        submitted = st.form_submit_button("Add Task")

        if submitted:
            if not title:
                st.error("Title is required")
            elif due_date < start_date:
                st.error("Due date can't be before start date")
            else:
                payload = {
                    "title": title,
                    "description": description or None,
                    "category": category,
                    "subject": subject or None,
                    "start_date": str(start_date),
                    "due_date": str(due_date),
                    "priority": priority,
                    "status": "pending",
                }
                try:
                    r = requests.post(f"{API_URL}/tasks", json=payload, timeout=10)
                    if r.status_code == 200:
                        st.success("Task added!")
                    else:
                        st.error(f"Failed: {r.text}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Could not reach the API at {API_URL}: {e}")

# ---------------------------------------------------------------- All Tasks
with tab1:
    st.subheader("All Tasks")
    filter_category = st.selectbox("Filter by category", ["all", "assignment", "revision", "general"])
    params = {} if filter_category == "all" else {"category": filter_category}

    try:
        r = requests.get(f"{API_URL}/tasks", params=params, timeout=10)
    except requests.exceptions.RequestException as e:
        r = None
        st.error(f"Could not reach the API at {API_URL}: {e}")

    if r is not None and r.status_code == 200:
        tasks = r.json()
        if not tasks:
            st.info("No tasks yet — add one in the 'Add Task' tab.")

        priority_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}

        for task in tasks:
            label = f"{priority_emoji.get(task['priority'], '⚪')} {task['title']} — due {task['due_date']}"
            with st.expander(label):
                st.write(f"**Category:** {task['category']}")
                if task.get("subject"):
                    st.write(f"**Subject:** {task['subject']}")
                st.write(f"**Description:** {task.get('description') or '—'}")
                st.write(f"**Window:** {task['start_date']} → {task['due_date']}")
                st.write(f"**Status:** {task['status']}")

                col1, col2 = st.columns(2)
                with col1:
                    if task["status"] == "pending":
                        if st.button("✅ Mark done", key=f"done_{task['id']}"):
                            requests.put(f"{API_URL}/tasks/{task['id']}", json={"status": "done"}, timeout=10)
                            st.rerun()
                with col2:
                    if st.button("🗑️ Delete", key=f"del_{task['id']}"):
                        requests.delete(f"{API_URL}/tasks/{task['id']}", timeout=10)
                        st.rerun()
    elif r is not None:
        st.error("Could not fetch tasks from the API.")

# ---------------------------------------------------------------- Conflicts
with tab3:
    st.subheader("Conflict Warnings")
    st.caption("High-priority, pending tasks whose date windows overlap")
    try:
        r = requests.get(f"{API_URL}/tasks/conflicts/check", timeout=10)
        if r.status_code == 200:
            conflicts = r.json()
            if not conflicts:
                st.success("No conflicts detected 🎉")
            for c in conflicts:
                st.warning(
                    f"**{c['task_1']}** overlaps with **{c['task_2']}** "
                    f"between {c['overlap_start']} and {c['overlap_end']}"
                )
        else:
            st.error("Could not fetch conflicts.")
    except requests.exceptions.RequestException as e:
        st.error(f"Could not reach the API at {API_URL}: {e}")
