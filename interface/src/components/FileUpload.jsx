import React, { useState, useRef } from 'react';
import { ingestFile } from '../api.js';

export default function FileUpload() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  function handleFileChange(e) {
    setFile(e.target.files[0] ?? null);
    setStatus(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file || loading) return;

    setLoading(true);
    setStatus(null);

    try {
      await ingestFile(file);
      setStatus({ type: 'success', message: `"${file.name}" ingested successfully.` });
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
    } catch (err) {
      setStatus({ type: 'error', message: `Failed to ingest: ${err.message}` });
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} style={styles.form}>
      <label style={styles.label}>Ingest Document</label>
      <div style={styles.row}>
        <input
          ref={inputRef}
          type="file"
          accept=".txt,.md,.pdf"
          onChange={handleFileChange}
          style={styles.fileInput}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={!file || loading}
          style={{
            ...styles.button,
            ...(!file || loading ? styles.buttonDisabled : {}),
          }}
        >
          {loading ? 'Ingesting...' : 'Ingest'}
        </button>
      </div>
      {status && (
        <p
          style={{
            ...styles.statusMsg,
            color: status.type === 'success' ? '#4caf82' : '#e05c5c',
          }}
        >
          {status.message}
        </p>
      )}
    </form>
  );
}

const styles = {
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    padding: '14px 20px',
    backgroundColor: '#0e1119',
    borderBottom: '1px solid #1e2435',
  },
  label: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#8b92a5',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  fileInput: {
    flex: 1,
    fontSize: '13px',
    color: '#c0c4d0',
    backgroundColor: '#1a1f2e',
    border: '1px solid #2a3040',
    borderRadius: '6px',
    padding: '7px 10px',
    cursor: 'pointer',
  },
  button: {
    padding: '8px 18px',
    borderRadius: '6px',
    border: 'none',
    backgroundColor: '#f5c518',
    color: '#0d0d0d',
    fontSize: '13px',
    fontWeight: '700',
    cursor: 'pointer',
    whiteSpace: 'nowrap',
    transition: 'background-color 0.15s',
  },
  buttonDisabled: {
    backgroundColor: '#3a3a2a',
    color: '#666',
    cursor: 'not-allowed',
  },
  statusMsg: {
    margin: '0',
    fontSize: '13px',
  },
};
