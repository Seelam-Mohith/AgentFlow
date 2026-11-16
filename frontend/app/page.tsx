'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowUp, ArrowUpRight, ChevronDown, Command, Globe2, History, Layers3, Link2, Menu, MessageSquare, Moon, Plus, Settings2, ShieldCheck, Sparkles, Sun, Terminal, X, LoaderCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ExecutionPanel } from '@/components/execution';
import { MobileTask } from '@/components/mobile-task';
import { Results } from '@/components/results';
import { Task, Progress } from '@/types';

const prompts = [
 {icon: Globe2, title:'Understand a website', text:'Crawl https://example.com and summarize the website.', description:'Turn a website into a concise brief.'},
 {icon: Link2, title:'Find what matters', text:'Extract headings and links from https://example.com.', description:'Collect headings, links, and key details.'},
 {icon: Terminal, title:'Make it structured', text:'Analyze https://example.com and return structured JSON.', description:'Go from unstructured pages to clean JSON.'},
 {icon: Sparkles, title:'Explore the big picture', text:'Crawl https://example.com and identify its main topics.', description:'Discover the ideas behind the pages.'},
];
const terminal = new Set(['completed','partial','failed','cancelled']);
async function api<T>(path: string, options?: RequestInit): Promise<T> {const res = await fetch(`/api${path}`, options); if (!res.ok) { const body = await res.json(); throw new Error(typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)); } return res.json();}

export default function Home() {
 const [history, setHistory] = useState<Task[]>([]), [task, setTask] = useState<Task | null>(null), [input, setInput] = useState(''), [sending,setSending] = useState(false), [error,setError] = useState(''), [connected,setConnected] = useState<boolean | null>(null), [ai,setAi] = useState(false), [light,setLight] = useState(false), [settings,setSettings] = useState(false), [mobile,setMobile] = useState(false);
 const end = useRef<HTMLDivElement>(null), inputRef=useRef<HTMLTextAreaElement>(null);
 const busy = sending || Boolean(task && !terminal.has(task.status));
 const refreshHistory = useCallback(() => api<Task[]>('/tasks').then(setHistory).catch(()=>{}), []);
 useEffect(() => {refreshHistory(); const check = () => api<{ai_configured:boolean}>('/health').then(h=>{setConnected(true);setAi(h.ai_configured);}).catch(()=>setConnected(false)); check(); const timer=setInterval(check,15000); setLight(localStorage.getItem('agentflow-theme') === 'light'); return ()=>clearInterval(timer);},[refreshHistory]);
 useEffect(() => {document.documentElement.dataset.theme=light?'light':'dark';localStorage.setItem('agentflow-theme',light?'light':'dark');},[light]);
 useEffect(() => {
   if(!task || terminal.has(task.status)) return;
   const id=task.task_id;
   const source = new EventSource(`/api/tasks/${id}/events`);
   source.addEventListener('progress', event=>{
     const progress:Progress=JSON.parse((event as MessageEvent).data);
     setTask(old=>old?.task_id === id && !terminal.has(old.status) ? {...old,status:'running',stage:progress.stage,events:[...old.events.filter(e=>e.id!==progress.id),progress]}:old);
   });
   source.addEventListener('done',event=>{
     const completed:Task=JSON.parse((event as MessageEvent).data);
     setTask(old=>old?.task_id === id?completed:old);
     source.close(); clearInterval(timer); refreshHistory();
   });
   const timer=setInterval(()=>{
     api<Task>(`/tasks/${id}`).then(current=>{
       setTask(old=>old?.task_id===id?current:old);
       if(terminal.has(current.status)){source.close();clearInterval(timer);refreshHistory();}
     }).catch(()=>{});
   },2000);
   return()=>{source.close();clearInterval(timer);};
 },[task?.task_id,refreshHistory]);
 useEffect(()=>{end.current?.scrollIntoView({behavior:'smooth',block:'end'});},[task?.status]);
 async function send(message=input) {if(!message.trim() || busy) return;setSending(true);setError('');try{const created=await api<Task>('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message})});setTask(created);setInput('');refreshHistory();}catch(e){setError((e as Error).message);}finally{setSending(false);}}
 async function openTask(item:Task) {try {setTask(await api<Task>(`/tasks/${item.task_id}`));setMobile(false);} catch(e) {setError((e as Error).message);}}
 async function cancel(){if(task) {const updated=await api<Task>(`/tasks/${task.task_id}/cancel`,{method:'POST'});setTask(updated);refreshHistory();}}
 function newChat(){setTask(null);setError('');setInput('');setMobile(false);inputRef.current?.focus();}
 return <div className="app-shell">
  {mobile && <button className="sidebar-overlay" aria-label="Close navigation" onClick={()=>setMobile(false)}/>}
  <aside className={`sidebar ${mobile?'mobile-open':''}`}><a className="brand" href="/" aria-label="AgentFlow home"><div className="brand-symbol"><Layers3 size={23}/></div><span>AgentFlow<span className="brand-period">.</span></span><span className="beta">BETA</span></a><Button variant="outline" className="new-chat" onClick={newChat}><Plus size={16}/>New conversation<kbd>↗</kbd></Button><div className="nav-label">WORKSPACE</div><button className="nav-item active" onClick={newChat}><MessageSquare size={16}/>Agent chat<span className="nav-dot"/></button><button className="nav-item" onClick={()=>document.getElementById('recent')?.scrollIntoView({behavior:'smooth'})}><History size={16}/>Task history<span className="count">{history.length}</span></button><div className="recent-heading" id="recent"><span>RECENT CONVERSATIONS</span><button aria-label="Refresh history" onClick={refreshHistory}><History size={13}/></button></div><div className="history-list">{history.length===0 ? <p className="history-empty">Your first idea starts here.<br/>Completed tasks will appear below.</p>:history.map(item=><button className={`history-item ${task?.task_id===item.task_id?'current':''}`} key={item.task_id} onClick={()=>openTask(item)}><MessageSquare size={14}/><span>{item.result?.website_title || item.input?.url || item.message}<small>{new Date(item.created_at).toLocaleDateString(undefined,{month:'short',day:'numeric'})} · {item.status}</small></span></button>)}</div><div className="sidebar-bottom"><div className="local-card"><span className="live-dot"/><div><strong>Local workspace</strong><small>Your tasks, on your machine</small></div><ShieldCheck size={15}/></div><div className="bottom-actions"><button onClick={()=>setSettings(true)}><Settings2 size={16}/>Settings</button><button aria-label="Toggle theme" onClick={()=>setLight(!light)}>{light?<Moon size={16}/>:<Sun size={16}/>}</button></div><div className="profile"><div className="avatar">Y</div><div><strong>Your workspace</strong><small>Personal environment</small></div><ChevronDown size={13}/></div></div></aside>
  <main className="main"><header className="topbar"><div><button className="mobile-menu" aria-label="Open navigation" onClick={()=>setMobile(true)}><Menu size={19}/></button><span className="breadcrumb">Workspace</span><span className="slash">/</span><strong>Agent chat</strong></div><div><span className="connection"><span className={connected?'live-dot':'offline-dot'}/>{connected===null?'Connecting':connected?'Backend connected':'Backend offline'}</span><span className="header-divider"/><span className="version">v1.0</span></div></header>
  <div className="work-area"><section className="chat-column"><div className="chat-scroll">{!task ? <motion.div className="welcome" initial={{opacity:0,y:12}} animate={{opacity:1,y:0}} transition={{duration:.4}}><div className="welcome-badge"><span className="live-dot"/>YOUR INTENT. REAL EXECUTION.</div><div className="welcome-mark"><Layers3 size={35}/><span className="mark-orbit one"/><span className="mark-orbit two"/></div><h1>Big ideas.<br/><span>One conversation away.</span></h1><p className="welcome-subtitle">Describe the task. Your agent handles the command line.<br/>Real tools, real results, full visibility.</p><div className="prompt-grid">{prompts.map(({icon:Icon,...prompt})=><button className="prompt-card" key={prompt.title} onClick={()=>{setInput(prompt.text);inputRef.current?.focus();}}><div><span className="prompt-icon"><Icon size={18}/></span><ArrowUpRight size={15}/></div><h3>{prompt.title}</h3><p>{prompt.description}</p></button>)}</div><div className="welcome-foot"><ShieldCheck size={13}/>Safe by default<span>·</span><Terminal size={13}/>Powered by real CLI tools</div></motion.div>:<div className="conversation"><div className="conversation-label">CONVERSATION <span>{task.task_id}</span></div><div className="user-message"><div className="avatar">Y</div><div><strong>You <time>{new Date(task.created_at).toLocaleTimeString(undefined,{hour:'2-digit',minute:'2-digit'})}</time></strong><p>{task.message}</p></div></div><div className="assistant-message"><div className="assistant-avatar"><Layers3 size={17}/></div><div className="assistant-content"><div className="assistant-heading"><strong>AgentFlow</strong><span className="small muted">{task.execution.intent_mode || 'Agent'}</span></div>{terminal.has(task.status)?<><p className="response-intro">{task.status==='completed'?'Your website analysis is ready. Here’s what the crawler found.':task.status==='partial'?'Some pages could not be retrieved. Here are the verified results.':task.status==='cancelled'?'This task has been cancelled.':'This task needs your attention.'}</p><Results task={task} rerun={()=>send(task.message)}/></>:<div className="thinking"><LoaderCircle size={16} className="spin"/><span>{task.events.at(-1)?.message || 'Preparing your task…'}</span></div>}</div></div></div>}<div ref={end}/></div>
  <div className="composer-container">{error&&<div role="alert" className="error-box">{error}</div>}{connected===false&&<div role="status" className="offline-message">Start the backend with <code>python -m uvicorn backend.main:app --port 8000</code></div>}<form className="composer" onSubmit={e=>{e.preventDefault();send();}}><label className="sr-only" htmlFor="prompt">Describe a website task</label><textarea id="prompt" ref={inputRef} value={input} onChange={e=>setInput(e.target.value)} placeholder="What would you like to get done?" rows={2} maxLength={4000} onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send();}}}/><div className="composer-bottom"><div className="tool-pill"><Globe2 size={13}/>Website crawler<ChevronDown size={12}/></div><div><span className="enter-hint">↵ to send</span><Button type="submit" size="icon" aria-label="Send message" disabled={busy||!input.trim()}>{sending?<LoaderCircle size={17} className="spin"/>:<ArrowUp size={18}/>}</Button></div></div></form><p className="composer-note"><ShieldCheck size={11}/>AgentFlow runs approved tools only. Always verify extracted information.<span><Command size={11}/> Shift + Enter for a new line</span></p></div>
  <MobileTask task={task} cancel={()=>cancel().catch(e=>setError(e.message))}/></section><ExecutionPanel task={task} cancel={()=>cancel().catch(e=>setError(e.message))}/></div></main>
  {settings&&<div className="modal-backdrop" onClick={()=>setSettings(false)}><section className="settings-modal" role="dialog" aria-modal="true" aria-label="Settings" onClick={e=>e.stopPropagation()}><div className="panel-title"><h2>Workspace settings</h2><button aria-label="Close settings" onClick={()=>setSettings(false)}><X size={19}/></button></div><p>Execution stays in your local Python backend.</p><div className="setting-row"><span>Intelligence</span><strong>{ai?'OpenAI enabled':'Deterministic parser + extractive summaries'}</strong></div><div className="setting-row"><span>Appearance</span><Button variant="outline" onClick={()=>setLight(!light)}>{light?'Light':'Dark'}</Button></div><p className="muted small">Configure OPENAI_API_KEY, OPENAI_MODEL, crawl limits, and timeouts in the root .env file, then restart the backend. API keys stay on the server.</p><a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">Open API documentation <ArrowUpRight size={13}/></a></section></div>}
 </div>;
}
