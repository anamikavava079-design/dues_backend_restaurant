import React, {useState, useEffect, useRef} from 'react';

const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";
export default function Chatbot() {
    const [messages, setMessages] = useState([
        { role:'bot', text: 'Hello! How can I assist you today?' }
    ]);
    const [input, setInput] = useState('');
    const [isTyping, setIsTyping] = useState(false);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };
    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMessage = inputText.trim();
        setInputText('');

        setMessages(prev => [...prev, { role: 'user', text: userMessage }]);
        setIsTyping(true);

        try {
            const response = await fetch(`${API_BASE_URL}/api/chat/`, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json",
          // Include authorization headers here if required later
            },
            body: JSON.stringify({ message: userMessage })
        });

        if (!response.ok) {
            throw new Error("Backend server error");
        }

        const data = await response.json();
      
      // 3. Update state with the backend response
        setMessages(prev => [...prev, { role: 'bot', text: data.reply }]);
    } catch (error) {
        console.error("Connection Error:", error);
        setMessages(prev => [...prev, { 
            role: 'bot', 
            text: "Sorry, I am facing trouble reaching the restaurant servers right now." 
        }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="messages-window">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <p>{msg.text}</p>
          </div>
        ))}
        {isTyping && <div className="typing-indicator">Deus Bot is typing...</div>}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSendMessage} className="input-area">
        <input 
          type="text" 
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Ask about our menu or place an order..."
        />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}

