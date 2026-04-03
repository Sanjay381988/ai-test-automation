import { useState, useEffect } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL ?? '';

// Safe helpers — prevent React crash when LLM returns objects instead of strings
const safeStr = (val) => {
  if (val === null || val === undefined) return '';
  if (typeof val === 'string') return val;
  if (Array.isArray(val)) return val.map(safeStr).join(' ');
  if (typeof val === 'object') return val.scenario || val.name || val.description || val.title || val.text || JSON.stringify(val);
  return String(val);
};
const safeList = (val) => {
  if (!val) return [];
  if (Array.isArray(val)) return val.map(item => safeStr(item));
  if (typeof val === 'string') return val.split('\n').filter(s => s.trim());
  if (typeof val === 'object') return Object.values(val).map(v => safeStr(v));
  return [String(val)];
};

function App() {
  const [theme, setTheme] = useState('dark');
  const [currentStep, setCurrentStep] = useState(1);
  
  // LLM State (Step 1)
  const [llmProvider, setLlmProvider] = useState('GROQ');
  const [llmApiKey, setLlmApiKey] = useState('');
  const [llmUrl, setLlmUrl] = useState('http://localhost:11434');
  const [llmModel, setLlmModel] = useState('llama3-8b-8192');
  const [llmStatus, setLlmStatus] = useState(null);

  // ALM State (Step 2)
  const [almUrl, setAlmUrl] = useState('https://your-domain.atlassian.net');
  const [almEmail, setAlmEmail] = useState('');
  const [almToken, setAlmToken] = useState('');
  const [almStatus, setAlmStatus] = useState(null);

  // Ticket & Context (Step 3)
  const [ticketId, setTicketId] = useState('');
  const [context, setContext] = useState('');

  // Dashboard / Result (Step 4)
  const [genStatus, setGenStatus] = useState('');
  const [downloadLink, setDownloadLink] = useState('');
  const [downloadMdLink, setDownloadMdLink] = useState('');
  const [finalData, setFinalData] = useState(null);
  const [finalHtml, setFinalHtml] = useState(null);

  // Confluence State
  const [confluenceUrl, setConfluenceUrl] = useState('');
  const [confluenceSpace, setConfluenceSpace] = useState('KAN');
  const [confStatus, setConfStatus] = useState('');
  const [confLink, setConfLink] = useState('');

  // History
  const [history, setHistory] = useState(() => {
    try { return JSON.parse(localStorage.getItem('testplan_history') || '[]'); } catch { return []; }
  });
  const [showHistory, setShowHistory] = useState(false);

  // Preview State
  const [previewData, setPreviewData] = useState(null);
  const [previewHtml, setPreviewHtml] = useState(null);
  const [previewMdLink, setPreviewMdLink] = useState('');
  const [previewStatus, setPreviewStatus] = useState('');
  const [previewTab, setPreviewTab] = useState('json');

  // Globals
  const [toast, setToast] = useState('');

  useEffect(() => {
    document.body.className = theme;
  }, [theme]);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(''), 4000);
  }

  // Handshake Methods
  const testLLM = async () => {
    setLlmStatus('testing');
    try {
      const res = await fetch(`${API_BASE}/api/test-llm`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ provider: llmProvider, url: llmUrl, api_key: llmApiKey })
      });
      if(res.ok) {
        setLlmStatus('success');
        showToast('✅ LLM Connection Successful!');
        setTimeout(() => setCurrentStep(2), 1000); // Auto advance
      } else {
        setLlmStatus('error');
        showToast('❌ LLM Connection Failed');
      }
    } catch(e) {
      setLlmStatus('error');
      showToast('❌ LLM Connection Failed');
    }
  };

  const testALM = async () => {
    setAlmStatus('testing');
    try {
      const res = await fetch(`${API_BASE}/api/test-alm`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ provider: 'Jira', url: almUrl, email: almEmail, token: almToken })
      });
      if(res.ok) {
        setAlmStatus('success');
        showToast('✅ Jira Connection Successful!');
        setTimeout(() => setCurrentStep(3), 1000); // Auto advance
      } else {
        setAlmStatus('error');
        showToast('❌ Jira Connection Failed');
      }
    } catch(e) {
      setAlmStatus('error');
      showToast('❌ Jira Connection Failed');
    }
  };

  const previewPlan = async () => {
    if(!ticketId) return showToast('⚠️ Please enter a Jira Ticket ID');
    setPreviewStatus('generating');
    setPreviewData(null);
    try {
      const res = await fetch(`${API_BASE}/api/preview`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          alm_provider: 'Jira',
          alm_url: almUrl,
          alm_email: almEmail,
          alm_token: almToken,
          llm_provider: llmProvider,
          llm_model: llmModel,
          llm_api_key: llmApiKey,
          llm_url: llmUrl,
          ticket_id: ticketId,
          additional_context: context
        })
      });
      const data = await res.json();
      if(res.ok) {
        setPreviewStatus('success');
        setPreviewData(data.data);
        setPreviewHtml(data.html);
        setPreviewMdLink(`${API_BASE}/api/download/${data.md_file}`);
        showToast('✨ Preview Generated Successfully!');
      } else {
        setPreviewStatus('error');
        showToast('❌ Preview Failed: ' + data.detail);
      }
    } catch(e) {
      setPreviewStatus('error');
      showToast('❌ Preview Failed: Server Error');
    }
  }

  const addToHistory = (ticketId, fileName, data) => {
    const entry = {
      id: Date.now(),
      ticketId,
      fileName,
      timestamp: new Date().toLocaleString(),
      objective: data?.objective || '',
      scenarioCount: Array.isArray(data?.test_scenarios) ? data.test_scenarios.length : 0
    };
    setHistory(prev => {
      const updated = [entry, ...prev].slice(0, 20);
      localStorage.setItem('testplan_history', JSON.stringify(updated));
      return updated;
    });
  };

  const pushToConfluence = async () => {
    if(!confluenceSpace) return showToast('⚠️ Enter a Confluence Space Key');
    setConfStatus('pushing');
    const effectiveConfUrl = confluenceUrl.trim() || almUrl;
    try {
      const res = await fetch(`${API_BASE}/api/confluence`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          alm_url: effectiveConfUrl,
          alm_email: almEmail,
          alm_token: almToken,
          space_key: confluenceSpace,
          ticket_id: ticketId,
          content: finalData
        })
      });
      const data = await res.json();
      if(res.ok) {
        setConfStatus('success');
        setConfLink(data.link);
        showToast('🚀 Pushed to Confluence!');
      } else {
        setConfStatus('error');
        showToast('❌ Confluence Push Failed');
      }
    } catch(e) {
      setConfStatus('error');
      showToast('❌ Server Error');
    }
  }

  const generatePlan = async () => {
    if(!ticketId) return showToast('⚠️ Please enter a Jira Ticket ID');
    setCurrentStep(4);
    setGenStatus('generating');
    setDownloadLink('');
    setDownloadMdLink('');
    setFinalData(null);
    setFinalHtml(null);
    setConfStatus('');
    setConfLink('');
    try {
      const res = await fetch(`${API_BASE}/api/generate`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          alm_provider: 'Jira',
          alm_url: almUrl,
          alm_email: almEmail,
          alm_token: almToken,
          llm_provider: llmProvider,
          llm_model: llmModel,
          llm_api_key: llmApiKey,
          llm_url: llmUrl,
          ticket_id: ticketId,
          additional_context: context
        })
      });
      const data = await res.json();
      if(res.ok) {
        setFinalData(data.data);
        setDownloadLink(`${API_BASE}/api/download/${data.file_name}`);
        setDownloadMdLink(`${API_BASE}/api/download/${data.md_file}`);
        setFinalHtml(data.html);
        addToHistory(ticketId, data.file_name, data.data);
        showToast('✨ Test Plan Generated Successfully!');
        setGenStatus('success');
      } else {
        setGenStatus('error');
        showToast('❌ Generation Failed: ' + data.detail);
      }
    } catch(e) {
      setGenStatus('error');
      showToast('❌ Generation Failed: Server Error');
    }
  }

  return (
    <div className={`app-layout ${theme}`}>
      {/* Left Sidebar Panel */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="logo">🚀 Dashboard</span>
          <button className="theme-toggle" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
          </button>
        </div>

        <nav className="steps-nav">
          <div className={`step-item ${currentStep === 1 && !showHistory ? 'active' : ''} ${llmStatus === 'success' ? 'completed' : ''}`} onClick={() => { setShowHistory(false); setCurrentStep(1); }}>
            <div className="step-indicator">1</div>
            <div className="step-details">
              <span className="step-title">LLM Engine</span>
              <span className="step-status">{llmStatus === 'success' ? 'Connected ✓' : llmStatus === 'error' ? 'Failed ✗' : 'Pending Setup'}</span>
            </div>
          </div>

          <div className={`step-item ${currentStep === 2 && !showHistory ? 'active' : ''} ${almStatus === 'success' ? 'completed' : ''}`} onClick={() => { setShowHistory(false); setCurrentStep(2); }}>
            <div className="step-indicator">2</div>
            <div className="step-details">
              <span className="step-title">Jira (ALM) Server</span>
              <span className="step-status">{almStatus === 'success' ? 'Connected ✓' : almStatus === 'error' ? 'Failed ✗' : 'Pending Auth'}</span>
            </div>
          </div>

          <div className={`step-item ${currentStep === 3 && !showHistory ? 'active' : ''} ${ticketId ? 'completed' : ''}`} onClick={() => { setShowHistory(false); setCurrentStep(3); }}>
            <div className="step-indicator">3</div>
            <div className="step-details">
              <span className="step-title">Story Context</span>
              <span className="step-status">{ticketId ? `Ticket: ${ticketId} ✓` : 'Define Scope'}</span>
            </div>
          </div>

          <div className={`step-item ${currentStep === 4 && !showHistory ? 'active' : ''}`} onClick={() => { setShowHistory(false); setCurrentStep(4); }}>
            <div className="step-indicator">4</div>
            <div className="step-details">
              <span className="step-title">Generation Dashboard</span>
              <span className="step-status">Final Output</span>
            </div>
          </div>

          <div style={{ marginTop: '1rem', borderTop: '1px solid var(--border)', paddingTop: '1rem' }}>
            <div className={`step-item ${showHistory ? 'active' : ''}`} onClick={() => setShowHistory(true)}>
              <div className="step-indicator" style={{ fontSize: '1rem' }}>📋</div>
              <div className="step-details">
                <span className="step-title">History</span>
                <span className="step-status">{history.length} plan{history.length !== 1 ? 's' : ''} generated</span>
              </div>
            </div>
          </div>
        </nav>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">

        {/* History Panel */}
        {showHistory && (
          <div className="step-container slide-in">
            <h2>📋 Generation History</h2>
            <p className="subtitle">All test plans generated in this session and previous sessions.</p>
            {history.length === 0 ? (
              <div className="form-card" style={{ textAlign: 'center', padding: '3rem' }}>
                <span style={{ fontSize: '3rem' }}>🕐</span>
                <h3>No history yet</h3>
                <p style={{ color: 'var(--text-sub)' }}>Generated test plans will appear here.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '800px' }}>
                {history.map(entry => (
                  <div key={entry.id} className="form-card" style={{ padding: '1.25rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                        <span style={{ background: 'var(--accent)', color: '#fff', padding: '0.2rem 0.6rem', borderRadius: '0.3rem', fontSize: '0.8rem', fontWeight: 700 }}>{entry.ticketId}</span>
                        <span style={{ color: 'var(--text-sub)', fontSize: '0.8rem' }}>{entry.timestamp}</span>
                        <span style={{ color: '#10b981', fontSize: '0.8rem' }}>{entry.scenarioCount} scenarios</span>
                      </div>
                      {entry.objective && (
                        <p style={{ margin: 0, color: 'var(--text-main)', fontSize: '0.9rem', lineHeight: 1.5 }}>{entry.objective.slice(0, 120)}{entry.objective.length > 120 ? '...' : ''}</p>
                      )}
                    </div>
                    <a href={`${API_BASE}/api/download/${entry.fileName}`} download style={{ textDecoration: 'none', padding: '0.5rem 1rem', background: '#22c55e', color: '#fff', borderRadius: '0.4rem', fontWeight: 600, fontSize: '0.85rem', whiteSpace: 'nowrap' }}>📥 Download</a>
                  </div>
                ))}
                <button onClick={() => { setHistory([]); localStorage.removeItem('testplan_history'); }} style={{ alignSelf: 'flex-start', background: 'transparent', border: '1px solid #ef4444', color: '#ef4444', padding: '0.5rem 1rem', borderRadius: '0.4rem', cursor: 'pointer', fontSize: '0.85rem' }}>🗑️ Clear History</button>
              </div>
            )}
          </div>
        )}
        
        {currentStep === 1 && (
          <div className="step-container slide-in">
            <h2>Step 1: Connect to Knowledge Engine (LLM)</h2>
            <p className="subtitle">Select your AI provider to power test case logic.</p>
            
            <div className="form-card">
              <div className="input-group">
                <label>Provider</label>
                <select value={llmProvider} onChange={e => {setLlmProvider(e.target.value); setLlmStatus(null);}}>
                  <option>GROQ</option>
                  <option>Ollama (Local)</option>
                  <option>MOCK LLM (For UI Testing)</option>
                </select>
              </div>
              
              <div className="input-group">
                <label>Model Engine</label>
                <input type="text" value={llmModel} onChange={e => setLlmModel(e.target.value)} />
              </div>

              {llmProvider === 'GROQ' ? (
                <div className="input-group">
                  <label>GROQ API Key</label>
                  <input type="password" placeholder="gsk_..." value={llmApiKey} onChange={e => setLlmApiKey(e.target.value)} />
                </div>
              ) : (
                <div className="input-group">
                  <label>Ollama End Point URL</label>
                  <input type="text" value={llmUrl} onChange={e => setLlmUrl(e.target.value)} />
                </div>
              )}
              
              <button className={`btn primary mt-4 ${llmStatus === 'testing' ? 'loading' : ''}`} onClick={testLLM}>
                {llmStatus === 'testing' ? 'Testing Connection...' : 'Verify LLM Connection'}
              </button>
            </div>
          </div>
        )}

        {currentStep === 2 && (
          <div className="step-container slide-in">
            <h2>Step 2: Connect to Jira (ALM)</h2>
            <p className="subtitle">Authenticate with Jira to automatically fetch feature details.</p>
            
            <div className="form-card">
              <div className="input-group">
                <label>Jira Server URL</label>
                <input type="text" placeholder="https://company.atlassian.net" value={almUrl} onChange={e => setAlmUrl(e.target.value)} />
              </div>
              <div className="input-group">
                <label>Jira User Email</label>
                <input type="email" placeholder="qa@company.com" value={almEmail} onChange={e => setAlmEmail(e.target.value)} />
              </div>
              <div className="input-group">
                <label>Jira API Token</label>
                <input type="password" placeholder="Auth Token" value={almToken} onChange={e => setAlmToken(e.target.value)} />
              </div>
              
              <button className={`btn primary mt-4 ${almStatus === 'testing' ? 'loading' : ''}`} onClick={testALM}>
                 {almStatus === 'testing' ? 'Testing Jira...' : 'Authorize Jira Server'}
              </button>
            </div>
          </div>
        )}

        {currentStep === 3 && (
          <div className="step-container slide-in">
            <h2>Step 3: Define Context</h2>
            <p className="subtitle">Specify the Jira Issue to test and any specific QA directives.</p>
            
            <div className="form-card">
              <div className="input-group">
                <label>Jira Ticket ID (Target)</label>
                <input type="text" placeholder="e.g. AUTH-4022" value={ticketId} onChange={e => setTicketId(e.target.value)} />
              </div>
              <div className="input-group">
                <label>Additional Testing Context (Optional)</label>
                <textarea rows="5" placeholder="E.g., Require strict OWASP checks, or ignore UI issues..." value={context} onChange={e => setContext(e.target.value)}></textarea>
              </div>

              <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                <button className={`btn outline ${previewStatus === 'generating' ? 'loading' : ''}`} style={{ flex: 1 }} onClick={previewPlan}>
                  {previewStatus === 'generating' ? 'Fetching Preview...' : 'Preview Plan'}
                </button>
                <button className="btn primary" style={{ flex: 1 }} onClick={generatePlan}>
                  Produce Full .Docx Plan
                </button>
              </div>

              {previewData && (
                <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                  <button className={`btn ${previewTab === 'json' ? 'primary' : 'outline'}`} style={{ flex: 1 }} onClick={() => setPreviewTab('json')}>Raw JSON Data</button>
                  <button className={`btn ${previewTab === 'html' ? 'primary' : 'outline'}`} style={{ flex: 1 }} onClick={() => setPreviewTab('html')}>Confluence Format</button>
                </div>
              )}

              {previewData && previewTab === 'json' && (
                <div className="preview-box fade-in" style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.1)' }}>
                  <h3 style={{ marginTop: 0, color: '#60a5fa' }}>Live API Output</h3>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', color: 'var(--text-main)', maxHeight: '300px', overflowY: 'auto' }}>
                    {JSON.stringify(previewData, null, 2)}
                  </pre>
                </div>
              )}
              
              {previewHtml && previewTab === 'html' && (
                 <div className="preview-box fade-in" style={{ marginTop: '1rem', padding: '1rem', background: '#ffffff', color: '#1f2937', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.1)', textAlign: 'left' }}>
                   <div dangerouslySetInnerHTML={{ __html: previewHtml }} style={{ maxHeight: '300px', overflowY: 'auto' }} />
                 </div>
              )}

              {previewMdLink && (
                <div style={{ marginTop: '1rem' }}>
                  <a href={previewMdLink} download className="btn outline" style={{ display: 'block', textAlign: 'center', textDecoration: 'none', background: 'rgba(16, 185, 129, 0.1)', borderColor: '#10b981', color: '#10b981' }}>
                    📥 Download Preview as Markdown (.md)
                  </a>
                </div>
              )}
            </div>
          </div>
        )}

        {currentStep === 4 && (
          <div className="step-container slide-in">
            <h2>Dashboard: Test Execution</h2>
            <p className="subtitle">Realtime AI generation tracking.</p>

            {/* Always-visible quick-status bar */}
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1.5rem', maxWidth: '800px' }}>
              <div style={{ flex: 1, minWidth: '140px', padding: '0.75rem 1rem', borderRadius: '0.6rem', background: llmStatus === 'success' ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.08)', border: `1px solid ${llmStatus === 'success' ? '#10b981' : '#ef4444'}`, fontSize: '0.85rem', fontWeight: 600, color: llmStatus === 'success' ? '#10b981' : '#ef4444', textAlign: 'center' }}>
                {llmStatus === 'success' ? '✅ LLM Ready' : '⚠️ LLM Not Set'}
              </div>
              <div style={{ flex: 1, minWidth: '140px', padding: '0.75rem 1rem', borderRadius: '0.6rem', background: almStatus === 'success' ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.08)', border: `1px solid ${almStatus === 'success' ? '#10b981' : '#ef4444'}`, fontSize: '0.85rem', fontWeight: 600, color: almStatus === 'success' ? '#10b981' : '#ef4444', textAlign: 'center' }}>
                {almStatus === 'success' ? '✅ Jira Ready' : '⚠️ Jira Not Set'}
              </div>
              <div style={{ flex: 1, minWidth: '140px', padding: '0.75rem 1rem', borderRadius: '0.6rem', background: ticketId ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.08)', border: `1px solid ${ticketId ? '#10b981' : '#ef4444'}`, fontSize: '0.85rem', fontWeight: 600, color: ticketId ? '#10b981' : '#ef4444', textAlign: 'center' }}>
                {ticketId ? `✅ Ticket: ${ticketId}` : '⚠️ No Ticket'}
              </div>
              {llmStatus === 'success' && almStatus === 'success' && ticketId && genStatus !== 'generating' && genStatus !== 'success' && (
                <button className="btn primary" style={{ flex: 1, minWidth: '160px' }} onClick={generatePlan}>
                  🚀 Generate Now
                </button>
              )}
            </div>
            
            <div className="form-card dashboard-card">
              {genStatus === 'generating' && (
                <div className="status-box loading">
                  <div className="spinner"></div>
                  <h3>Creating structured logic...</h3>
                  <p>Fetching ALM, calling LLM, mapping properties into Docx Template.</p>
                </div>
              )}

              {genStatus === 'error' && (
                <div className="status-box error">
                  <span className="huge-icon">⚠️</span>
                  <h3>Failed Generation</h3>
                  <p>Check the notification for exact API errors.</p>
                  <button className="btn primary mt-4" onClick={() => setCurrentStep(3)}>Try Again</button>
                </div>
              )}

              {genStatus === 'success' && (
                <div className="status-box success" style={{ textAlign: 'left' }}>
                  <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
                    <span className="huge-icon">🎉</span>
                    <h3 style={{ marginTop: '0.5rem' }}>Phase T (Trigger) Completed</h3>
                    <p style={{ color: 'var(--text-sub)' }}>Your Test Plan has been generated using the B.L.A.S.T Framework.</p>
                  </div>

                  {/* Generated Content Preview */}
                  {finalData && (
                    <div style={{ marginBottom: '1.5rem' }}>
                      {finalData.objective && (
                        <div style={{ marginBottom: '1rem', padding: '1rem', background: 'rgba(59,130,246,0.08)', borderLeft: '3px solid #3b82f6', borderRadius: '0 0.5rem 0.5rem 0' }}>
                          <strong style={{ color: '#60a5fa', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>🎯 Objective</strong>
                          <p style={{ margin: '0.5rem 0 0', color: 'var(--text-main)', lineHeight: 1.6 }}>{safeStr(finalData.objective)}</p>
                        </div>
                      )}
                      {finalData.scope && (
                        <div style={{ marginBottom: '1rem', padding: '1rem', background: 'rgba(16,185,129,0.08)', borderLeft: '3px solid #10b981', borderRadius: '0 0.5rem 0.5rem 0' }}>
                          <strong style={{ color: '#10b981', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>📋 Scope</strong>
                          <p style={{ margin: '0.5rem 0 0', color: 'var(--text-main)', lineHeight: 1.6 }}>{safeStr(finalData.scope)}</p>
                        </div>
                      )}
                      {finalData.test_scenarios && (
                        <div style={{ marginBottom: '1rem', padding: '1rem', background: 'rgba(245,158,11,0.08)', borderLeft: '3px solid #f59e0b', borderRadius: '0 0.5rem 0.5rem 0' }}>
                          <strong style={{ color: '#f59e0b', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>🧪 Test Scenarios</strong>
                          <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.25rem', color: 'var(--text-main)', lineHeight: 1.8 }}>
                            {safeList(finalData.test_scenarios).map((s, i) => <li key={i}>{s}</li>)}
                          </ul>
                        </div>
                      )}
                      {finalData.risks && (
                        <div style={{ marginBottom: '1rem', padding: '1rem', background: 'rgba(239,68,68,0.08)', borderLeft: '3px solid #ef4444', borderRadius: '0 0.5rem 0.5rem 0' }}>
                          <strong style={{ color: '#ef4444', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>⚠️ Risks</strong>
                          <p style={{ margin: '0.5rem 0 0', color: 'var(--text-main)', lineHeight: 1.6 }}>{safeStr(finalData.risks)}</p>
                        </div>
                      )}
                      {finalData.environment && (
                        <div style={{ marginBottom: '1rem', padding: '1rem', background: 'rgba(139,92,246,0.08)', borderLeft: '3px solid #8b5cf6', borderRadius: '0 0.5rem 0.5rem 0' }}>
                          <strong style={{ color: '#8b5cf6', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>🖥️ Environment</strong>
                          <p style={{ margin: '0.5rem 0 0', color: 'var(--text-main)', lineHeight: 1.6 }}>{safeStr(finalData.environment)}</p>
                        </div>
                      )}

                      {/* Full Result Document Preview */}
                      {finalHtml && (
                        <div style={{ marginTop: '2rem', padding: '1.5rem', background: '#F9FAFB', borderRadius: '1rem', border: '1px solid #E5E7EB', color: '#111827', textAlign: 'left' }}>
                          <h4 style={{ marginTop: 0, marginBottom: '1.5rem', color: '#1F2937', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                             📄 Real-time Document Preview 
                          </h4>
                          <div
                            className="rendered-preview-content"
                            style={{ maxHeight: '450px', overflowY: 'auto', paddingRight: '0.5rem', fontSize: '0.95rem' }}
                            dangerouslySetInnerHTML={{ __html: finalHtml }}
                          />
                        </div>
                      )}
                      
                      {/* Detailed Result Display for Phase 4 */}
                      <div className="result-success-indicator fade-in">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: '#10b981', fontWeight: 'bold', fontSize: '1.1rem' }}>
                          <span style={{ fontSize: '1.5rem' }}>✓</span> Phase 4: Output Verified & Ready
                        </div>
                      </div>
                    </div>
                  )}

                  <hr style={{ borderColor: 'rgba(255,255,255,0.1)', margin: '1.5rem 0' }}/>

                  <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                    {downloadLink && (
                      <a href={downloadLink} download style={{ flex: 1, minWidth: '180px', display: 'block', textDecoration: 'none', textAlign: 'center', padding: '0.75rem', borderRadius: '0.5rem', background: '#2563eb', color: '#fff', fontWeight: 700 }}>
                        📥 Download .Docx File
                      </a>
                    )}
                    {downloadMdLink && (
                      <a href={downloadMdLink} download style={{ flex: 1, minWidth: '180px', display: 'block', textDecoration: 'none', textAlign: 'center', padding: '0.75rem', borderRadius: '0.5rem', background: '#059669', color: '#fff', fontWeight: 700 }}>
                        📥 Download .MD File
                      </a>
                    )}
                  </div>

                  <hr style={{ borderColor: 'rgba(255,255,255,0.1)', margin: '1.5rem 0' }}/>

                  <h4 style={{ marginBottom: '0.75rem' }}>☁️ Push to Confluence</h4>
                  <div className="input-group" style={{ marginBottom: '0.75rem' }}>
                    <label>Confluence Base URL <span style={{ color: 'var(--text-sub)', fontWeight: 400 }}>(optional override)</span></label>
                    <input type="text" value={confluenceUrl} onChange={e => setConfluenceUrl(e.target.value)} placeholder={`defaults to ${almUrl}`} />
                  </div>
                  <div className="input-group" style={{ marginBottom: '1rem' }}>
                    <label>Confluence Space Key</label>
                    <input type="text" value={confluenceSpace} onChange={e => setConfluenceSpace(e.target.value)} placeholder="e.g. KAN" />
                  </div>

                  {confLink ? (
                    <a href={confLink} target="_blank" rel="noreferrer" className="btn outline" style={{ display: 'block', textAlign: 'center', padding: '0.75rem', textDecoration: 'none' }}>
                      🔗 Open Confluence Page
                    </a>
                  ) : (
                    <button className={`btn outline ${confStatus === 'pushing' ? 'loading' : ''}`} onClick={pushToConfluence} style={{ width: '100%' }}>
                      {confStatus === 'pushing' ? 'Publishing to Confluence...' : '☁️ Create Confluence Doc'}
                    </button>
                  )}
                </div>
              )}

              {genStatus === '' && (
                <div style={{ padding: '2.5rem 1rem', textAlign: 'center' }}>
                  <span style={{ fontSize: '4rem', display: 'block', marginBottom: '1rem' }}>🚀</span>
                  <h3 style={{ margin: '0 0 0.75rem', fontSize: '1.4rem', color: 'var(--text-main)' }}>Ready to Generate</h3>
                  <p style={{ color: 'var(--text-sub)', marginBottom: '2rem', maxWidth: '400px', margin: '0 auto 2rem' }}>
                    {!llmStatus || llmStatus !== 'success'
                      ? 'Go to Step 1 to connect your LLM engine first.'
                      : !almStatus || almStatus !== 'success'
                      ? 'Go to Step 2 to connect Jira.'
                      : !ticketId
                      ? 'Go to Step 3 and enter a Jira ticket ID.'
                      : 'All set! Click Generate Now above or use the button below.'}
                  </p>
                  <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                    {llmStatus === 'success' && almStatus === 'success' && ticketId ? (
                      <button className="btn primary" style={{ minWidth: '200px', fontSize: '1rem' }} onClick={generatePlan}>
                        🚀 Generate Test Plan
                      </button>
                    ) : (
                      <>
                        {(!llmStatus || llmStatus !== 'success') && (
                          <button className="btn outline" style={{ minWidth: '160px' }} onClick={() => setCurrentStep(1)}>Step 1: Set LLM</button>
                        )}
                        {llmStatus === 'success' && (!almStatus || almStatus !== 'success') && (
                          <button className="btn outline" style={{ minWidth: '160px' }} onClick={() => setCurrentStep(2)}>Step 2: Set Jira</button>
                        )}
                        {llmStatus === 'success' && almStatus === 'success' && !ticketId && (
                          <button className="btn outline" style={{ minWidth: '160px' }} onClick={() => setCurrentStep(3)}>Step 3: Set Ticket</button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Global Toast Notification */}
      {toast && (
        <div className="toast-notification">
          {toast}
        </div>
      )}
    </div>
  )
}

export default App;
