import React, { useState, useRef, useEffect } from 'react';
import Chat from './components/Chat.jsx';
import TestRunner from './components/TestRunner.jsx';

export default function App() {
  const [view, setView] = useState(() =>
    window.location.hash === '#tests' ? 'tests' : 'chat'
  );
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    function onHash() {
      setView(window.location.hash === '#tests' ? 'tests' : 'chat');
    }
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  useEffect(() => {
    function handle(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    }
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, []);

  const navigate = (target) => {
    window.location.hash = target === 'tests' ? '#tests' : '';
    setView(target);
    setMenuOpen(false);
  };

  return (
    <div style={styles.root}>
      <header style={styles.header}>
        <div style={styles.logoMark} onClick={() => navigate('chat')} role="button" tabIndex={0}>
          <span style={styles.logoText}>IMDb</span>
        </div>
        <div>
          <h1 style={styles.title}>IMDB UI Helper</h1>
          <p style={styles.subtitle}>
            {view === 'tests' ? 'Test Runner — benchmark the RAG system' : 'Ask me how to navigate and use IMDB'}
          </p>
        </div>

        {/* Hamburger */}
        <div ref={menuRef} style={styles.menuWrap}>
          <button
            style={styles.hamburger}
            onClick={() => setMenuOpen(o => !o)}
            aria-label="Menu"
          >
            <span style={styles.bar} />
            <span style={styles.bar} />
            <span style={styles.bar} />
          </button>

          {menuOpen && (
            <div style={styles.dropdown}>
              <div style={styles.dropTitle}>Developer Tools</div>

              <div
                style={styles.dropItem}
                onClick={() => navigate('chat')}
                onMouseEnter={e => e.currentTarget.style.background = '#1e2235'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <span style={styles.dropIcon}>💬</span>
                <div>
                  <div style={styles.dropLabel}>Chat</div>
                  <div style={styles.dropDesc}>Ask how to navigate IMDB</div>
                </div>
              </div>

              <div
                style={styles.dropItem}
                onClick={() => navigate('tests')}
                onMouseEnter={e => e.currentTarget.style.background = '#1e2235'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
              >
                <span style={styles.dropIcon}>🧪</span>
                <div>
                  <div style={styles.dropLabel}>Test Runner</div>
                  <div style={styles.dropDesc}>Run benchmarks & view AI judge scores</div>
                </div>
              </div>

              <a
                href="http://localhost:8000/dashboard/"
                target="_blank"
                rel="noreferrer"
                style={styles.dropItem}
                onMouseEnter={e => e.currentTarget.style.background = '#1e2235'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                onClick={() => setMenuOpen(false)}
              >
                <span style={styles.dropIcon}>📊</span>
                <div>
                  <div style={styles.dropLabel}>Full Dashboard</div>
                  <div style={styles.dropDesc}>Charts & detailed analysis (localhost:8765)</div>
                </div>
              </a>
            </div>
          )}
        </div>
      </header>

      <main style={styles.main}>
        {view === 'chat' ? <Chat /> : <TestRunner />}
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
    position: 'relative',
  },
  logoMark: {
    backgroundColor: '#f5c518',
    borderRadius: '6px',
    padding: '5px 10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
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
    maxWidth: '1100px',
    width: '100%',
    margin: '0 auto',
    padding: '20px',
    boxSizing: 'border-box',
    minHeight: '0',
  },
  /* Hamburger button */
  menuWrap: {
    marginLeft: 'auto',
    position: 'relative',
  },
  hamburger: {
    background: 'transparent',
    border: '1px solid #2a2e42',
    borderRadius: '8px',
    padding: '8px 10px',
    cursor: 'pointer',
    display: 'flex',
    flexDirection: 'column',
    gap: '5px',
    alignItems: 'center',
  },
  bar: {
    display: 'block',
    width: '22px',
    height: '2px',
    backgroundColor: '#e0e4f0',
    borderRadius: '2px',
  },

  /* Dropdown */
  dropdown: {
    position: 'absolute',
    top: 'calc(100% + 8px)',
    right: 0,
    width: '280px',
    background: '#131620',
    border: '1px solid #2a2e42',
    borderRadius: '10px',
    boxShadow: '0 8px 32px rgba(0,0,0,.6)',
    zIndex: 1000,
    overflow: 'hidden',
  },
  dropTitle: {
    padding: '10px 16px',
    fontSize: '10px',
    fontWeight: '700',
    color: '#f5c518',
    textTransform: 'uppercase',
    letterSpacing: '.8px',
    borderBottom: '1px solid #2a2e42',
  },
  dropItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    padding: '12px 16px',
    cursor: 'pointer',
    textDecoration: 'none',
    color: 'inherit',
    background: 'transparent',
    transition: 'background .15s',
    borderBottom: '1px solid #1a1e2e',
  },
  dropIcon: {
    fontSize: '18px',
    flexShrink: 0,
    marginTop: '1px',
  },
  dropLabel: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#e0e4f0',
    marginBottom: '2px',
  },
  dropDesc: {
    fontSize: '11px',
    color: '#8890a8',
  },
};
