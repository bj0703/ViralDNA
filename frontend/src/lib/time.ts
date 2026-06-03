export function formatSeconds(seconds: number) {
  if (!Number.isFinite(seconds)) {
    return '--:--';
  }

  const total = Math.max(0, Math.floor(seconds));
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export function clampPercent(value: number) {
  return Math.min(100, Math.max(0, value));
}
