"""
Faculty Pulse Chatbot - Streamlit Web Interface
Interactive web application for querying Haverford College faculty database
"""
import streamlit as st
import os
import pandas as pd
import json
from io import BytesIO
from dotenv import load_dotenv
from chatbot import FacultyPulseChatbot
from datetime import datetime

# Load environment variables from .env file
load_dotenv()


# Page configuration
st.set_page_config(
    page_title="Faculty Pulse Chatbot",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern, professional UI
st.markdown("""
<style>
    /* Global Styles */
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        color: #2C3E50;
        background-color: #F8F9FA;
    }

    .main {
        background-color: #F8F9FA;
    }

    .block-container {
        padding: 2rem 1rem;
        max-width: 900px;
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: #F8F9FA;
    }

    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #8B0000 0%, #A52A2A 100%);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #A52A2A 0%, #8B0000 100%);
    }

    /* Header Styles */
    .college-name {
        font-size: 1rem;
        font-weight: 600;
        color: #8B0000;
        text-align: center;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 0.5rem;
        padding-top: 1rem;
    }

    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #8B0000 0%, #A52A2A 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
        padding: 0.5rem 0;
    }

    .subtitle {
        text-align: center;
        color: #6C757D;
        font-size: 1.125rem;
        margin-bottom: 2rem;
        font-weight: 400;
        line-height: 1.6;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
    }

    /* Message Bubbles */
    .user-message {
        background: linear-gradient(135deg, #8B0000 0%, #A52A2A 100%);
        color: white;
        padding: 1.25rem 1.5rem;
        border-radius: 18px 18px 4px 18px;
        margin: 0.75rem 0;
        box-shadow: 0 4px 6px -1px rgba(139, 0, 0, 0.3),
                    0 2px 4px -1px rgba(139, 0, 0, 0.2);
        max-width: 80%;
        margin-left: auto;
        position: relative;
        animation: slideInRight 0.3s ease-out;
        line-height: 1.6;
    }

    .user-message strong {
        font-weight: 600;
        display: block;
        margin-bottom: 0.5rem;
        font-size: 0.875rem;
        opacity: 0.9;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    .assistant-message {
        background: white;
        color: #2C3E50;
        padding: 1.25rem 1.5rem;
        border-radius: 18px 18px 18px 4px;
        margin: 0.75rem 0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1),
                    0 2px 4px -1px rgba(0, 0, 0, 0.06);
        border-left: 4px solid #27AE60;
        max-width: 85%;
        position: relative;
        animation: slideInLeft 0.3s ease-out;
        line-height: 1.6;
    }

    .assistant-message strong {
        font-weight: 600;
        display: block;
        margin-bottom: 0.5rem;
        color: #27AE60;
        font-size: 0.875rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    /* Sidebar Styles */
    [data-testid="stSidebar"] {
        background-color: #F8F9FA;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #2C3E50;
        font-weight: 600;
    }

    [data-testid="stSidebar"] [data-testid="stMetric"] {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
        border: 1px solid #DEE2E6;
    }

    [data-testid="stSidebar"] [data-testid="stMetricValue"] {
        color: #8B0000;
        font-size: 1.875rem;
        font-weight: 700;
    }

    /* Stats Box */
    .stats-box {
        background: linear-gradient(135deg, #FFF5F5 0%, #FFE4E4 100%);
        padding: 1.25rem;
        border-radius: 12px;
        margin: 1rem 0;
        border: 1px solid rgba(139, 0, 0, 0.1);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }

    .stats-box h4 {
        color: #2C3E50;
        font-weight: 600;
        margin-bottom: 0.75rem;
        font-size: 1rem;
    }

    .stats-box ul {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .stats-box li {
        padding: 0.5rem 0;
        color: #6C757D;
        border-bottom: 1px solid rgba(0, 0, 0, 0.05);
    }

    .stats-box li:last-child {
        border-bottom: none;
    }

    /* Button Styles */
    .stButton > button {
        background: linear-gradient(135deg, #8B0000 0%, #A52A2A 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.625rem 1.5rem;
        font-weight: 600;
        font-size: 0.9375rem;
        box-shadow: 0 4px 6px -1px rgba(139, 0, 0, 0.3);
        transition: all 0.2s ease-in-out;
        cursor: pointer;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(139, 0, 0, 0.4);
    }

    .stButton > button:active {
        transform: translateY(0);
    }

    /* Chat Input */
    [data-testid="stChatInput"] {
        border-radius: 12px;
        border: 2px solid #DEE2E6;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease-in-out;
    }

    [data-testid="stChatInput"]:focus-within {
        border-color: #8B0000;
        box-shadow: 0 4px 6px -1px rgba(139, 0, 0, 0.2);
    }

    /* Select and Slider Elements */
    .stSelectbox [data-baseweb="select"] {
        border-radius: 8px;
        border-color: #DEE2E6;
        transition: all 0.2s ease-in-out;
    }

    .stSelectbox [data-baseweb="select"]:hover {
        border-color: #8B0000;
    }

    .stSlider [role="slider"] {
        background: linear-gradient(135deg, #8B0000 0%, #A52A2A 100%);
    }

    /* Info and Error Boxes */
    .stInfo {
        background: linear-gradient(135deg, rgba(93, 173, 226, 0.1) 0%, rgba(52, 152, 219, 0.1) 100%);
        border-left: 4px solid #5DADE2;
        padding: 1rem 1.25rem;
        border-radius: 8px;
        color: #2C3E50;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(93, 173, 226, 0.1);
    }

    .stError {
        background: linear-gradient(135deg, rgba(231, 76, 60, 0.1) 0%, rgba(192, 57, 43, 0.1) 100%);
        border-left: 4px solid #E74C3C;
        padding: 1rem 1.25rem;
        border-radius: 8px;
        margin: 1rem 0;
        box-shadow: 0 2px 4px rgba(231, 76, 60, 0.1);
    }

    /* Spinner */
    [data-testid="stSpinner"] {
        border-color: #8B0000 !important;
    }

    [data-testid="stSpinner"] > div {
        border-top-color: #8B0000 !important;
    }

    /* Caption/Metadata */
    .stCaption {
        color: #ADB5BD;
        font-size: 0.875rem;
        margin-top: 0.5rem;
        padding: 0.5rem 0;
    }

    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, #DEE2E6, transparent);
        margin: 1.5rem 0;
    }

    /* Focus States */
    *:focus {
        outline: 2px solid #8B0000;
        outline-offset: 2px;
    }

    button:focus-visible,
    input:focus-visible,
    select:focus-visible {
        outline: 2px solid #8B0000;
        outline-offset: 2px;
    }

    /* Responsive Design */
    @media (max-width: 768px) {
        .main-header {
            font-size: 2rem;
        }

        .subtitle {
            font-size: 1rem;
        }

        .user-message,
        .assistant-message {
            max-width: 95%;
            padding: 1rem 1.25rem;
        }
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize Streamlit session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "chatbot" not in st.session_state:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            st.error("⚠️ ANTHROPIC_API_KEY environment variable not set. Please configure your API key.")
            st.stop()
        st.session_state.chatbot = FacultyPulseChatbot(api_key=api_key)

    if "stats" not in st.session_state:
        st.session_state.stats = st.session_state.chatbot.get_database_stats()

    if "last_results" not in st.session_state:
        st.session_state.last_results = None

    if "last_num_results" not in st.session_state:
        st.session_state.last_num_results = 0

    if "show_export" not in st.session_state:
        st.session_state.show_export = False


def display_message(role: str, content: str):
    """Display a chat message with appropriate styling"""
    if role == "user":
        st.markdown(f'<div class="user-message"><strong>👤 You</strong>{content}</div>',
                   unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message"><strong>🤖 Assistant</strong>{content}</div>',
                   unsafe_allow_html=True)


def create_export_data(results_data, max_results=None):
    """Create exportable data from query results

    Args:
        results_data: Raw results from ChromaDB
        max_results: Maximum number of results to export (limits to top N results used in response)
    """
    try:
        if not results_data or 'documents' not in results_data or 'metadatas' not in results_data:
            st.warning("⚠️ No data available for export")
            return None

        # ChromaDB returns nested lists, so we need to flatten them
        documents = results_data['documents']
        metadatas = results_data['metadatas']

        # Handle nested list structure from ChromaDB
        if isinstance(documents, list) and len(documents) > 0:
            if isinstance(documents[0], list):
                documents = documents[0]

        if isinstance(metadatas, list) and len(metadatas) > 0:
            if isinstance(metadatas[0], list):
                metadatas = metadatas[0]

        # Verify we have data
        if not documents or not metadatas or len(documents) == 0:
            st.warning("⚠️ No results to export")
            return None

        if len(documents) != len(metadatas):
            st.error(f"❌ Data mismatch: {len(documents)} documents but {len(metadatas)} metadata entries")
            return None

        # Limit to max_results if specified (export only what was shown to user)
        if max_results and max_results > 0:
            documents = documents[:max_results]
            metadatas = metadatas[:max_results]

        export_rows = []
        for idx, (doc, meta) in enumerate(zip(documents, metadatas)):
            try:
                # Extract title from metadata or document content
                title = meta.get('title', 'N/A')
                if title == 'N/A' or (title and len(title) > 400):
                    if doc and 'Publication Title:' in doc:
                        lines = doc.split('\n')
                        for line in lines:
                            if 'Publication Title:' in line:
                                title = line.replace('Publication Title:', '').strip()
                                break

                # Limit title length for clean display
                title = title[:200] if title and title != 'N/A' else title

                # Extract a brief description from the document (first 300 chars, not full content)
                description = 'N/A'
                if doc:
                    # Try to get abstract or a short description
                    if 'Abstract:' in doc:
                        # Extract abstract section
                        abstract_start = doc.find('Abstract:')
                        description_text = doc[abstract_start + 9:].strip()
                        # Get first 300 characters of abstract
                        description = description_text[:300]
                        if len(description_text) > 300:
                            description += '...'
                    else:
                        # Just take first 300 chars of document
                        description = doc[:300]
                        if len(doc) > 300:
                            description += '...'

                # Build basic row with essential metadata
                row = {
                    'Author': meta.get('faculty_name', 'N/A'),
                    'Department': meta.get('department', 'N/A'),
                    'Type': meta.get('content_type', 'N/A'),
                    'Title': title,
                    'Date': meta.get('date_published', 'N/A'),
                    'Description': description,
                }

                # Add type-specific URL/DOI field
                if meta.get('content_type') == 'Publication':
                    doi = meta.get('doi', '')
                    pdf_url = meta.get('pdf_url', '')
                    # Prefer DOI, fallback to PDF URL
                    if doi:
                        row['DOI/URL'] = f"https://doi.org/{doi}" if not doi.startswith('http') else doi
                    elif pdf_url:
                        row['DOI/URL'] = pdf_url
                    else:
                        row['DOI/URL'] = 'N/A'

                    # Add venue and citations for publications
                    row['Venue'] = meta.get('venue', 'N/A')
                    row['Citations'] = meta.get('cited_by_count', 'N/A')
                else:
                    # For non-publications, use source URL
                    row['DOI/URL'] = meta.get('source', 'N/A')

                export_rows.append(row)
            except Exception as row_error:
                st.warning(f"⚠️ Skipped row {idx+1} due to error: {str(row_error)}")
                continue

        df = pd.DataFrame(export_rows)

        if df.empty:
            st.warning("⚠️ No data to export")
            return None

        return df

    except Exception as e:
        st.error(f"❌ Error creating export data: {str(e)}")
        import traceback
        st.text(traceback.format_exc())
        return None


def export_to_excel(df):
    """Export dataframe to Excel file"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Faculty Data')
    output.seek(0)
    return output


def export_to_csv(df):
    """Export dataframe to CSV file"""
    return df.to_csv(index=False).encode('utf-8')


def main():
    """Main application function"""
    # Initialize session state
    initialize_session_state()

    # Header
    st.markdown('<div class="college-name">Haverford College</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-header">🎓 Faculty Pulse Chatbot</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Ask questions about Haverford College faculty, their publications, awards, and talks</div>',
               unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        # Database statistics
        st.subheader("📊 Database Statistics")
        stats = st.session_state.stats
        st.metric("Total Documents", stats['total_documents'])

        if stats['content_types']:
            st.write("**Content Types:**")
            for content_type, count in stats['content_types'].items():
                st.write(f"- {content_type}: {count}")

        if stats['departments']:
            st.write("**Departments:**")
            for dept in stats['departments']:
                if dept != "Unknown":
                    st.write(f"- {dept}")

        st.divider()

        # Query filters
        st.subheader("🔍 Query Filters")

        # Number of results
        n_results = st.slider(
            "Number of results to retrieve",
            min_value=1,
            max_value=10,
            value=5,
            help="How many relevant documents to retrieve from the database"
        )

        # Content type filter
        content_type_options = ["All"] + list(stats['content_types'].keys())
        content_type_filter = st.selectbox(
            "Filter by content type",
            content_type_options,
            help="Filter results by type of content"
        )
        content_type = None if content_type_filter == "All" else content_type_filter

        # Department filter (exclude "Unknown" from options)
        department_options = ["All"] + [dept for dept in stats['departments'] if dept != "Unknown"]
        department_filter = st.selectbox(
            "Filter by department",
            department_options,
            help="Filter results by department"
        )
        department = None if department_filter == "All" else department_filter

        st.divider()

        # Export info
        st.info("💡 Include 'export' or 'spreadsheet' in your query to download results")

        st.divider()

        # Reset conversation button
        if st.button("🔄 Reset Conversation", use_container_width=True):
            st.session_state.chatbot.reset_conversation()
            st.session_state.messages = []
            st.session_state.show_export = False
            st.rerun()

        # Example queries
        st.subheader("💡 Example Questions")
        st.markdown("""
        - What awards have faculty received?
        - Tell me about publications in Computer Science
        - Which faculty members have given talks?
        - What are Dr. [Name]'s recent achievements?
        - Show me research about [topic]
        """)

    # Main chat area
    chat_container = st.container()

    # Display chat history
    with chat_container:
        if not st.session_state.messages:
            st.info("👋 Welcome! Ask me anything about Haverford College faculty members, their research, awards, and presentations.")
        else:
            for message in st.session_state.messages:
                display_message(message["role"], message["content"])

            # Show metadata for the last query
            if st.session_state.last_num_results > 0:
                st.caption(f"📚 Found {st.session_state.last_num_results} relevant document(s) in the database")

    # Export section - OUTSIDE chat_container so it persists after rerun
    if st.session_state.show_export and st.session_state.last_results and st.session_state.last_num_results > 0:
        st.divider()
        st.subheader("📥 Export Results")

        # Only export the top N results that were actually used in the response
        df = create_export_data(st.session_state.last_results, st.session_state.last_num_results)

        if df is not None and not df.empty:
            col1, col2, col3 = st.columns(3)

            with col1:
                csv_data = export_to_csv(df)
                st.download_button(
                    label="📄 Download CSV",
                    data=csv_data,
                    file_name=f"faculty_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="csv_download"
                )

            with col2:
                excel_data = export_to_excel(df)
                st.download_button(
                    label="📊 Download Excel",
                    data=excel_data,
                    file_name=f"faculty_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="excel_download"
                )

            with col3:
                json_data = df.to_json(orient='records', indent=2)
                st.download_button(
                    label="📋 Download JSON",
                    data=json_data,
                    file_name=f"faculty_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True,
                    key="json_download"
                )

            # Show preview
            with st.expander(f"👁️ Preview Data ({len(df)} rows)"):
                st.dataframe(df, use_container_width=True)

    # Chat input
    user_input = st.chat_input("Ask a question about faculty...")

    if user_input:
        # Check if user is requesting export/spreadsheet
        user_input_lower = user_input.lower()
        export_keywords = ['spreadsheet', 'export']
        # Enable export ONLY when explicitly requested (not persistent)
        # Reset to False first, then check if current query requests it
        st.session_state.show_export = False
        if any(keyword in user_input_lower for keyword in export_keywords):
            st.session_state.show_export = True

        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Show user message immediately
        with chat_container:
            display_message("user", user_input)

        # Generate response
        with st.spinner("🤔 Searching database and generating response..."):
            try:
                result = st.session_state.chatbot.chat(
                    user_query=user_input,
                    n_results=n_results,
                    content_type=content_type,
                    department=department
                )

                response = result['response']
                num_results = result['num_results']

                # Store the raw results for export
                if 'database_results' in result:
                    st.session_state.last_results = result['database_results']
                    st.session_state.last_num_results = num_results

                # Add assistant message to history
                st.session_state.messages.append({"role": "assistant", "content": response})

                # Show assistant response
                with chat_container:
                    display_message("assistant", response)

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.error("💡 Tip: If the chatbot keeps failing, try resetting the conversation using the button in the sidebar.")
                # Log the full error for debugging
                import traceback
                st.expander("🔍 Error Details").code(traceback.format_exc())

        # Rerun to update the chat
        st.rerun()


if __name__ == "__main__":
    main()
