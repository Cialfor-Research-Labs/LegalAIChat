import { BookOpenCheck, ExternalLink } from 'lucide-react';

export function SourcePanel() {
  return (
    <aside className="source-panel">
      <div>
        <div className="eyebrow">Evidence</div>
        <h2>Source viewer</h2>
      </div>
      <div className="source-empty">
        <BookOpenCheck size={24} />
        <strong>No source selected</strong>
        <p>Verified statutes, judgments, and matter-file spans will open here with page or paragraph locators.</p>
      </div>
      <div className="citation-gates">
        <span>Existence</span>
        <span>Entailment</span>
        <span>Fitness</span>
      </div>
      <button className="source-action" disabled><ExternalLink size={15} /> Open canonical source</button>
    </aside>
  );
}
