'use client';
import { useState } from 'react';
import { Copy, Download, Check, ExternalLink, FileJson, Terminal, AlignLeft, Files, RotateCcw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Task } from '@/types';
import { Button } from './ui/button';
import { JsonTree } from './json-tree';

export function Results({task, rerun}: {task: Task; rerun: () => void}) {
  const [tab, setTab] = useState('Summary');
  const [copied, setCopied] = useState(false);
  const [tree, setTree] = useState(true);
  const result = task.result;
  const json = JSON.stringify(task, null, 2);
  async function copy() { await navigator.clipboard.writeText(tab === 'Summary' ? result?.summary || task.execution.errors.join('\n') : json); setCopied(true); setTimeout(() => setCopied(false), 1800); }
  function download() { const url = URL.createObjectURL(new Blob([json], {type: 'application/json'})); const a = document.createElement('a'); a.href = url; a.download = `${task.task_id}.json`; a.click(); URL.revokeObjectURL(url); }
  return <div className="results">
    <div className="result-tabs" role="tablist" aria-label="Task results">{[['Summary',AlignLeft],['JSON',FileJson],['Execution logs',Terminal],['Pages',Files]].map(([label, Icon]) => { const I = Icon as typeof AlignLeft; return <button role="tab" aria-selected={tab === label} key={String(label)} onClick={() => setTab(String(label))} className={tab === label ? 'selected' : ''}><I size={14}/>{String(label)}</button>; })}</div>
    <div className="result-body">
      {tab === 'Summary' && (result ? <><div className="result-title"><div><span className="eyebrow">WEBSITE ANALYSIS</span><h2>{result.website_title || 'Website results'}</h2></div><span className={`status ${task.status}`}>{task.status}</span></div><div className="markdown"><ReactMarkdown>{result.summary}</ReactMarkdown></div><h4>Key findings</h4>{result.key_findings.map((finding, i) => <div className="finding" key={i}><span>{String(i+1).padStart(2,'0')}</span><div><p>{finding.text}</p><a href={finding.source_url} target="_blank" rel="noreferrer">{finding.source_url}<ExternalLink size={11}/></a></div></div>)}<div className="insights"><div><strong>{result.total_pages_crawled}</strong><span>Pages analyzed</span></div><div><strong>{result.pages.reduce((n,p) => n+p.links.length,0)}</strong><span>Links discovered</span></div><div><strong>{task.execution.duration_seconds.toFixed(1)}s</strong><span>Execution time</span></div></div><p className="muted small">Summary mode: {task.execution.summary_mode}. Sources contain untrusted website content.</p></> : <div className="error-box"><h3>{task.status === 'cancelled' ? 'Execution cancelled' : 'Unable to complete this task'}</h3>{task.execution.errors.map((e,i) => <p key={i}>{e}</p>)}<p>Check the public URL and its crawl permissions, then try again.</p></div>)}
      {tab === 'JSON' && <><div className="json-toolbar"><span className="muted small">Validated task record</span><button onClick={() => setTree(!tree)}>{tree ? 'View source' : 'View tree'}</button></div>{tree ? <div className="json-tree"><JsonTree value={task}/></div> : <SyntaxHighlighter language="json" style={vscDarkPlus} wrapLongLines>{json}</SyntaxHighlighter>}</>}
      {tab === 'Execution logs' && <><div className="terminal-heading"><span className="live-dot"/>Real subprocess · {task.execution.tool}</div><pre className="command">$ {task.execution.command.join(' ') || 'Process was not started'}</pre><div className="log-meta">Exit code: {task.execution.exit_code ?? '—'} · Duration: {task.execution.duration_seconds}s<br/>Intent: {task.execution.intent_mode || '—'} · Summary: {task.execution.summary_mode || '—'}</div><h4>Progress</h4><pre className="logs">{task.events.map(e => `${new Date(e.time).toLocaleTimeString()}  ${e.message}`).join('\n')}</pre><h4>Captured stderr</h4><pre className="logs">{task.execution.stderr || '(empty)'}</pre><h4>Captured stdout</h4><pre className="logs">{task.execution.stdout || '(empty)'}</pre>{task.execution.errors.length > 0 && <pre className="error-box">{task.execution.errors.join('\n')}</pre>}</>}
      {tab === 'Pages' && <>{result?.pages.map((page,i) => <details className="page-card" key={page.url} open={i === 0}><summary><span className="page-index">{String(i+1).padStart(2,'0')}</span><span>{page.title || page.url}<small>{page.url}</small></span><Check size={15}/></summary><p>{page.content}</p><div className="chips">{page.headings.map((h,j) => <span key={j}>{h}</span>)}</div><a href={page.url} target="_blank" rel="noreferrer">Open source <ExternalLink size={12}/></a></details>)}{!result && <p className="muted">No successfully extracted pages.</p>}</>}
    </div><div className="result-actions"><Button variant="ghost" onClick={copy}>{copied ? <Check size={14}/> : <Copy size={14}/>} {copied ? 'Copied' : 'Copy'}</Button><Button variant="ghost" onClick={download}><Download size={14}/>Export JSON</Button><Button variant="ghost" onClick={rerun}><RotateCcw size={14}/>Rerun</Button></div>
  </div>;
}
