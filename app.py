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

# Custom CSS for better chat UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subtitle {
        text-align: center;
        color: #666;
        margin-bottom: 2rem;
    }
    .user-message {
        background-color: #e3f2fd;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    .assistant-message {
        background-color: #f5f5f5;
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #4caf50;
    }
    .stats-box {
        background-color: #fff3e0;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
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
        st.markdown(f'<div class="user-message">👤 <strong>You:</strong><br/>{content}</div>',
                   unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="assistant-message">🤖 <strong>Assistant:</strong><br/>{content}</div>',
                   unsafe_allow_html=True)


def main():
    """Main application function"""
    # Initialize session state
    initialize_session_state()

    # Header
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
