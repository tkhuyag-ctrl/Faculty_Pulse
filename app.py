"""
Faculty Pulse Chatbot - Streamlit Web Interface
Interactive web application for querying Haverford College faculty database
"""
import streamlit as st
import os
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


def display_message(role: str, content: str):
    """Display a chat message with appropriate styling"""
    if role == "user":
        st.markdown(f'<div class="user-message"><strong>👤 You</strong>{content}</div>',
                   unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message"><strong>🤖 Assistant</strong>{content}</div>',
                   unsafe_allow_html=True)


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

        # Department filter
        department_options = ["All"] + stats['departments']
        department_filter = st.selectbox(
            "Filter by department",
            department_options,
            help="Filter results by department"
        )
        department = None if department_filter == "All" else department_filter

        st.divider()

        # Reset conversation button
        if st.button("🔄 Reset Conversation", use_container_width=True):
            st.session_state.chatbot.reset_conversation()
            st.session_state.messages = []
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

    # Chat input
    user_input = st.chat_input("Ask a question about faculty...")

    if user_input:
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

                # Add assistant message to history
                st.session_state.messages.append({"role": "assistant", "content": response})

                # Show assistant response
                with chat_container:
                    display_message("assistant", response)

                    # Show metadata
                    st.caption(f"📚 Found {num_results} relevant document(s) in the database")

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
