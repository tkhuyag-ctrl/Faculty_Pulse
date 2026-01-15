"""
Run chatbot with .env file support
"""
import os
import sys
from pathlib import Path

# Load .env file
env_file = Path(__file__).parent / '.env'
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

# Now run the chatbot
from chatbot import FacultyPulseChatbot

if __name__ == "__main__":
    print("\n" + "="*60)
    print("FACULTY PULSE CHATBOT - Terminal Mode")
    print("="*60)
    print("\nInitializing chatbot...")

    try:
        chatbot = FacultyPulseChatbot()
        print("✓ Chatbot initialized successfully!")
        print(f"✓ Database has {chatbot.db_manager.collection.count()} documents")
        print("\nRAG System: Enabled (adaptive truncation up to 30K chars)")
        print("\nType 'quit' or 'exit' to stop\n")

        # Interactive loop
        while True:
            try:
                query = input("\n🔍 Your question: ").strip()

                if query.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye!")
                    break

                if not query:
                    continue

                print("\n" + "-"*60)
                result = chatbot.chat(query)
                print(f"\n💬 Response:\n{result['response']}")
                print(f"\n📊 Found {result['num_results']} relevant documents")
                print("-"*60)

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")

    except Exception as e:
        print(f"\n✗ Error initializing chatbot: {e}")
        sys.exit(1)
