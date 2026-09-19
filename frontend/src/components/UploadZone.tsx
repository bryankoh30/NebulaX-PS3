import { useRef, useState } from 'react';
import { FileSpreadsheet, UploadCloud, X, ArrowRight } from 'lucide-react';
import type { Subsystem } from '../api/types';
import { config } from '../utils/domain';
export function UploadZone({ subsystem, busy, onAnalyse }: { subsystem: Subsystem; busy: boolean; onAnalyse: (files: File[]) => void }) {
  const settings = config[subsystem]; const input = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]); const [error, setError] = useState(''); const [dragging, setDragging] = useState(false);
  function add(incoming: File[]) {
    if (busy) return;
    const next = [...files, ...incoming];
    if (!settings.multiple && next.length > 1) return setError('Door analysis accepts one continuous CSV recording. Remove the selected file to replace it.');
    if (incoming.some(file => !file.name.toLowerCase().endsWith(settings.extension))) return setError(`Select ${settings.extension.toUpperCase()} files for ${settings.name}.`);
    if (incoming.some(file => file.size === 0)) return setError('Empty files cannot be analysed. Choose a recording containing data.');
    if (new Set(next.map(file => file.name)).size !== next.length) return setError('Each recording must have a unique filename. Remove duplicate filenames before uploading.');
    setFiles(next); setError('');
  }
  return <section className="card upload-card" aria-labelledby="upload-title"><div className="section-heading"><div><p className="eyebrow">NEW ANALYSIS</p><h2 id="upload-title">{settings.upload}</h2></div><span className="file-format">{settings.extension.toUpperCase().slice(1)}</span></div>
    <div className={`dropzone ${dragging ? 'dragging' : ''}`} onDragOver={event => { event.preventDefault(); if (!busy) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={event => { event.preventDefault(); setDragging(false); add(Array.from(event.dataTransfer.files)); }}>
      <UploadCloud size={29} /><div><strong>Drag {settings.multiple ? 'recordings' : 'a recording'} here, or <button disabled={busy} className="text-button" onClick={() => input.current?.click()}>browse files</button></strong><p>{settings.multiple ? 'One or more files' : 'One continuous recording'} · {settings.extension.toUpperCase()} format</p></div>
      <input ref={input} className="sr-only" type="file" aria-label={settings.upload} accept={settings.extension} multiple={settings.multiple} disabled={busy} onChange={event => { add(Array.from(event.target.files ?? [])); event.target.value = ''; }} />
    </div>
    {error && <p className="validation" role="alert">{error}</p>}
    {files.length > 0 && <ul className="file-list">{files.map(file => <li key={file.name}><FileSpreadsheet size={17} /><span>{file.name}<small>{(file.size / 1024).toFixed(1)} KB</small></span><button disabled={busy} className="icon-button" aria-label={`Remove ${file.name}`} onClick={() => { setFiles(files.filter(f => f !== file)); setError(''); }}><X size={16} /></button></li>)}</ul>}
    <div className="upload-actions"><span>{files.length} {files.length === 1 ? 'file' : 'files'} selected</span><button className="primary" disabled={busy || files.length === 0 || !!error} onClick={() => onAnalyse(files)}>{busy ? 'Analysis in progress' : 'Analyse recordings'}<ArrowRight size={17} /></button></div>
  </section>;
}
