import React, { useState, useEffect, useRef } from 'react';
import { apiFetch } from '../../core/api';
import './ChatPanel.css';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: number;
}

interface ChatPanelProps {
  problemId: number;
  userCode: string;
  width: string;
  onDragStart: () => void;
  onCloseChat: () => void;
  chatMessages: ChatMessage[];
  onChatMessagesChange: (messages: ChatMessage[]) => void;
  chatInput: string;
  onChatInputChange: (input: string) => void;
}

// Enhanced markdown to JSX converter with support for emoji bullet points
const parseMarkdownContent = (content: string): React.ReactNode[] => {
  const elements: React.ReactNode[] = [];
  const lines = content.split('\n');
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Code blocks
    if (line.trim().startsWith('```')) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      if (codeLines.length > 0) {
        elements.push(
          <pre key={`code-${i}`} className="code-block">
            <code>{codeLines.join('\n')}</code>
          </pre>
        );
      }
      i++;
      continue;
    }

    // Headings
    if (line.startsWith('###')) {
      elements.push(
        <h3 key={`h3-${i}`}>{line.replace(/^###\s*/, '').trim()}</h3>
      );
      i++;
      continue;
    }
    if (line.startsWith('##')) {
      elements.push(
        <h2 key={`h2-${i}`}>{line.replace(/^##\s*/, '').trim()}</h2>
      );
      i++;
      continue;
    }
    if (line.startsWith('#')) {
      elements.push(
        <h1 key={`h1-${i}`}>{line.replace(/^#\s*/, '').trim()}</h1>
      );
      i++;
      continue;
    }

    // Separators
    if (line.trim().match(/^(-{3,}|={3,}|\*{3,})$/)) {
      elements.push(<hr key={`hr-${i}`} style={{ margin: '12px 0', border: 'none', borderTop: '1px solid #ddd' }} />);
      i++;
      continue;
    }

    // Bullet lists with emoji support (both • and * markers)
    if ((line.trim().startsWith('•') || line.trim().startsWith('*')) && line.trim().length > 1) {
      const listItems: React.ReactNode[] = [];
      while (i < lines.length && (lines[i].trim().startsWith('•') || lines[i].trim().startsWith('*'))) {
        const itemText = lines[i].trim().substring(1).trim();
        const formattedItem = formatInlineMarkdown(itemText);
        listItems.push(
          <li key={i} className="emoji-bullet-item">
            {formattedItem}
          </li>
        );
        i++;
      }
      elements.push(
        <ul key={`list-${i}`} className="emoji-bullet-list">
          {listItems}
        </ul>
      );
      continue;
    }

    // Empty lines
    if (line.trim() === '') {
      i++;
      continue;
    }

    // Regular paragraphs with inline formatting
    if (line.trim().length > 0) {
      const formattedLine = formatInlineMarkdown(line);
      elements.push(
        <p key={`p-${i}`} style={{ margin: '8px 0' }}>
          {formattedLine}
        </p>
      );
    }
    i++;
  }

  return elements.length > 0 ? elements : [content];
};

const formatInlineMarkdown = (text: string): React.ReactNode => {
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;

  // Match **bold**, *italic*, and `code`
  const regex = /\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`/g;
  let match;

  while ((match = regex.exec(text)) !== null) {
    // Add text before match
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    // Add formatted text
    if (match[1]) {
      // Bold
      parts.push(<strong key={`bold-${match.index}`}>{match[1]}</strong>);
    } else if (match[2]) {
      // Italic
      parts.push(<em key={`italic-${match.index}`}>{match[2]}</em>);
    } else if (match[3]) {
      // Inline code
      parts.push(
        <span key={`code-${match.index}`} className="inline-code">
          {match[3]}
        </span>
      );
    }

    lastIndex = regex.lastIndex;
  }

  // Add remaining text
  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts.length > 0 ? parts : text;
};

const defaultPlaceholder = 'Ask your question about the problem...';

export const ChatPanel: React.FC<ChatPanelProps> = ({
  problemId,
  userCode,
  width,
  onDragStart,
  onCloseChat,
  chatMessages,
  onChatMessagesChange,
  chatInput,
  onChatInputChange
}) => {
  const [chatLoading, setChatLoading] = useState(false);
  const chatMessagesRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    if (chatMessagesRef.current) {
      chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight;
    }
  }, [chatMessages, chatLoading]);

  const handleSendMessage = async () => {
    if (!chatInput.trim()) return;

    try {
      setChatLoading(true);

      // Add user message to chat
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'user',
        content: chatInput,
        timestamp: Date.now(),
      };
      onChatMessagesChange([...chatMessages, userMessage]);

      // Call the chat API (intent will be auto-classified by backend)
      const response = await apiFetch('/chat/ask', {
        method: 'POST',
        body: JSON.stringify({
          problem_id: problemId,
          user_code: userCode,
          user_query: chatInput,
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
      onChatMessagesChange([...chatMessages, userMessage, assistantMessage]);

      // Clear input
      onChatInputChange('');
    } catch (err) {
      console.error('Chat error:', err);
      const errorMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'assistant',
        content: `Error: ${err instanceof Error ? err.message : 'Failed to get response'}`,
        timestamp: Date.now(),
      };
      onChatMessagesChange([...chatMessages, errorMessage]);
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
              <h3>AI Explanation Assistant</h3>
              <p className="chat-subtitle">Judge decides · AI explains</p>
            </div>
          </div>

          <button
            className="chat-close-btn"
            onClick={() => {
              // Just hide the chat panel, keep the session history
              onCloseChat();
            }}
            title="Hide chat (Alt+H)"
            aria-label="Close chat"
          >
            x
          </button>
        </div>

        {/* Messages */}
        <div className="chat-messages" ref={chatMessagesRef}>
          {chatMessages.length === 0 ? (
            <div className="chat-message system">
              <strong>Welcome 👋</strong>
              <p>
                Write your code and ask questions to get AI-powered guidance! The system will automatically understand what you need.
              </p>
            </div>
          ) : (
            chatMessages.map((msg) => (
              <div key={msg.id} className={`chat-message ${msg.role}`}>
                <div className="message-content markdown-content">
                  {msg.role === 'assistant' ? parseMarkdownContent(msg.content) : msg.content}
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
          {/* Message Input */}
          <div className="message-input-row">
            <input
              type="text"
              className="chat-input"
              placeholder={defaultPlaceholder}
              value={chatInput}
              onChange={(e) => onChatInputChange(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey && !chatLoading) {
                  handleSendMessage();
                }
              }}
              disabled={chatLoading}
            />
            <button
              className="chat-send-btn"
              onClick={handleSendMessage}
              disabled={!chatInput.trim() || chatLoading}
              title="Send message"
            >
              {chatLoading ? '...' : 'Send'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
};
