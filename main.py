import sys
import os
# Add the project root to sys.path dynamically
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import json
from datetime import datetime

# Initialize Streamlit Page Config at the very top
st.set_page_config(
    page_title="AI Financial Report Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

from src.auth.models import init_db
from src.auth.manager import login_user, register_user, log_action, get_document_by_id
from src.ui.styles import inject_premium_css, render_metric_card
from src.ui.document_hub import render_document_hub, UPLOAD_DIR
from src.ui.dashboard import render_financial_dashboard
from src.ui.qa_interface import render_qa_interface
from src.ui.admin_panel import render_admin_panel
from src.analysis.ratios import calculate_ratios
from src.analysis.risk_detector import detect_risks
from src.analysis.kpi_extractor import extract_kpis_summary
from src.rag.ai_agent import query_ai
from src.exporter.excel_generator import generate_excel_report
from src.exporter.pdf_generator import generate_pdf_report

def main():
    # 1. Initialize SQLite Database Schema
    init_db()
    
    # 2. Inject Premium CSS Styles
    inject_premium_css()
    
    # 3. Setup Session State
    if "user" not in st.session_state:
        st.session_state.user = None
    if "active_doc_id" not in st.session_state:
        st.session_state.active_doc_id = None
    if "gemini_api_key" not in st.session_state:
        st.session_state.gemini_api_key = ""
        
    # 4. Handle Login Screens if not Authenticated
    if st.session_state.user is None:
        render_auth_screen()
        return
        
    # 5. Main Application Layout (Authenticated)
    user = st.session_state.user
    
    # Render Sidebar Brand Logo and User Context
    st.sidebar.markdown('<div class="sidebar-logo">FIN-INTELLECT 📊</div>', unsafe_allow_html=True)
    st.sidebar.markdown(f"👤 Welcome, **{user['username']}**")
    
    # Access badges
    badge_type = "admin" if user["role"] == "Admin" else "user"
    st.sidebar.markdown(f'<span class="badge badge-{badge_type}">{user["role"]} Access</span>', unsafe_allow_html=True)
    st.sidebar.markdown("<br/>", unsafe_allow_html=True)
    
    # Navigation Router
    nav_options = ["📂 Document Ingestion", "📊 Visual Dashboard", "💬 Analyst Chatbot (RAG)", "📄 Executive Summary & Exporter"]
    if user["role"] == "Admin":
        nav_options.append("⚙️ Console Administration")
        
    selected_page = st.sidebar.radio("Navigation Cockpit", nav_options)
    
    # Logout Button
    st.sidebar.markdown("---")
    if st.sidebar.button("Log Out", use_container_width=True):
        log_action(user["id"], "LOGOUT", f"User {user['username']} logged out.")
        st.session_state.user = None
        st.session_state.active_doc_id = None
        st.session_state.chat_history = []
        st.rerun()

    # 6. Fetch active document & evaluate financial calculations
    active_doc_id = st.session_state.get("active_doc_id")
    doc = None
    metrics = {}
    ratios = {}
    risks = []
    kpis = {}
    
    if active_doc_id:
        doc = get_document_by_id(active_doc_id)
        if doc and doc.get("financials_json"):
            metrics = json.loads(doc["financials_json"])
            ratios = calculate_ratios(metrics)
            risks = detect_risks(metrics, ratios)
            kpis = extract_kpis_summary(metrics, ratios)

    # 7. Render Pages
    if selected_page == "📂 Document Ingestion":
        render_document_hub()
    elif selected_page == "📊 Visual Dashboard":
        render_financial_dashboard(metrics, ratios, risks, kpis)
    elif selected_page == "💬 Analyst Chatbot (RAG)":
        render_qa_interface()
    elif selected_page == "📄 Executive Summary & Exporter":
        render_executive_summary_page(doc, metrics, ratios, risks, kpis)
    elif selected_page == "⚙️ Console Administration":
        render_admin_panel()

def render_auth_screen():
    """Renders a beautiful credentials form for logging in or signing up."""
    st.markdown("<h1 style='text-align: center;'>Financial Analyzer Intelligence Platform</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94A3B8; margin-top:-15px;'>Ingest, audit, screen, and chat with corporate reports using advanced LLMs & RAG.</p>", unsafe_allow_html=True)
    
    cols = st.columns([1, 1.6, 1])
    with cols[1]:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        
        tab_login, tab_register = st.tabs(["🔑 Access Login", "👥 Register Account"])
        
        with tab_login:
            st.markdown("### Access Login")
            l_username = st.text_input("Username:", key="l_user")
            l_password = st.text_input("Password:", type="password", key="l_pass")
            
            if st.button("Log In", type="primary", use_container_width=True):
                if not l_username or not l_password:
                    st.error("Please enter both username and password.")
                else:
                    u = login_user(l_username, l_password)
                    if u:
                        st.session_state.user = u
                        st.success("Successfully logged in!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password configuration.")
            
            # Seed reminders
            st.info("💡 **Quick Test Profiles:**\n- Admin access: Username: `admin` / Password: `admin123`\n- User access: Username: `user` / Password: `user123`")
            
        with tab_register:
            st.markdown("### Create New Profile")
            r_username = st.text_input("Username:", key="r_user")
            r_password = st.text_input("Password:", type="password", key="r_pass")
            r_role = st.selectbox("Role Permissions:", ["User", "Admin"])
            
            if st.button("Create Account", use_container_width=True):
                if len(r_username.strip()) < 3 or len(r_password) < 4:
                    st.error("Username must be >= 3 chars, password must be >= 4 chars.")
                else:
                    if register_user(r_username.strip(), r_password, r_role):
                        st.success("Profile created! You can now log in using the Login tab.")
                    else:
                        st.error("Username already registered in SQLite database.")
                        
        st.markdown('</div>', unsafe_allow_html=True)

def render_executive_summary_page(doc, metrics, ratios, risks, kpis):
    """Renders the executive summary tab, automated report text, and document export buttons."""
    if not doc:
        st.info("Please upload a financial document in the Document Hub to generate summaries.")
        return
        
    st.markdown("## 📄 Automated Executive Summary & Report Export")
    st.caption(f"Currently summarizing: **{doc['name']}**")
    
    # 1. Check/Generate AI summary in Session State to prevent LLM call repeating on rerun
    summary_key = f"ai_summary_{doc['id']}"
    
    if summary_key not in st.session_state:
        with st.spinner("Analyzing document metrics and formulating executive summary..."):
            # Construct a prompt for summary
            prompt = "Summarize the key financial findings of this report in detail. Structure it with sections: Executive Overview, Key Financial Strengths, Areas of Risk, and Strategic Recommendations."
            
            # Simple context snippet assembly
            years = metrics.get("years", [2025, 2024])
            context_summary = f"Financial Metrics Overview:\n"
            for y in years:
                ys = str(y)
                context_summary += f"Year {ys}: Revenue = {metrics['revenue'].get(ys, 0.0)}, Net Income = {metrics['net_income'].get(ys, 0.0)}, Assets = {metrics['assets'].get(ys, 0.0)}, Liabilities = {metrics['liabilities'].get(ys, 0.0)}, Equity = {metrics['equity'].get(ys, 0.0)}, Operating Cash Flow = {metrics['operating_cash_flow'].get(ys, 0.0)}.\n"
            
            # Retrieve small text snippet
            context_summary += f"\nDetailed Content Snippet:\n{doc['text_content'][:2000]}"
            
            ai_summary = query_ai(prompt, context_summary, st.session_state.get("gemini_api_key"))
            st.session_state[summary_key] = ai_summary
            
    summary_text = st.session_state[summary_key]
    
    # Display the summary inside a card
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown(summary_text)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("📥 Export Intelligence Package")
    
    # 2. Report Exporters
    col_exp = st.columns(2)
    
    with col_exp[0]:
        st.markdown("**Download PDF Report**")
        st.caption("Generates a formal, printable PDF document featuring parsed account tables, calculated ratios, risk logs, and the AI executive summary.")
        
        pdf_filename = f"Financial_Report_{doc['id']}.pdf"
        pdf_path = os.path.join(UPLOAD_DIR, pdf_filename)
        
        try:
            generate_pdf_report(metrics, ratios, risks, summary_text, pdf_path)
            with open(pdf_path, "rb") as pdf_file:
                st.download_button(
                    label="📥 Download Printable PDF",
                    data=pdf_file,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"Failed to generate PDF document: {e}")
            
    with col_exp[1]:
        st.markdown("**Download Excel Model**")
        st.caption("Exports clean, formatted spreadsheets using accounting borders, column adjustments, values formatting, and key indicators.")
        
        xls_filename = f"Financial_Model_{doc['id']}.xlsx"
        xls_path = os.path.join(UPLOAD_DIR, xls_filename)
        
        try:
            generate_excel_report(metrics, ratios, xls_path)
            with open(xls_path, "rb") as xls_file:
                st.download_button(
                    label="📥 Export Excel Spreadsheet",
                    data=xls_file,
                    file_name=xls_filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"Failed to generate Excel sheet: {e}")

if __name__ == "__main__":
    main()
