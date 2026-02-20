import React, { useState } from 'react';
import Header from './components/Header';
import Overview from './components/Overview';
import RealTimeMonitor from './components/RealTimeMonitor';
import Transcripts from './components/Transcripts';
import KnowledgeBase from './components/KnowledgeBase';
import { ViewState } from './types';
import { COLORS } from './constants';

const App: React.FC = () => {
  const [activeView, setActiveView] = useState<ViewState>('overview');
  const [greeting, setGreeting] = useState("Hello, thank you for calling VocalQ.ai support.");
  const [savingGreeting, setSavingGreeting] = useState(false);
  const [saveStatus, setSaveStatus] = useState<string>('');

  React.useEffect(() => {
    fetch('http://localhost:8000/api/v1/admin/settings/greeting')
      .then(res => res.json())
      .then(data => {
        if (data.greeting) setGreeting(data.greeting);
      })
      .catch(console.error);
  }, []);

  const saveGreeting = async () => {
    setSavingGreeting(true);
    setSaveStatus('');
    try {
      const res = await fetch('http://localhost:8000/api/v1/admin/settings/greeting', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ greeting })
      });
      if (res.ok) {
        setSaveStatus('Saved successfully!');
        setTimeout(() => setSaveStatus(''), 3000);
      } else {
        setSaveStatus('Failed to save');
      }
    } catch (err) {
      console.error(err);
      setSaveStatus('Error saving');
    } finally {
      setSavingGreeting(false);
    }
  };

  const renderView = () => {
    switch (activeView) {
      case 'overview':
        return <Overview />;
      case 'realtime':
        return <RealTimeMonitor />;
      case 'transcripts':
        return <Transcripts />;
      case 'knowledge':
        return <KnowledgeBase />;
      case 'settings':
        return (
          <div style={{ maxWidth: '800px', margin: '0 auto' }}>
            <h2 style={{
              fontSize: '1.875rem',
              fontWeight: '700',
              color: COLORS.text,
              marginBottom: '0.5rem',
            }}>
              Settings
            </h2>
            <p style={{
              fontSize: '0.875rem',
              color: COLORS.textMuted,
              marginBottom: '2rem',
            }}>
              Configure your AI assistant and system preferences
            </p>

            <div style={{
              backgroundColor: COLORS.surface,
              borderRadius: '12px',
              padding: '1.5rem',
              boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
              borderTop: `3px solid ${COLORS.primary}`,
            }}>
              <h3 style={{
                fontSize: '1.125rem',
                fontWeight: '600',
                color: COLORS.text,
                marginBottom: '1rem',
              }}>
                AI Greeting Message
              </h3>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{
                  display: 'block',
                  fontSize: '0.875rem',
                  fontWeight: '500',
                  color: COLORS.textMuted,
                  marginBottom: '0.5rem',
                }}>
                  Greeting Text
                </label>
                <textarea
                  value={greeting}
                  onChange={(e) => setGreeting(e.target.value)}
                  rows={3}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: `1px solid ${COLORS.border}`,
                    borderRadius: '8px',
                    fontSize: '0.875rem',
                    color: COLORS.text,
                    resize: 'vertical',
                    fontFamily: 'inherit',
                  }}
                  placeholder="Enter the AI greeting message..."
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <button
                  onClick={saveGreeting}
                  disabled={savingGreeting}
                  style={{
                    padding: '0.625rem 1.5rem',
                    backgroundColor: COLORS.primary,
                    color: 'white',
                    border: 'none',
                    borderRadius: '8px',
                    fontWeight: '600',
                    fontSize: '0.875rem',
                    cursor: savingGreeting ? 'not-allowed' : 'pointer',
                    opacity: savingGreeting ? 0.6 : 1,
                  }}
                >
                  {savingGreeting ? 'Saving...' : 'Save Changes'}
                </button>
                {saveStatus && (
                  <span style={{
                    fontSize: '0.875rem',
                    color: saveStatus.includes('success') ? COLORS.success : COLORS.danger,
                    fontWeight: '500',
                  }}>
                    {saveStatus}
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      default:
        return <Overview />;
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      backgroundColor: COLORS.background,
    }}>
      <Header activeView={activeView} onViewChange={setActiveView} />

      <main style={{
        padding: '0 40px 40px',
        maxWidth: '1200px',
        margin: '0 auto',
      }}>
        {renderView()}
      </main>
    </div>
  );
};

export default App;
