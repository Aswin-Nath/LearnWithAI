import React, { useState, useEffect, useRef } from 'react';
import { apiFetch } from '../../core/api';
import './ChatPanel.css';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  intent?: string;
  timestamp: number;
}

interface ChatPanelProps {
  problemId: number;
  userCode: string;
  width: string;
  onDragStart: () => void;
  onCloseChat: () => void;
}

const INTENTS = [
  {
    id: 'how_to_solve_this',
    label: '💡 Approach',
    description: 'How to solve this',
    color: '#3498db'
  },
  {
    id: 'why_my_code_failed',
    label: '🐛 Debug',
    description: 'Why my code failed',
    color: '#e74c3c'
  },
  {
    id: 'explain_my_code',
    label: '📝 Explain',
    description: 'Explain my code',
    color: '#f39c12'
  },
  {
    id: 'validate_my_approach',
    label: '✓ Validate',
    description: 'Validate my approach',
    color: '#27ae60'
  },
  {
    id: 'clarification_request',
    label: '❓ Clarify',
    description: 'Clarify the problem',
    color: '#9b59b6'
  }
];

export const ChatPanel: React.FC<ChatPanelProps> = ({
  problemId,
  userCode,
  width,
  onDragStart,
  onCloseChat
}) => {
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [selectedIntent, setSelectedIntent] = useState<string | null>(null);
  const [chatLoading, setChatLoading] = useState(false);
  const chatMessagesRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
    }
  }, [chatMessages, chatLoading]);

  const handleSendMessage = async () => {
    if (!selectedIntent || !chatInput.trim()) return;

    try {
      setChatLoading(true);

      // Add user message to chat
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'user',
        content: chatInput,
        intent: selectedIntent,
        timestamp: Date.now(),
      };
      setChatMessages((prev) => [...prev, userMessage]);

      // Call the chat API
      const response = await apiFetch('/chat/ask', {
        method: 'POST',
        body: JSON.stringify({
          problem_id: problemId,
          user_code: userCode,
          user_query: chatInput,
          intent: selectedIntent,
        }),
      });

      const chatResponse = response.data || response;

      // Add assistant message to chat
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: chatResponse.answer || chatResponse,
        timestamp: Date.now(),
      };
      setChatMessages((prev) => [...prev, assistantMessage]);

      // Clear input
      setChatInput('');
    } catch (err) {
      console.error('Chat error:', err);
      const errorMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `Error: ${err instanceof Error ? err.message : 'Failed to get response'}`,
        timestamp: Date.now(),
      };
      setChatMessages((prev) => [...prev, errorMessage]);
    } finally {
      setChatLoading(false);
    }
  };

  return (
    <>
      {/* Vertical Divider */}
      <div
        className="editor-chat-divider"
        onMouseDown={onDragStart}
      />

      {/* Chat Section */}
      <div className="chat-section" style={{ width }}>
        {/* Header */}
        <div className="chat-header">
          <div className="chat-header-left">
            <span className="chat-avatar">🤖</span>
            <div>
              <h3>AI Problem Assistant</h3>
              <p className="chat-subtitle">Context-aware · Code-first · Interactive</p>
            </div>
          </div>

          <button
            className="chat-close-btn"
            onClick={onCloseChat}
            title="Hide chat (Alt+H)"
            aria-label="Close chat"
          >
            ×
          </button>
        </div>

        {/* Messages */}
        <div className="chat-messages" ref={chatMessagesRef}>
          {chatMessages.length === 0 ? (
            <div className="chat-message system">
              <strong>Welcome 👋</strong>
              <p>
                Select an intent below, write your code, and ask a question to get AI-powered guidance!
              </p>
            </div>
          ) : (
            chatMessages.map((msg) => (
              <div key={msg.id} className={`chat-message ${msg.role}`}>
                {msg.role === 'user' && msg.intent && (
                  <span className="intent-badge">
                    {INTENTS.find(i => i.id === msg.intent)?.label}
                  </span>
                )}
                <div className="message-content">
                  {msg.content}
                </div>
                <span className="message-time">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </span>
              </div>
            ))
          )}
          {chatLoading && (
            <div className="chat-message system">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
        </div>

        {/* Input */}
        <div className="chat-input-area">
          {/* Intent Buttons */}
          <div className="intent-buttons">
            {INTENTS.map((intent) => (
              <button
                key={intent.id}
                className={`intent-btn ${selectedIntent === intent.id ? 'active' : ''}`}
                onClick={() => setSelectedIntent(selectedIntent === intent.id ? null : intent.id)}
                title={intent.description}
                style={{
                  borderColor: selectedIntent === intent.id ? intent.color : '#ccc',
                  backgroundColor: selectedIntent === intent.id ? intent.color + '15' : 'transparent',
                  color: selectedIntent === intent.id ? intent.color : '#666'
                }}
              >
                {intent.label}
              </button>
            ))}
          </div>

          {/* Message Input */}
          <div className="message-input-row">
            <input
              type="text"
              className="chat-input"
              placeholder={selectedIntent ? 'Ask your question...' : 'Select an intent first...'}
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && !chatLoading && selectedIntent) {
                  handleSendMessage();
                }
              }}
              disabled={!selectedIntent || chatLoading}
            />
            <button
              className="chat-send-btn"
              onClick={handleSendMessage}
              disabled={!selectedIntent || !chatInput.trim() || chatLoading}
              title={selectedIntent ? 'Send message' : 'Select an intent first'}
            >
              {chatLoading ? '...' : 'Send'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
