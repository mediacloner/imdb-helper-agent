import React from 'react';

export default function StepList({ steps }) {
  if (!steps || steps.length === 0) return null;

  return (
    <div style={styles.container}>
      <p style={styles.heading}>Steps:</p>
      <ol style={styles.list}>
        {steps.map((step, index) => {
          const stepNumber = step.step_number ?? index + 1;
          const description = step.node_description ?? step.description ?? '';
          const interactionType = step.interaction_type ?? step.action?.interaction_type ?? '';
          const rawTarget = step.target_element ?? step.action?.target_element_id ?? step.target ?? '';
          // Hide internal graph IDs (contain __ or start with state_)
          const targetElement = (rawTarget.includes('__') || rawTarget.startsWith('state_')) ? '' : rawTarget;

          return (
            <li key={index} style={styles.item}>
              <span style={styles.stepNum}>Step {stepNumber}</span>
              {description && (
                <span style={styles.description}>{description}</span>
              )}
              {(interactionType || targetElement) && (
                <span style={styles.action}>
                  {interactionType && (
                    <span style={styles.badge}>{interactionType}</span>
                  )}
                  {targetElement && (
                    <span style={styles.target}>{targetElement}</span>
                  )}
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

const styles = {
  container: {
    marginTop: '10px',
    backgroundColor: '#1a1f2e',
    borderRadius: '6px',
    padding: '12px 16px',
    border: '1px solid #2a3040',
  },
  heading: {
    margin: '0 0 8px 0',
    fontSize: '13px',
    fontWeight: '600',
    color: '#8b92a5',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  list: {
    margin: '0',
    padding: '0',
    listStyle: 'none',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  item: {
    display: 'flex',
    flexDirection: 'column',
    gap: '3px',
    padding: '8px 10px',
    backgroundColor: '#222736',
    borderRadius: '5px',
    border: '1px solid #2d3348',
  },
  stepNum: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#f5c518',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
  },
  description: {
    fontSize: '14px',
    color: '#d4d8e2',
    lineHeight: '1.4',
  },
  action: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginTop: '2px',
  },
  badge: {
    fontSize: '11px',
    color: '#4a9eff',
    backgroundColor: '#1a2d45',
    borderRadius: '3px',
    padding: '1px 6px',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.03em',
  },
  target: {
    fontSize: '12px',
    color: '#8b92a5',
    fontFamily: 'monospace',
  },
};
