(() => {
  'use strict';
  // SimpleUI opens menu items inside an iframe; the cockpit owns its full-page navigation.
  if (window.self !== window.top && window.top.location.origin === window.location.origin) {
    window.top.location.href = window.location.href;
    return;
  }
  const form = document.querySelector('#dashboard-filters');
  const series = JSON.parse(document.getElementById('dashboard-series').textContent);
  const subjects = JSON.parse(document.getElementById('dashboard-subjects').textContent);
  document.querySelector('[data-batch-submit]')?.addEventListener('change', event => {
    form.elements.school.value = '';
    if (!event.target.value && form.elements.capture) form.elements.capture.disabled = true;
    form.requestSubmit();
  });
  document.querySelectorAll('[data-submit]').forEach(select => select.addEventListener('change', () => form.requestSubmit()));
  document.querySelectorAll('[data-filter]').forEach(select => select.addEventListener('change', () => {
    form.elements[select.dataset.filter].value = select.value;
    form.requestSubmit();
  }));
  const chart = document.getElementById('activity-chart');
  const tooltip = document.getElementById('chart-tooltip');
  const range = document.getElementById('trend-range');
  const ns = 'http://www.w3.org/2000/svg';
  const svg = (tag, attrs, text) => {
    const element = document.createElementNS(ns, tag);
    for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
    if (text !== undefined) element.textContent = text;
    return element;
  };
  function drawTrend() {
    const data = series.slice(-Number(range.value));
    form.elements.trend.value = range.value;
    const exportLink = document.querySelector('.export-button');
    const exportUrl = new URL(exportLink.href);
    exportUrl.searchParams.set('trend', range.value);
    exportLink.href = exportUrl.href;
    document.getElementById('trend-caption').textContent = `（近${data.length}天）`;
    chart.replaceChildren();
    tooltip.hidden = true;
    const max = Math.max(1, ...data.flatMap(point => [point.active, point.content]));
    const step = Math.max(1, Math.ceil(max / 5));
    const ceiling = step * 5;
    const width = Math.max(300, chart.clientWidth), height = Math.max(150, chart.clientHeight);
    chart.setAttribute('viewBox', `0 0 ${width} ${height}`);
    const left = 30, right = width - 14, top = 15, bottom = height - 26;
    const x = i => data.length === 1 ? (left + right) / 2 : left + (right - left) * i / (data.length - 1);
    const y = value => bottom - value / ceiling * (bottom - top);
    chart.append(svg('title', {}, `近${data.length}天教师活跃趋势。活跃教师按当天使用记录去重，发布内容包括教学设计、听评课、笔记和报告。`));
    const defs = svg('defs', {});
    const gradient = svg('linearGradient', { id: 'trend-fill', x1: 0, y1: 0, x2: 0, y2: 1 });
    gradient.append(svg('stop', { 'stop-color': '#1684ff', 'stop-opacity': '.24' }), svg('stop', { offset: '1', 'stop-color': '#1684ff', 'stop-opacity': '.025' }));
    defs.append(gradient); chart.append(defs);
    const dark = document.documentElement.getAttribute('data-theme') === 'dark';
    const grid = dark ? '#1d3d66' : '#e9eff8';
    const guide = dark ? '#163456' : '#f1f5fa';
    for (let i = 0; i <= 5; i++) {
      chart.append(svg('line', { x1: left, y1: y(i * step), x2: right, y2: y(i * step), stroke: grid, 'stroke-width': 1 }));
      chart.append(svg('text', { x: 17, y: y(i * step) + 4, 'text-anchor': 'end' }, i * step));
    }
    const interval = Math.max(1, Math.ceil((data.length - 1) / (width < 500 ? 4 : 8)));
    data.forEach((point, i) => {
      if (i % interval !== 0 && i !== data.length - 1) return;
      chart.append(svg('line', { x1: x(i), y1: top, x2: x(i), y2: bottom, stroke: guide, 'stroke-width': 1 }));
      // Suppress a crowded final tick while keeping the last point accessible.
      if (i === data.length - 1 && i % interval > 0 && i % interval < interval / 2) return;
      chart.append(svg('text', { x: x(i), y: height - 5, 'text-anchor': 'middle' }, point.date.slice(5).replace('-', '/')));
    });
    for (const [key, color] of [['active', '#1684ff'], ['content', '#9bbcef']]) {
      const points = data.map((point, i) => `${x(i)},${y(point[key])}`).join(' ');
      if (key === 'active' && data.length > 1) chart.append(svg('polygon', { points: `${left},${bottom} ${points} ${right},${bottom}`, fill: 'url(#trend-fill)' }));
      chart.append(svg('polyline', { points, fill: 'none', stroke: color, 'stroke-width': key === 'active' ? 2 : 1.5, 'stroke-linejoin': 'round' }));
    }
    data.forEach((point, i) => {
      const accessible = `${point.date}，活跃教师 ${point.active} 人，发布内容 ${point.content} 条`;
      const group = svg('g', { class: 'chart-point', tabindex: 0, role: 'img', 'aria-label': accessible });
      group.append(svg('circle', { cx: x(i), cy: y(point.active), r: 3.7, fill: '#1684ff', stroke: 'white', 'stroke-width': 1.1 }),
        svg('circle', { cx: x(i), cy: y(point.content), r: 3.3, fill: '#9bbcef', stroke: 'white', 'stroke-width': 1 }),
        svg('rect', { x: x(i) - 9, y: top, width: 18, height: bottom - top, fill: 'transparent' }));
      const show = () => {
        tooltip.replaceChildren();
        for (const line of [point.date, `活跃教师：${point.active}`, `发布内容：${point.content}`]) {
          const div = document.createElement('div'); div.textContent = line; tooltip.append(div);
        }
        tooltip.hidden = false;
        const ratio = chart.clientWidth / width;
        tooltip.style.left = `${Math.max(0, Math.min(chart.clientWidth - tooltip.offsetWidth, x(i) * ratio - tooltip.offsetWidth / 2))}px`;
        tooltip.style.top = `${Math.max(0, y(Math.max(point.active, point.content)) * chart.clientHeight / height - tooltip.offsetHeight - 8)}px`;
      };
      group.addEventListener('pointerenter', show); group.addEventListener('focus', show);
      group.addEventListener('pointerleave', () => { tooltip.hidden = true; });
      group.addEventListener('blur', () => { tooltip.hidden = true; });
      group.addEventListener('keydown', event => {
        if (event.key === 'Escape') tooltip.hidden = true;
        if (event.key === 'ArrowRight' || event.key === 'ArrowLeft') {
          event.preventDefault();
          const next = event.key === 'ArrowRight' ? group.nextElementSibling : group.previousElementSibling;
          if (next?.classList.contains('chart-point')) next.focus();
        }
      });
      chart.append(group);
    });
  }
  range.addEventListener('change', drawTrend);
  document.addEventListener('admin-theme-change', drawTrend);
  drawTrend();
  new ResizeObserver(drawTrend).observe(chart);
  document.querySelectorAll('.mini-bars').forEach(element => {
    const values = element.dataset.series === 'content' ? series.slice(-7).map(p => p.content) : subjects.slice(0, 7).map(s => s.count);
    const max = Math.max(1, ...values);
    values.forEach(value => { const bar = document.createElement('i'); bar.style.height = `${value / max * 100}%`; element.append(bar); });
  });
  document.addEventListener('click', event => {
    document.querySelectorAll('.header-menu[open]').forEach(menu => { if (!menu.contains(event.target)) menu.open = false; });
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') document.querySelectorAll('.header-menu[open]').forEach(menu => { menu.open = false; menu.querySelector('summary').focus(); });
  });
})();
