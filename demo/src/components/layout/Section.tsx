import type { PropsWithChildren } from "react";

interface SectionProps extends PropsWithChildren {
  id?: string;
  title: string;
  subtitle?: string;
}

export function Section({ id, title, subtitle, children }: SectionProps) {
  return (
    <section id={id} className="mx-auto w-full max-w-7xl px-6 py-14 md:py-20">
      <div className="mb-6 md:mb-8">
        <h2 className="text-2xl font-semibold text-white md:text-3xl">{title}</h2>
        {subtitle ? <p className="mt-2 max-w-3xl text-sm text-slate-300">{subtitle}</p> : null}
      </div>
      {children}
    </section>
  );
}
