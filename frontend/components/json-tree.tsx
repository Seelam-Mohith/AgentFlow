'use client';
export function JsonTree({value, name}: {value: unknown; name?: string}) {
  if (value !== null && typeof value === 'object') {
    const entries = Object.entries(value);
    return <details open={name === undefined}><summary><span className="json-key">{name ? `${name}: ` : ''}</span>{Array.isArray(value) ? `[ ${entries.length} items ]` : `{ ${entries.length} fields }`}</summary><div className="json-children">{entries.map(([key, item]) => <JsonTree key={key} name={key} value={item}/>)}</div></details>;
  }
  return <div className="json-leaf"><span className="json-key">{name}: </span><span className={typeof value === 'string' ? 'json-string' : 'json-number'}>{JSON.stringify(value)}</span></div>;
}
