import React from 'react';
import ReactMarkdown from 'react-markdown';
import StepList from './StepList.jsx';

export default function Message({ message }) {
  const { role, content, steps, videoUrl, recordingVideo } = message;
  const isAssistant = role === 'assistant';

  return (
    <div style={{ ...styles.wrapper, justifyContent: isAssistant ? 'flex-start' : 'flex-end' }}>
      {isAssistant && <div style={styles.avatar}>AI</div>}
      <div
        style={{
          ...styles.bubble,
          ...(isAssistant ? styles.assistantBubble : styles.userBubble),
        }}
      >
        <div style={styles.content} className="md-content">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>

        {isAssistant && steps && steps.length > 0 && (
          <StepList steps={steps} />
        )}

        {isAssistant && recordingVideo && (
          <div style={styles.videoContainer}>
            <p style={styles.videoLabel}>⏺ Recording tutorial video...</p>
          </div>
        )}

        {isAssistant && videoUrl && (
          <div style={styles.videoContainer}>
            <p style={styles.videoLabel}>Tutorial Video</p>
            <video
              src={videoUrl}
              controls
              autoPlay
              style={styles.video}
              preload="auto"
            >
              Your browser does not support the video element.
            </video>
          </div>
        )}
      </div>
      {!isAssistant && <div style={styles.userAvatar}>You</div>}
    </div>
  );
}

const styles = {
  wrapper: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    marginBottom: '16px',
  },
  avatar: {
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
  userAvatar: {
    flexShrink: 0,
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    backgroundColor: '#4a9eff',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '10px',
    fontWeight: '700',
    marginTop: '2px',
  },
  bubble: {
    maxWidth: '75%',
    borderRadius: '12px',
    padding: '12px 16px',
    lineHeight: '1.5',
  },
  assistantBubble: {
    backgroundColor: '#1e2435',
    border: '1px solid #2a3040',
    borderTopLeftRadius: '3px',
  },
  userBubble: {
    backgroundColor: '#1a3a5c',
    border: '1px solid #2050a0',
    borderTopRightRadius: '3px',
  },
  content: {
    margin: '0',
    fontSize: '17px',
    color: '#e0e4f0',
    wordBreak: 'break-word',
  },
  videoContainer: {
    marginTop: '12px',
  },
  videoLabel: {
    margin: '0 0 6px 0',
    fontSize: '12px',
    fontWeight: '600',
    color: '#8b92a5',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  video: {
    width: '100%',
    borderRadius: '6px',
    border: '1px solid #2a3040',
    backgroundColor: '#000',
    maxHeight: '300px',
  },
};
