// Landing page interactivity: mobile menu, count-up stats.
const themeButton = document.getElementById("siteThemeBtn");
const themeMeta = document.querySelector('meta[name="theme-color"]');
function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeButton.textContent = theme === "light" ? "☾" : "☼";
  themeButton.title = theme === "light" ? "Switch to dark theme" : "Switch to light theme";
  themeButton.setAttribute("aria-label", themeButton.title);
  themeMeta.content = theme === "light" ? "#f4f7f2" : "#070b10";
}
const storedTheme = localStorage.getItem("asg_theme");
setTheme(storedTheme || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"));
themeButton.addEventListener("click", () => {
  const theme = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  localStorage.setItem("asg_theme", theme);
  setTheme(theme);
});

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

if ("serviceWorker" in navigator && location.protocol !== "file:") {
  window.addEventListener("load", () => navigator.serviceWorker.register("service-worker.js").catch(() => {}));
}
