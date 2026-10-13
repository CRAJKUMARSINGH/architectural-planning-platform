import React from 'react';

export type LevelId = 'GF' | 'FF';

interface Props {
  level: LevelId;
  onChange: (next: LevelId) => void;
}

const OPTIONS: { id: LevelId; label: string; hint: string }[] = [
  { id: 'GF', label: 'GROUND FLOOR', hint: 'Chambers · Main Hall · Porticos' },
  { id: 'FF', label: 'FIRST FLOOR',  hint: 'Library · EDP · Admin · Librarian' },
];

export function ProjectLevelSelector({ level, onChange }: Props): React.JSX.Element {
  return (
    <section aria-label="Project level selector">
      <h2 style={{ margin: '0 0 10px 0', fontSize: 12, textTransform: 'uppercase', letterSpacing: 1.2, color: '#65717a' }}>
        Project / Level
      </h2>
      <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>
        Bar Association Hall · Banswara
      </div>
      <div style={{ fontSize: 11, color: '#65717a', marginBottom: 12 }}>
        RCC framed · 12″ columns · 15′ grid
      </div>

      {/* WCAG 1.3.1 / 4.1.2: interactive elements must be buttons, not divs */}
      {OPTIONS.map((opt) => (
        <button
          key={opt.id}
          type="button"
          aria-pressed={level === opt.id}
          onClick={() => onChange(opt.id)}
          style={{
            display: 'block',
            width: '100%',
            textAlign: 'left',
            padding: '14px',
            borderRadius: 6,
            cursor: 'pointer',
            border: level === opt.id ? '2px solid #2e5c62' : '1px solid #c7d0d4',
            background: level === opt.id ? '#eef4f4' : '#ffffff',
            marginBottom: 8,
            transition: 'background 120ms ease',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ fontWeight: 700, fontSize: 13 }}>{opt.label}</div>
            {/* WCAG 1.4.1: badge conveys id as text, not colour alone */}
            <div
              aria-hidden="true"
              style={{
                fontSize: 10,
                padding: '2px 8px',
                borderRadius: 999,
                background: level === opt.id ? '#2e5c62' : '#e9eef0',
                color: level === opt.id ? '#ffffff' : '#192530',
              }}
            >
              {opt.id}
            </div>
          </div>
          <div style={{ fontSize: 11, color: '#65717a', marginTop: 4 }}>{opt.hint}</div>
        </button>
      ))}
    </section>
  );
}
