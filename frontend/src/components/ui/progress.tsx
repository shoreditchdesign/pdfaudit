interface ProgressProps {
  value: number;
  max: number;
}

export function Progress({ value, max }: ProgressProps) {
  const width = max === 0 ? 0 : Math.min((value / max) * 100, 100);
  return (
    <div className="h-3 w-full overflow-hidden rounded-full bg-secondary">
      <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${width}%` }} />
    </div>
  );
}
