'use client';
import { X } from 'lucide-react';
import { Button } from './ui/button';
import { Task } from '@/types';
export function MobileTask({task, cancel}: {task:Task|null;cancel:()=>void}) {
 if(!task || !['running','queued'].includes(task.status)) return null;
 return <div className="mobile-task"><span><i className="live-dot"/>{task.events.at(-1)?.message || 'Preparing task'}</span><Button variant="outline" onClick={cancel}><X size={12}/>Cancel</Button></div>;
}
