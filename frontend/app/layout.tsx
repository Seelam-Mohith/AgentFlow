import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'AgentFlow', description: 'A transparent workspace for real AI-powered CLI tasks.' };
export default function RootLayout({children}: Readonly<{children: React.ReactNode}>) { return <html lang="en"><body>{children}</body></html>; }
