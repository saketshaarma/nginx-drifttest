export function DiffViewer({ diff }) {
  if (!diff) {
    return (
      <div className="p-6 text-center text-sm text-slate-500 font-mono" data-testid="diff-empty">
        No text diff available (binary or unchanged).
      </div>
    );
  }
  const lines = diff.split("\n");
  return (
    <div className="rounded-lg border border-slate-800 bg-[#0B0F19] overflow-x-auto" data-testid="diff-viewer">
      <pre className="text-xs md:text-sm leading-relaxed font-mono py-2">
        {lines.map((line, i) => {
          let cls = "diff-line text-slate-300";
          if (line.startsWith("+++") || line.startsWith("---")) cls = "diff-line diff-meta";
          else if (line.startsWith("@@")) cls = "diff-line diff-hunk";
          else if (line.startsWith("+")) cls = "diff-line diff-add";
          else if (line.startsWith("-")) cls = "diff-line diff-del";
          return (
            <span key={i} className={cls}>
              {line || " "}
            </span>
          );
        })}
      </pre>
    </div>
  );
}
