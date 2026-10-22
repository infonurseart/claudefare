export default function ProgressBar({ value = 0, color = "#1558B0", track = "#E2E8F0", height = 7 }) {
  const safeValue = Math.max(0, Math.min(100, value));
  return (
    <div aria-label={`Progreso ${Math.round(safeValue)}%`} style={{ height, background: track, borderRadius: 999, overflow: "hidden" }}>
      <div style={{ height: "100%", width: `${safeValue}%`, background: color, borderRadius: 999, transition: "width .2s ease-out" }} />
    </div>
  );
}
