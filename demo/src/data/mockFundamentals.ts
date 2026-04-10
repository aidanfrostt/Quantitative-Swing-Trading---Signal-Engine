export function makeFundamentalScore(rng: () => number) {
  const roe = 0.05 + rng() * 0.35;
  const pe = 8 + rng() * 42;
  const debt = rng() * 2.8;
  const growth = -0.05 + rng() * 0.35;

  let score = 0;
  score += roe > 0.18 ? 0.35 : roe > 0.1 ? 0.2 : -0.1;
  score += pe < 28 ? 0.2 : pe < 38 ? 0.05 : -0.15;
  score += debt < 1.2 ? 0.2 : debt < 2 ? 0.05 : -0.15;
  score += growth > 0.12 ? 0.25 : growth > 0.03 ? 0.1 : -0.15;

  return Number(Math.max(-1, Math.min(1, score)).toFixed(3));
}
