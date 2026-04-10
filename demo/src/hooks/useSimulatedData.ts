import { useMemo, useState } from "react";
import { buildDemoData } from "../data";

export function useSimulatedData() {
  const [seed, setSeed] = useState<number>(Date.now());
  const data = useMemo(() => buildDemoData(seed), [seed]);

  return {
    data,
    reseed: () => setSeed(Date.now() + Math.floor(Math.random() * 10_000)),
  };
}
