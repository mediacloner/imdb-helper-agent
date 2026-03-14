import React, { useState, useRef, useEffect } from 'react';
import Message from './Message.jsx';
import { sendQuery, recordSteps } from '../api.js';

export default function Chat() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! Ask me anything about how to use IMDB — searching for movies, managing watchlists, ratings, and more.',
      steps: [],
      videoUrl: null,
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  async function handleSubmit(e) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    const userMessage = { role: 'user', content: question, steps: [], videoUrl: null };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const data = await sendQuery(question);
      const steps = data.steps ?? [];
      const assistantMessage = {
        role: 'assistant',
        content: data.answer ?? data.response ?? data.text ?? JSON.stringify(data),
        steps,
        videoUrl: null,
        recordingVideo: steps.length > 0,
      };
      setMessages((prev) => [...prev, assistantMessage]);

      if (steps.length > 0) {
        const videoUrl = await recordSteps(steps);
        setMessages((prev) =>
          prev.map((m, i) =>
            i === prev.length - 1 ? { ...m, videoUrl, recordingVideo: false } : m
          )
        );
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Sorry, something went wrong: ${err.message}`,
          steps: [],
          videoUrl: null,
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.messageList}>
        {messages.map((msg, i) => (
          <Message key={i} message={msg} />
        ))}
        {loading && (
          <div style={styles.typingWrapper}>
            <div style={styles.typingAvatar}>AI</div>
            <div style={styles.typingBubble}>
              <span style={styles.dot} />
              <span style={{ ...styles.dot, animationDelay: '0.2s' }} />
              <span style={{ ...styles.dot, animationDelay: '0.4s' }} />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form onSubmit={handleSubmit} style={styles.form}>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask how to do something on IMDB..."
          style={styles.input}
          disabled={loading}
          autoComplete="off"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          style={{
            ...styles.button,
            ...(loading || !input.trim() ? styles.buttonDisabled : {}),
          }}
        >
          {loading ? '...' : 'Send'}
        </button>
      </form>

      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40% { transform: translateY(-6px); opacity: 1; }
        }
        .md-content p { margin: 0 0 8px 0; }
        .md-content p:last-child { margin-bottom: 0; }
        .md-content a { color: #4a9eff; text-decoration: underline; }
        .md-content ul, .md-content ol { margin: 6px 0 6px 20px; padding: 0; }
        .md-content li { margin-bottom: 4px; }
        .md-content code { background: #1a1f2e; border-radius: 3px; padding: 1px 5px; font-size: 14px; color: #f5c518; }
        .md-content pre { background: #1a1f2e; border-radius: 5px; padding: 10px; overflow-x: auto; }
        .md-content pre code { background: none; padding: 0; }
        .md-content strong { color: #fff; }
        .md-content h1, .md-content h2, .md-content h3 { margin: 10px 0 6px 0; color: #f5c518; }
      `}</style>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
    overflow: 'hidden',
    backgroundColor: '#12151f',
    borderRadius: '10px',
    border: '1px solid #1e2435',
  },
  messageList: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px',
    display: 'flex',
    flexDirection: 'column',
  },
  typingWrapper: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    marginBottom: '16px',
  },
  typingAvatar: {
    flexShrink: 0,
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    backgroundColor: '#f5c518',
    color: '#0d0d0d',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '11px',
    fontWeight: '700',
    marginTop: '2px',
  },
  typingBubble: {
    backgroundColor: '#1e2435',
    border: '1px solid #2a3040',
    borderRadius: '12px',
    borderTopLeftRadius: '3px',
    padding: '14px 18px',
    display: 'flex',
    alignItems: 'center',
    gap: '5px',
  },
  dot: {
    display: 'inline-block',
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    backgroundColor: '#8b92a5',
    animation: 'bounce 1.2s infinite ease-in-out',
  },
  form: {
    display: 'flex',
    gap: '10px',
    padding: '16px 20px',
    borderTop: '1px solid #1e2435',
    backgroundColor: '#0e1119',
  },
  input: {
    flex: 1,
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1px solid #2a3040',
    backgroundColor: '#1a1f2e',
    color: '#e0e4f0',
    fontSize: '17px',
    outline: 'none',
    transition: 'border-color 0.15s',
  },
  button: {
    padding: '12px 24px',
    borderRadius: '8px',
    border: 'none',
    backgroundColor: '#f5c518',
    color: '#0d0d0d',
    fontSize: '17px',
    fontWeight: '700',
    cursor: 'pointer',
    transition: 'background-color 0.15s',
    whiteSpace: 'nowrap',
  },
  buttonDisabled: {
    backgroundColor: '#3a3a2a',
    color: '#666',
    cursor: 'not-allowed',
  },
};
