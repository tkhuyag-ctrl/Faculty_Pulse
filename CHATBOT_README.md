# Faculty Pulse Chatbot 🎓

An interactive chatbot interface for querying the Haverford College faculty database using natural language. Built with Streamlit and powered by Anthropic's Claude AI.

## Features

✨ **Natural Language Interface** - Ask questions in plain English
🤖 **AI-Powered Responses** - Claude generates conversational, context-aware answers
🔍 **Semantic Search** - Find relevant faculty information by meaning, not just keywords
🎯 **Smart Filtering** - Filter by content type (Awards, Publications, Talks) and department
💬 **Conversation History** - Maintains context across multiple questions
📊 **Real-time Statistics** - View database statistics in the sidebar

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- `streamlit` - Web interface framework
- `anthropic` - Claude AI API client
- `chromadb` - Vector database
- Other supporting libraries

### 2. Set Up Anthropic API Key

You need an Anthropic API key to use Claude. Get one at: https://console.anthropic.com/

Set the environment variable:

**On Windows (Command Prompt):**
```bash
set ANTHROPIC_API_KEY=your-api-key-here
```

**On Windows (PowerShell):**
```bash
$env:ANTHROPIC_API_KEY="your-api-key-here"
```

**On macOS/Linux:**
```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

**Permanent Setup (recommended):**
Create a `.env` file in the project directory:
```
ANTHROPIC_API_KEY=your-api-key-here
```

### 3. Ensure Database Has Data

Make sure your ChromaDB database (`./chroma_db/`) has faculty data. If you need to add data, use the existing scripts:

```bash
# Extract text from URLs and add to database
python data_extractor.py your_urls.json

# View what's in the database
python view_db_summary.py
```

## Usage

### Running the Chatbot

**Web Interface (Streamlit):**
```bash
streamlit run app.py
```

This will:
1. Start a local web server
2. Open the chatbot interface in your browser (usually http://localhost:8501)
3. Display the interactive chat interface

**Command Line Test:**
```bash
python chatbot.py
```

This runs a simple test query to verify everything is working.

### Using the Web Interface

1. **Ask Questions** - Type your question in the chat input at the bottom
   - "What awards have faculty members received?"
   - "Tell me about publications in Computer Science"
   - "Which faculty gave talks on machine learning?"

2. **Adjust Filters** (Sidebar)
   - **Number of results**: How many relevant documents to retrieve (1-10)
   - **Content type**: Filter by Awards, Publications, or Talks
   - **Department**: Filter by specific department

3. **View Statistics** (Sidebar)
   - Total documents in database
   - Breakdown by content type
   - List of departments

4. **Reset Conversation** - Click "Reset Conversation" to start fresh

### Example Questions

```
General queries:
- What awards have faculty received recently?
- Tell me about research publications
- Which faculty members have given talks?

Specific queries:
- What has Dr. [Name] published?
- Show me Computer Science publications
- What awards were given in 2026?

Filtered queries:
- (Set filter to "Publications" + "Computer Science")
  "Tell me about recent research"
```

## Architecture

### Files

- **[app.py](app.py)** - Streamlit web interface
- **[chatbot.py](chatbot.py)** - Core chatbot logic with Claude integration
- **[chroma_manager.py](chroma_manager.py)** - ChromaDB database manager
- **[requirements.txt](requirements.txt)** - Python dependencies

### How It Works

```
User Question
     ↓
Streamlit Interface (app.py)
     ↓
Chatbot Logic (chatbot.py)
     ↓
1. Query ChromaDB (semantic search)
     ↓
2. Retrieve relevant documents
     ↓
3. Format results for Claude
     ↓
4. Generate natural language response
     ↓
Display to User
```

### Key Components

**FacultyPulseChatbot class** (`chatbot.py`):
- `chat()` - Main entry point for queries
- `query_database()` - Searches ChromaDB
- `generate_response()` - Calls Claude API
- `get_database_stats()` - Returns database statistics

**Streamlit Interface** (`app.py`):
- Chat interface with message history
- Sidebar with filters and statistics
- Session state management
- Real-time response generation

## Configuration

### Adjusting Claude Model

Edit [chatbot.py:131](chatbot.py#L131) to change the Claude model:

```python
model="claude-3-5-sonnet-20241022",  # Current model
# Other options:
# model="claude-3-opus-20240229",    # Most capable
# model="claude-3-haiku-20240307",   # Fastest
```

### Customizing Search Results

Edit the `n_results` parameter in `chat()` method:

```python
# In chatbot.py
def chat(self, user_query: str, n_results: int = 5):
    # Change default number of results
```

### Conversation History Length

Edit [chatbot.py:147](chatbot.py#L147):

```python
if len(self.conversation_history) > 20:  # 10 exchanges
    # Adjust to keep more or fewer previous messages
```

## API Costs

The chatbot uses Anthropic's Claude API, which has costs based on usage:

- **Claude 3.5 Sonnet**: ~$3 per million input tokens, ~$15 per million output tokens
- Typical query: ~1,000-2,000 tokens (input + output)
- Cost per query: ~$0.01-$0.03

Monitor your usage at: https://console.anthropic.com/

## Troubleshooting

### "ANTHROPIC_API_KEY not found"
- Make sure you've set the environment variable
- Verify the key is correct
- Try restarting your terminal/IDE after setting the variable

### "No relevant information found"
- The database might be empty - check with `python view_db_summary.py`
- Your query might not match the database content - try rephrasing
- Adjust filters in the sidebar - they might be too restrictive

### Streamlit won't start
- Make sure you installed dependencies: `pip install -r requirements.txt`
- Check if port 8501 is already in use
- Try: `streamlit run app.py --server.port 8502`

### Claude API errors
- Check your API key is valid
- Verify you have API credits available
- Check Anthropic's status page: https://status.anthropic.com/

### Database connection issues
- Ensure `./chroma_db/` directory exists
- Check directory permissions
- Try clearing and recreating: `python clear_db_demo.py`

## Advanced Usage

### Programmatic Access

```python
from chatbot import FacultyPulseChatbot

# Initialize
chatbot = FacultyPulseChatbot(api_key="your-key")

# Ask a question
result = chatbot.chat("What awards have faculty received?")
print(result['response'])
print(f"Found {result['num_results']} relevant documents")

# Use filters
result = chatbot.chat(
    "Tell me about research",
    content_type="Publication",
    department="Computer Science",
    n_results=3
)

# Reset conversation
chatbot.reset_conversation()
```

### Custom System Prompt

Edit the `system_prompt` in [chatbot.py:91-107](chatbot.py#L91-L107) to customize how Claude responds:

```python
system_prompt = """You are a helpful assistant...
[Customize the instructions here]
"""
```

### Integration with Other Systems

The chatbot can be integrated with:
- Discord/Slack bots
- Web applications (Flask/Django)
- REST APIs
- Mobile apps

Example REST API wrapper:
```python
from flask import Flask, request, jsonify
from chatbot import FacultyPulseChatbot

app = Flask(__name__)
chatbot = FacultyPulseChatbot()

@app.route('/chat', methods=['POST'])
def chat():
    query = request.json['query']
    result = chatbot.chat(query)
    return jsonify(result)
```

## Security Notes

1. **API Key Protection**: Never commit your API key to version control
2. **Rate Limiting**: Consider adding rate limiting for production use
3. **Input Validation**: The chatbot validates inputs, but add extra validation for public-facing deployments
4. **Database Access**: Ensure only authorized users can query the database

## Performance Tips

1. **Reduce n_results**: Use fewer results (3-5) for faster queries
2. **Use Filters**: Apply content type/department filters to narrow search
3. **Cache Common Queries**: Implement caching for frequently asked questions
4. **Model Selection**: Use Claude Haiku for faster, cheaper responses if quality allows

## Contributing

To add features or improvements:

1. Test with existing data: `python chatbot.py`
2. Test the web interface: `streamlit run app.py`
3. Ensure error handling works
4. Update this README with new features

## License

MIT License

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the main project README
3. Check Anthropic's documentation: https://docs.anthropic.com/
4. Check Streamlit's documentation: https://docs.streamlit.io/

---

**Happy Chatting! 🎓🤖**
