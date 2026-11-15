export type Progress = { id: number; stage: number; message: string; time: string };
export type Page = {url: string; title: string | null; description: string | null; headings: string[]; content: string; links: string[]; metadata: Record<string,string>; status: string};
export type Task = {
  task_id: string; message: string; status: string; created_at: string; stage: number; events: Progress[];
  input: {url: string; max_pages: number; operations: string[]; instructions: string} | null;
  result: {website_title: string | null; description: string | null; summary: string; key_findings: {text: string; source_url: string}[]; pages: Page[]; total_pages_crawled: number; source_urls: string[]} | null;
  execution: {tool: string; command: string[]; started_at: string | null; exit_code: number | null; duration_seconds: number; stdout: string; stderr: string; errors: string[]; intent_mode: string | null; summary_mode: string | null};
};
