import { motion } from "framer-motion";

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-line bg-gradient-to-b from-[#0f1733] via-[#0b1228] to-[#080d1c]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(62,230,207,0.18),transparent_32%),radial-gradient(circle_at_80%_10%,rgba(255,95,143,0.18),transparent_36%)]" />
      <div className="mx-auto max-w-7xl px-6 py-20 md:py-28">
        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="max-w-3xl text-4xl font-semibold leading-tight text-white md:text-6xl"
        >
          Visual Signal Engine Demo
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          className="mt-5 max-w-2xl text-base text-slate-300 md:text-lg"
        >
          Backend-free showcase of a quantitative equities pipeline: ingestion, NLP sentiment, technical features,
          regime-aware scoring, attribution, factor exposures, and portfolio risk outputs.
        </motion.p>
      </div>
    </section>
  );
}
