// Tiny dependency-free SVG charts with hover tooltips (line + column).
// Colors come from CSS custom properties so light/dark modes swap automatically.
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const el = (tag, attrs, parent) => {
    const n = document.createElementNS(NS, tag);
    for (const k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  };
  const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const fmtDate = (s) => {
    const d = new Date(s + "T12:00:00");
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  };
  const niceTicks = (lo, hi, n = 4) => {
    if (lo === hi) { lo -= 1; hi += 1; }
    const raw = (hi - lo) / n, mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw);
    const start = Math.floor(lo / step) * step, ticks = [];
    for (let v = start; v <= hi + step * 0.001; v += step) ticks.push(+v.toFixed(6));
    if (ticks[ticks.length - 1] < hi) ticks.push(ticks[ticks.length - 1] + step);
    return ticks;
  };

  function frame(host, yMin, yMax, unit) {
    host.innerHTML = "";
    const W = host.clientWidth || 320, H = host.clientHeight || 200;
    const m = { l: 40, r: 12, t: 10, b: 24 };
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img" }, host);
    const ticks = niceTicks(yMin, yMax);
    const y0 = ticks[0], y1 = ticks[ticks.length - 1];
    const y = (v) => m.t + (H - m.t - m.b) * (1 - (v - y0) / (y1 - y0 || 1));
    for (const t of ticks) {
      el("line", { x1: m.l, x2: W - m.r, y1: y(t), y2: y(t), class: "grid" }, svg);
      const lab = el("text", { x: m.l - 6, y: y(t) + 4, "text-anchor": "end", class: "axis" }, svg);
      lab.textContent = t.toLocaleString() + (unit && t === ticks[ticks.length - 1] ? "" : "");
    }
    const tip = document.createElement("div");
    tip.className = "tip";
    host.appendChild(tip);
    return { svg, W, H, m, y, tip };
  }

  function showTip(f, x, yPx, html) {
    f.tip.innerHTML = html;
    f.tip.style.display = "block";
    f.tip.style.left = Math.min(Math.max(x, 60), f.W - 60) + "px";
    f.tip.style.top = yPx + "px";
  }

  // series: [{name, color: "--series-1", points: [[isoDate, value], ...]}]
  window.lineChart = function (host, series, opts = {}) {
    const all = series.flatMap((s) => s.points);
    if (!all.length) { host.innerHTML = `<p class="empty">${opts.empty || "No data yet."}</p>`; host.style.height = "auto"; return; }
    const xs = [...new Set(all.map((p) => p[0]))].sort();
    const vals = all.map((p) => p[1]);
    const pad = (Math.max(...vals) - Math.min(...vals)) * 0.1 || 2;
    const f = frame(host, opts.yMin ?? Math.min(...vals) - pad, opts.yMax ?? Math.max(...vals) + pad, opts.unit);
    const t0 = new Date(xs[0]).getTime(), t1 = new Date(xs[xs.length - 1]).getTime();
    const x = (d) => xs.length === 1 ? (f.m.l + f.W - f.m.r) / 2
      : f.m.l + (f.W - f.m.l - f.m.r) * ((new Date(d).getTime() - t0) / (t1 - t0));
    [xs[0], xs[xs.length - 1]].forEach((d, i) => {
      if (i === 1 && xs.length === 1) return;
      const t = el("text", { x: x(d), y: f.H - 6, "text-anchor": i ? "end" : "start", class: "axis" }, f.svg);
      t.textContent = fmtDate(d);
    });
    for (const s of series) {
      const color = css(s.color);
      const pts = [...s.points].sort((a, b) => (a[0] < b[0] ? -1 : 1));
      if (pts.length > 1 && !s.dotsOnly) {
        el("polyline", { points: pts.map((p) => `${x(p[0])},${f.y(p[1])}`).join(" "), fill: "none",
          stroke: color, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" }, f.svg);
      }
      for (const p of pts) {
        el("circle", { cx: x(p[0]), cy: f.y(p[1]), r: s.dotsOnly ? 3 : 4, fill: color,
          stroke: css("--surface"), "stroke-width": 2, opacity: s.dotsOnly ? 0.55 : 1 }, f.svg);
      }
    }
    const cross = el("line", { y1: f.m.t, y2: f.H - f.m.b, stroke: css("--muted"), "stroke-width": 1, visibility: "hidden" }, f.svg);
    const hit = el("rect", { x: 0, y: 0, width: f.W, height: f.H, fill: "transparent" }, f.svg);
    const move = (ev) => {
      const r = f.svg.getBoundingClientRect();
      const px = ((ev.touches ? ev.touches[0].clientX : ev.clientX) - r.left) * (f.W / r.width);
      const d = xs.reduce((a, b) => (Math.abs(x(b) - px) < Math.abs(x(a) - px) ? b : a));
      cross.setAttribute("x1", x(d)); cross.setAttribute("x2", x(d)); cross.setAttribute("visibility", "visible");
      const rows = series.map((s) => {
        const p = s.points.find((q) => q[0] === d);
        return p ? `<div><i style="background:${css(s.color)}"></i>${s.name}: <b>${p[1]}${opts.unit || ""}</b></div>` : "";
      }).join("");
      showTip(f, x(d) * (r.width / f.W), f.m.t + 4, `<div>${fmtDate(d)}</div>${rows}`);
    };
    hit.addEventListener("mousemove", move);
    hit.addEventListener("touchstart", move, { passive: true });
    hit.addEventListener("touchmove", move, { passive: true });
    hit.addEventListener("mouseleave", () => { f.tip.style.display = "none"; cross.setAttribute("visibility", "hidden"); });
  };

  // points: [[label(isoDate), value]]
  window.columnChart = function (host, points, opts = {}) {
    if (!points.length || points.every((p) => !p[1])) { host.innerHTML = `<p class="empty">${opts.empty || "No data yet."}</p>`; host.style.height = "auto"; return; }
    const max = Math.max(...points.map((p) => p[1]));
    const f = frame(host, 0, max, opts.unit);
    const band = (f.W - f.m.l - f.m.r) / points.length;
    const bw = Math.min(24, band * 0.6);
    const color = css(opts.color || "--series-1");
    points.forEach((p, i) => {
      const cx = f.m.l + band * (i + 0.5);
      const top = f.y(p[1]), base = f.y(0), h = Math.max(0, base - top);
      if (h > 0) {
        const r = Math.min(4, h, bw / 2);
        const x0 = cx - bw / 2;
        el("path", { d: `M${x0},${base} V${top + r} Q${x0},${top} ${x0 + r},${top} H${x0 + bw - r} Q${x0 + bw},${top} ${x0 + bw},${top + r} V${base} Z`, fill: color }, f.svg);
      }
      if (i === 0 || i === points.length - 1) {
        const t = el("text", { x: cx, y: f.H - 6, "text-anchor": "middle", class: "axis" }, f.svg);
        t.textContent = fmtDate(p[0]);
      }
      const hit = el("rect", { x: cx - band / 2, y: f.m.t, width: band, height: f.H - f.m.t - f.m.b, fill: "transparent" }, f.svg);
      const show = () => {
        const r = f.svg.getBoundingClientRect();
        showTip(f, cx * (r.width / f.W), top * (r.height / f.H), `<div>Week of ${fmtDate(p[0])}</div><b>${p[1]}${opts.unit || ""}</b>`);
      };
      hit.addEventListener("mouseenter", show);
      hit.addEventListener("touchstart", show, { passive: true });
      hit.addEventListener("mouseleave", () => (f.tip.style.display = "none"));
    });
  };
})();
