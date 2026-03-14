import React from 'react';
import Chat from './components/Chat.jsx';
import FileUpload from './components/FileUpload.jsx';

export default function App() {
  return (
    <div style={styles.root}>
      <header style={styles.header}>
        <div style={styles.logoMark}>
          <span style={styles.logoText}>IMDb</span>
        </div>
        <div>
          <h1 style={styles.title}>IMDB UI Helper</h1>
          <p style={styles.subtitle}>Ask me how to navigate and use IMDB</p>
        </div>
      </header>

      <main style={styles.main}>
        <FileUpload />
        <Chat />
      </main>
    </div>
  );
}

const styles = {
  root: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#0a0c14',
    color: '#e0e4f0',
    fontFamily: "'Segoe UI', system-ui, -apple-system, sans-serif",
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    padding: '18px 24px',
    backgroundColor: '#0d1017',
    borderBottom: '2px solid #f5c518',
    flexShrink: 0,
  },
  logoMark: {
    backgroundColor: '#f5c518',
    borderRadius: '6px',
    padding: '5px 10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoText: {
    color: '#0d0d0d',
    fontSize: '18px',
    fontWeight: '900',
    letterSpacing: '-0.5px',
  },
  title: {
    margin: '0',
    fontSize: '20px',
    fontWeight: '700',
    color: '#ffffff',
    lineHeight: '1.2',
  },
  subtitle: {
    margin: '2px 0 0 0',
    fontSize: '13px',
    color: '#8b92a5',
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    maxWidth: '900px',
    width: '100%',
    margin: '0 auto',
    padding: '20px',
    boxSizing: 'border-box',
    gap: '0',
    minHeight: '0',
  },
};
