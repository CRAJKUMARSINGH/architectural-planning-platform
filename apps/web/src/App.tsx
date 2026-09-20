import { useState } from 'react';
import { ArtifactPanel } from './components/ArtifactPanel';
import { ProductModePanel } from './components/ProductModePanel';
import { ProjectLevelSelector } from './components/ProjectLevelSelector';
import { PropertyInspector } from './components/PropertyInspector';
import { ValidationPanel } from './components/ValidationPanel';
import { Viewport2D } from './components/Viewport2D';
import './App.css';

type LevelId = 'GF' | 'FF';

function BrandMark(): React.JSX.Element {
  return (
    <span className="brand-mark" aria-hidden="true">
      <span>A</span>
      <span>C</span>
    </span>
  );
}

function ArrowIcon(): React.JSX.Element {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d="M4 10h11M10.5 5.5 15 10l-4.5 4.5" />
    </svg>
  );
}

function CheckIcon(): React.JSX.Element {
  return (
    <svg viewBox="0 0 20 20" aria-hidden="true">
      <path d="m4 10 4 4 8-9" />
    </svg>
  );
}

function PlanPreview(): React.JSX.Element {
  return (
    <div className="plan-preview" aria-label="Simplified Bar Association Hall plan preview">
      <div className="plan-preview__topline">
        <span>BAR ASSOCIATION HALL</span>
        <span className="plan-preview__stamp">PRELIMINARY REVIEW</span>
      </div>
      <svg className="plan-preview__drawing" viewBox="0 0 720 440" role="img">
        <defs>
          <pattern id="plan-grid" width="24" height="24" patternUnits="userSpaceOnUse">
            <path d="M24 0H0V24" fill="none" stroke="currentColor" strokeOpacity=".08" />
          </pattern>
          <marker id="arrow-start" markerWidth="5" markerHeight="5" refX="2" refY="2.5" orient="auto">
            <path d="M5 0 0 2.5 5 5" fill="none" stroke="currentColor" strokeWidth="1" />
          </marker>
          <marker id="arrow-end" markerWidth="5" markerHeight="5" refX="3" refY="2.5" orient="auto">
            <path d="m0 0 5 2.5L0 5" fill="none" stroke="currentColor" strokeWidth="1" />
          </marker>
        </defs>
        <rect width="720" height="440" fill="url(#plan-grid)" />
        <g className="plan-preview__dimensions">
          <path d="M86 24H665M86 24v16M665 24v16" markerStart="url(#arrow-start)" markerEnd="url(#arrow-end)" />
          <text x="330" y="18">58'-6" NOMINAL</text>
          <path d="M40 48V383M40 48h26M40 383h26" markerStart="url(#arrow-start)" markerEnd="url(#arrow-end)" />
          <text x="22" y="235" transform="rotate(-90 22 235)">28'-6" NOMINAL</text>
        </g>
        <g className="plan-preview__walls">
          <path d="M86 48h579v335H86z" />
          <path d="M86 202h579M250 48v335M397 48v335M86 300h579" />
          <path d="M86 383h178M330 383h335" />
        </g>
        <g className="plan-preview__doors">
          <path d="M86 130h22a22 22 0 0 1-22 22M250 202h22a22 22 0 0 1-22 22M397 300h22a22 22 0 0 1-22 22" />
          <path d="M665 110h-28a28 28 0 0 0 28 28M665 328h-28a28 28 0 0 1 28-28" />
        </g>
        <g className="plan-preview__stairs">
          <rect x="269" y="217" width="106" height="66" rx="2" />
          <path d="M278 226h88M278 235h88M278 244h88M278 253h88M278 262h88M278 271h88" />
          <path d="m319 271 0-38 12 12" />
        </g>
        <g className="plan-preview__labels">
          <text x="122" y="130">RECEPTION</text>
          <text x="122" y="145">RECORDS</text>
          <text x="286" y="113">PRESIDENT</text>
          <text x="301" y="128">CHAMBER</text>
          <text x="284" y="339">LIBRARY</text>
          <text x="474" y="180">MAIN ASSEMBLY HALL</text>
          <text x="299" y="255" className="plan-preview__label--small">STAIR</text>
          <text x="489" y="330">SERVICE</text>
        </g>
        <g className="plan-preview__markers">
          <circle cx="108" cy="82" r="5" />
          <circle cx="634" cy="82" r="5" />
          <circle cx="634" cy="350" r="5" />
        </g>
      </svg>
      <div className="plan-preview__bottomline">
        <span><i className="status-dot" /> Canonical model · Revision 1</span>
        <span>Units: inches</span>
      </div>
    </div>
  );
}

function LandingPage({ onOpenStudio }: { onOpenStudio: () => void }): React.JSX.Element {
  return (
    <div className="landing">
      <header className="site-header">
        <a className="brand" href="#" aria-label="Advocate Chambers home">
          <BrandMark />
          <span className="brand-copy">
            <strong>Advocate</strong>
            <span>Chambers</span>
          </span>
        </a>
        <nav className="site-nav" aria-label="Main navigation">
          <a href="#workflows">Workflows</a>
          <a href="#validation">Validation</a>
          <a href="#delivery">Delivery</a>
        </nav>
        <button className="header-action" type="button" onClick={onOpenStudio}>
          Open workspace <ArrowIcon />
        </button>
      </header>

      <main>
        <section className="hero section-frame">
          <div className="hero__copy">
            <div className="eyebrow"><span className="eyebrow-line" /> Architectural planning, with evidence built in.</div>
            <h1>From first brief to a plan your team can <em>trust.</em></h1>
            <p className="hero__lede">
              Advocate Chambers turns architectural intent into a clear, reviewable
              planning workspace — keeping the model authoritative, the drawings
              legible, and every decision traceable.
            </p>
            <div className="hero__actions">
              <button className="button button--primary" type="button" onClick={onOpenStudio}>
                Explore the workspace <ArrowIcon />
              </button>
              <a className="button button--quiet" href="#workflows">See the workflow <span>↓</span></a>
            </div>
            <div className="hero__proof">
              <div className="proof-avatars" aria-hidden="true"><span>AK</span><span>RS</span><span>+</span></div>
              <p><strong>Built for the messy middle.</strong><br />Where ideas become coordinated drawings.</p>
            </div>
          </div>
          <div className="hero__visual">
            <div className="visual-kicker"><span>LIVE MODEL VIEW</span><span>W16 / 09</span></div>
            <PlanPreview />
            <div className="visual-callout visual-callout--top"><span className="callout-dot" /> Source of truth</div>
            <div className="visual-callout visual-callout--bottom"><span className="callout-dot callout-dot--gold" /> Review-ready evidence</div>
          </div>
        </section>

        <section className="signal-strip section-frame" aria-label="Project capabilities">
          <div><span className="signal-number">01</span><strong>One canonical model</strong><span>Geometry stays authoritative.</span></div>
          <div><span className="signal-number">02</span><strong>Every check has context</strong><span>Findings stay explainable.</span></div>
          <div><span className="signal-number">03</span><strong>Drawings that travel</strong><span>From review to delivery.</span></div>
        </section>

        <section className="intro section-frame" id="workflows">
          <div className="section-heading">
            <div className="eyebrow"><span className="eyebrow-line" /> A better way to coordinate</div>
            <h2>Good architecture is more than a beautiful view.</h2>
          </div>
          <p className="intro__body">
            It is a chain of decisions that can survive a second look. Bring the
            brief, the site, the rooms, and the drawings into one calm place —
            then make the important unknowns impossible to miss.
          </p>
          <div className="feature-grid">
            <article className="feature-card feature-card--blue">
              <span className="feature-index">01 / MODEL TRUTH</span>
              <div className="feature-icon"><span className="icon-crosshair" /></div>
              <h3>Keep the model honest.</h3>
              <p>Rooms, openings, stairs, routes, and levels remain the authority. Visual tools add options — never silent geometry edits.</p>
              <a href="#delivery">How it stays traceable <ArrowIcon /></a>
            </article>
            <article className="feature-card feature-card--cream">
              <span className="feature-index">02 / VISUAL CLARITY</span>
              <div className="feature-icon feature-icon--lines"><i /><i /><i /></div>
              <h3>See what the plan is saying.</h3>
              <p>Move between technical plans, presentation views, and evidence without losing the revision they came from.</p>
              <a href="#validation">Explore synchronized views <ArrowIcon /></a>
            </article>
            <article className="feature-card feature-card--dark">
              <span className="feature-index">03 / DELIVERY CONFIDENCE</span>
              <div className="feature-icon feature-icon--check"><CheckIcon /></div>
              <h3>Know what is ready.</h3>
              <p>Transparent findings and conservative release states make review conversations faster and safer.</p>
              <a href="#delivery">See the release path <ArrowIcon /></a>
            </article>
          </div>
        </section>

        <section className="workflow section-frame" id="validation">
          <div className="workflow__intro">
            <div className="eyebrow"><span className="eyebrow-line" /> The planning loop</div>
            <h2>A straight line from intent to evidence.</h2>
            <p>Every stage keeps its source, revision, and review state. That is how a fast workflow stays dependable.</p>
            <button className="text-button" type="button" onClick={onOpenStudio}>Open the live model <ArrowIcon /></button>
          </div>
          <div className="workflow__steps">
            <div className="workflow-step"><span>01</span><div><strong>Brief</strong><p>Capture intent, constraints, and the questions still open.</p></div></div>
            <div className="workflow-step"><span>02</span><div><strong>Model</strong><p>Build rooms, levels, openings, routes, and vertical connections.</p></div></div>
            <div className="workflow-step workflow-step--active"><span>03</span><div><strong>Validate</strong><p>Run focused checks and keep every finding attached to its object.</p></div><b>Current</b></div>
            <div className="workflow-step"><span>04</span><div><strong>Present</strong><p>Compare candidates and views without changing the source model.</p></div></div>
            <div className="workflow-step"><span>05</span><div><strong>Deliver</strong><p>Export a coordinated package with its assumptions intact.</p></div></div>
          </div>
        </section>

        <section className="evidence section-frame" id="delivery">
          <div className="evidence__heading">
            <div className="eyebrow eyebrow--light"><span className="eyebrow-line" /> Week 16 / review-first by design</div>
            <h2>Beautiful enough to present.<br /><em>Careful enough to review.</em></h2>
          </div>
          <div className="evidence__panel">
            <div className="evidence__panel-head"><span>VALIDATION SIGNALS</span><span>MODEL REVISION 1</span></div>
            <div className="evidence-row"><span className="evidence-status evidence-status--pass">PASS</span><strong>Canonical object identity</strong><span>17 spaces · 2 levels</span><i>↗</i></div>
            <div className="evidence-row"><span className="evidence-status evidence-status--review">REVIEW</span><strong>Live dimensions</strong><span>Archiagent · source retained</span><i>↗</i></div>
            <div className="evidence-row"><span className="evidence-status evidence-status--pass">PASS</span><strong>Drawing traceability</strong><span>Plans · sections · elevations</span><i>↗</i></div>
            <div className="evidence__panel-foot"><span className="status-dot status-dot--gold" /> Preliminary planning aid — professional review required.</div>
          </div>
        </section>

        <section className="closing section-frame">
          <div className="closing__mark"><BrandMark /></div>
          <div>
            <div className="eyebrow"><span className="eyebrow-line" /> Your next review starts here</div>
            <h2>Make the drawing clearer.<br /><em>Make the decision easier.</em></h2>
          </div>
          <button className="button button--primary" type="button" onClick={onOpenStudio}>Enter Advocate Chambers <ArrowIcon /></button>
        </section>
      </main>

      <footer className="site-footer section-frame">
        <a className="brand" href="#" aria-label="Advocate Chambers home"><BrandMark /><span className="brand-copy"><strong>Advocate</strong><span>Chambers</span></span></a>
        <span>Architectural planning intelligence · Banswara</span>
        <span>Preliminary review material · 2026</span>
      </footer>
    </div>
  );
}

function StudioView({ onBack }: { onBack: () => void }): React.JSX.Element {
  const [level, setLevel] = useState<LevelId>('GF');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const projectId = 'proj-banswara-bar-association';

  return (
    <div className="studio-shell">
      <header className="studio-header">
        <button className="studio-back" type="button" onClick={onBack}>← Back to overview</button>
        <div className="studio-title"><BrandMark /><strong>Advocate Chambers</strong><span>Workspace</span></div>
        <div className="studio-revision"><span className="status-dot" /> Revision 1 · Preliminary review</div>
      </header>
      <div className="studio-body">
        <aside className="studio-sidebar">
          <ProductModePanel />
          <ProjectLevelSelector level={level} onChange={setLevel} />
          <ValidationPanel projectId={projectId} level={level} />
          <ArtifactPanel projectId={projectId} level={level} />
        </aside>
        <main className="studio-viewport">
          <Viewport2D projectId={projectId} level={level} selectedId={selectedId} onSelect={setSelectedId} />
        </main>
        <aside className="studio-sidebar studio-sidebar--right">
          <PropertyInspector projectId={projectId} level={level} selectedId={selectedId} />
        </aside>
      </div>
    </div>
  );
}

export function App(): React.JSX.Element {
  const [view, setView] = useState<'landing' | 'studio'>('landing');
  return view === 'studio'
    ? <StudioView onBack={() => setView('landing')} />
    : <LandingPage onOpenStudio={() => setView('studio')} />;
}