interface NavbarProps {
  onSimulate: () => void;
}

export function Navbar({ onSimulate }: NavbarProps) {
  return (
    <header className="sticky top-0 z-50 border-b border-line/70 bg-ink/85 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-mint">Finance Tool Demo</p>
          <p className="text-sm text-slate-300">Quant signal pipeline visualization</p>
        </div>
        <button
          type="button"
          onClick={onSimulate}
          className="rounded-md border border-mint/60 bg-mint/10 px-3 py-2 text-sm font-medium text-mint transition hover:bg-mint/20"
        >
          Simulate refresh
        </button>
      </div>
    </header>
  );
}
