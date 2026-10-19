// Landing page interactivity: mobile menu, count-up stats.
document.getElementById("burger").onclick = () =>
  document.getElementById("mobilemenu").classList.toggle("hidden");
document.querySelectorAll(".mobilemenu a").forEach((a) =>
  a.addEventListener("click", () =>
    document.getElementById("mobilemenu").classList.add("hidden")));

const counted = new WeakSet();
const io = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (!e.isIntersecting || counted.has(e.target)) continue;
    counted.add(e.target);
    const end = parseInt(e.target.dataset.count, 10);
    const t0 = performance.now();
    const step = (t) => {
      const p = Math.min(1, (t - t0) / 900);
      e.target.textContent = Math.round(end * p);
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
});
document.querySelectorAll("[data-count]").forEach((el) => io.observe(el));
