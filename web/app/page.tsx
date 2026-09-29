'use client';
import {useState} from 'react';

type Citation = {chunk_id:string; title:string; url:string; text:string; version:string; score:number; snapshot_date:string};
type Result = {answer:string; abstained:boolean; mode:string; citations:Citation[]};
const examples = ['What human oversight is required for high-risk AI systems?', 'What rights apply to automated decision-making under GDPR?', 'What transparency obligations apply to synthetic content?'];

export default function Page() {
  const [question, setQuestion] = useState(examples[0]);
  const [result, setResult] = useState<Result|null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [mode, setMode] = useState('extractive');
  async function ask(event:React.FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setResult(null);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/ask`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({question,mode}), signal:AbortSignal.timeout(100000)});
      if (!response.ok) throw new Error(response.status === 502 ? 'The local model is unavailable or returned invalid citations. Try source excerpts.' : 'The API is unavailable. Check that the backend is running.');
      setResult(await response.json());
    } catch (e) {setError(e instanceof Error ? e.message : 'Request failed.');}
    finally {setBusy(false);}
  }
  return <main>
    <header><a className="brand" href="https://github.com/suprkco/rag-eu-ai-act">KC / APPLIED AI</a><span className="badge">RESEARCH PROTOTYPE · v0.1</span></header>
    <section className="hero"><p className="eyebrow">EVIDENCE BEFORE ANSWERS</p><h1>Explore the rules.<br/><em>Inspect the source.</em></h1><p className="intro">Search selected EU AI Act and GDPR articles. Every result includes the passage and the document it came from.</p></section>
    <div className="workspace"><section className="query">
      <h2>Ask a question</h2><p className="muted">English questions · 20 selected articles</p>
      <form onSubmit={ask}><label htmlFor="question">Your research question</label><textarea id="question" value={question} onChange={e=>setQuestion(e.target.value)} minLength={5} maxLength={2000} required rows={5}/>
      <label htmlFor="mode">Response mode</label><select id="mode" value={mode} onChange={e=>setMode(e.target.value)}><option value="extractive">Source excerpts · no model required</option><option value="ollama">Generated answer · local Ollama required</option></select>
      <button className="primary" disabled={busy}>{busy ? 'Retrieving evidence…' : 'Find supporting evidence →'}</button></form>
      <h3>Try a question</h3><div className="examples">{examples.map(example=><button key={example} onClick={()=>setQuestion(example)}>{example}</button>)}</div>
      <aside><strong>Know the scope</strong><p>A limited snapshot, not a complete or current legal database. GDPR text is the EU regulation as adopted in 2016. Results are research aids, not legal advice.</p></aside>
    </section><section className="results" aria-live="polite" aria-busy={busy}>
      <div className="section-title"><h2>Evidence workspace</h2><span>{result ? `${result.citations.length} passages` : 'READY'}</span></div>
      {error && <p role="alert" className="error">{error}</p>}
      {!result && !error && <div className="empty"><div className="symbol">§</div><h3>{busy ? 'Reading the corpus…' : 'A clear path back to the text'}</h3><p>Submit a question to inspect matching passages, source links and version information.</p></div>}
      {result?.abstained && <aside>{result.answer} Try a more specific question within the listed corpus.</aside>}
      {result && !result.abstained && <>
        {result.mode === 'ollama' && <article><h3>Generated synthesis</h3><p className="answer">{result.answer}</p><small>Citation identifiers are checked; factual entailment still requires human review.</small></article>}
        {result.citations.map((c,i)=><article key={c.chunk_id}><div className="source-label">SOURCE {String(i+1).padStart(2,'0')}<span>RETRIEVAL SCORE {c.score.toFixed(2)}</span></div><h3><a href={c.url} target="_blank" rel="noreferrer">{c.title} ↗</a></h3><blockquote>{c.text}</blockquote><p className="version">{c.version.replace('; see fetched_at','')} · Snapshot {c.snapshot_date}</p></article>)}
      </>}
    </section></div><footer>Built by Kilian Codaccioni · <a href="https://github.com/suprkco/rag-eu-ai-act">Code, evaluation & limitations ↗</a></footer>
  </main>;
}
