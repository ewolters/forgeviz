/**
 * ForgeViz.js — Zero-dependency chart renderer.
 *
 * Takes a ChartSpec JSON object and renders it to SVG in the browser.
 * No Plotly. No D3. No npm. One <script> tag.
 *
 * Usage:
 *   <div id="chart1"></div>
 *   <script src="/static/js/forgeviz.js"></script>
 *   <script>
 *     ForgeViz.render(document.getElementById('chart1'), chartSpecJSON);
 *   </script>
 *
 * Features:
 *   - Line, scatter, bar, area, step charts
 *   - Reference lines, zones, markers
 *   - Hover tooltips
 *   - Click events (emits 'forgeviz:click' CustomEvent)
 *   - Responsive resize
 *   - Theme support (svend_dark, light, print)
 *   - Copy to clipboard
 *   - SVG export
 */

(function(global) {
    'use strict';

    // ========================================================================
    // Themes
    // ========================================================================

    const THEMES = {
        svend_dark: {
            bg: '#0d120d', plotBg: '#0d120d',
            text: '#e8efe8', textSecondary: '#94a3b8',
            grid: 'rgba(255,255,255,0.06)', axis: 'rgba(255,255,255,0.15)',
            accent: '#4a9f6e',
            font: "Inter, system-ui, sans-serif",
            colors: ['#4a9f6e','#e8c547','#4dc9c0','#a78bfa','#f472b6','#fb923c','#92400e','#94a3b8','#60a5fa','#f87171'],
        },
        light: {
            bg: '#ffffff', plotBg: '#ffffff',
            text: '#1a1a2e', textSecondary: '#64748b',
            grid: 'rgba(0,0,0,0.08)', axis: 'rgba(0,0,0,0.2)',
            accent: '#4a9f6e',
            font: "Inter, system-ui, sans-serif",
            colors: ['#4a9f6e','#e8c547','#4dc9c0','#a78bfa','#f472b6','#fb923c','#92400e','#94a3b8','#60a5fa','#f87171'],
        },
        print: {
            bg: '#ffffff', plotBg: '#ffffff',
            text: '#000000', textSecondary: '#333333',
            grid: 'rgba(0,0,0,0.1)', axis: '#000000',
            accent: '#000000',
            font: "Helvetica, Arial, sans-serif",
            colors: ['#000','#444','#888','#bbb','#000','#444'],
        },
    };

    // ========================================================================
    // Scale utilities
    // ========================================================================

    function linearScale(domain, range) {
        const [d0, d1] = domain;
        const [r0, r1] = range;
        const ratio = (d1 - d0) !== 0 ? (r1 - r0) / (d1 - d0) : 0;
        return function(val) { return r0 + (val - d0) * ratio; };
    }

    function niceRange(min, max, ticks) {
        if (min === max) { min -= 1; max += 1; }
        const range = max - min;
        const step = Math.pow(10, Math.floor(Math.log10(range / ticks)));
        const niceStep = [1, 2, 5, 10].map(m => m * step).find(s => range / s <= ticks) || step;
        return {
            min: Math.floor(min / niceStep) * niceStep,
            max: Math.ceil(max / niceStep) * niceStep,
            step: niceStep,
        };
    }

    function generateTicks(min, max, step) {
        const ticks = [];
        for (let v = min; v <= max + step * 0.01; v += step) {
            ticks.push(Math.round(v * 1e10) / 1e10);
        }
        return ticks;
    }

    // ========================================================================
    // SVG helpers
    // ========================================================================

    function svgEl(tag, attrs, children) {
        const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
        if (attrs) Object.keys(attrs).forEach(k => el.setAttribute(k, attrs[k]));
        if (children) {
            if (typeof children === 'string') el.textContent = children;
            else children.forEach(c => { if (c) el.appendChild(c); });
        }
        return el;
    }

    function dashArray(dash) {
        if (dash === 'dashed') return '8,4';
        if (dash === 'dotted') return '3,3';
        return '';
    }

    // ========================================================================
    // Tooltip
    // ========================================================================

    function createTooltip(container) {
        const tip = document.createElement('div');
        tip.style.cssText = 'position:absolute;display:none;background:rgba(0,0,0,0.85);color:#fff;padding:4px 8px;border-radius:4px;font-size:11px;pointer-events:none;z-index:1000;white-space:nowrap;font-family:Inter,system-ui,sans-serif;';
        container.style.position = 'relative';
        container.appendChild(tip);
        return tip;
    }

    function showTooltip(tip, x, y, text) {
        tip.textContent = text;
        tip.style.display = 'block';
        tip.style.left = (x + 12) + 'px';
        tip.style.top = (y - 8) + 'px';
    }

    function hideTooltip(tip) { tip.style.display = 'none'; }

    // ========================================================================
    // Main render function
    // ========================================================================

    function render(container, spec, options) {
        options = options || {};
        const theme = THEMES[spec.theme || 'svend_dark'] || THEMES.svend_dark;

        // Dimensions
        const rect = container.getBoundingClientRect();
        const W = options.width || spec.width || rect.width || 800;
        const H = options.height || spec.height || rect.height || 400;
        const ml = 65, mr = 25, mt = spec.title ? 40 : 20, mb = 55;
        const pw = W - ml - mr;
        const ph = H - mt - mb;

        // Collect data ranges
        let allX = [], allY = [];
        (spec.traces || []).forEach(t => {
            if (t.x) t.x.forEach((v, i) => { if (typeof v === 'number') allX.push(v); else allX.push(i); });
            if (t.y) t.y.forEach(v => { if (typeof v === 'number') allY.push(v); });
        });
        (spec.reference_lines || []).forEach(r => { if (r.axis === 'y') allY.push(r.value); });

        if (!allX.length) allX = [0, 1];
        if (!allY.length) allY = [0, 1];

        const xNice = niceRange(Math.min(...allX), Math.max(...allX), 8);
        const yNice = niceRange(Math.min(...allY), Math.max(...allY), 6);
        const sx = linearScale([xNice.min, xNice.max], [ml, ml + pw]);
        const sy = linearScale([yNice.min, yNice.max], [mt + ph, mt]);

        // Build SVG
        const svg = svgEl('svg', { width: W, height: H, style: `background:${theme.bg}` });

        // Title
        if (spec.title) {
            svg.appendChild(svgEl('text', {
                x: W / 2, y: 18, 'text-anchor': 'middle',
                fill: theme.text, 'font-size': 14, 'font-weight': 500,
                'font-family': theme.font,
            }, spec.title));
        }

        // Grid
        const yTicks = generateTicks(yNice.min, yNice.max, yNice.step);
        yTicks.forEach(v => {
            const yy = sy(v);
            svg.appendChild(svgEl('line', { x1: ml, y1: yy, x2: ml + pw, y2: yy, stroke: theme.grid, 'stroke-width': 1 }));
            svg.appendChild(svgEl('text', {
                x: ml - 6, y: yy + 4, 'text-anchor': 'end',
                fill: theme.textSecondary, 'font-size': 10, 'font-family': theme.font,
            }, v.toFixed(v % 1 ? 2 : 0)));
        });

        const xTicks = generateTicks(xNice.min, xNice.max, xNice.step);
        xTicks.forEach(v => {
            const xx = sx(v);
            svg.appendChild(svgEl('text', {
                x: xx, y: mt + ph + 18, 'text-anchor': 'middle',
                fill: theme.textSecondary, 'font-size': 10, 'font-family': theme.font,
            }, typeof (spec.traces[0] || {}).x?.[v] === 'string' ? spec.traces[0].x[v] : v.toFixed(v % 1 ? 1 : 0)));
        });

        // Zones
        (spec.zones || []).forEach(z => {
            if (z.axis === 'y') {
                const zy1 = sy(z.high), zy2 = sy(z.low);
                svg.appendChild(svgEl('rect', { x: ml, y: zy1, width: pw, height: zy2 - zy1, fill: z.color }));
            }
        });

        // Reference lines
        (spec.reference_lines || []).forEach(r => {
            if (r.axis === 'y' || !r.axis) {
                const ry = sy(r.value);
                svg.appendChild(svgEl('line', {
                    x1: ml, y1: ry, x2: ml + pw, y2: ry,
                    stroke: r.color || '#888', 'stroke-width': r.width || 1,
                    'stroke-dasharray': dashArray(r.dash),
                }));
                if (r.label) {
                    svg.appendChild(svgEl('text', {
                        x: ml + pw + 4, y: ry + 4, fill: r.color || '#888',
                        'font-size': 9, 'font-family': theme.font,
                    }, r.label));
                }
            }
        });

        // Data elements for hover
        const dataPoints = [];

        // Traces
        (spec.traces || []).forEach((t, ti) => {
            if (!t.x || !t.y) return;
            const color = t.color || theme.colors[ti % theme.colors.length];
            const n = Math.min(t.x.length, t.y.length);

            if (t.trace_type === 'line' || t.trace_type === 'step' || (!t.trace_type && ti === 0)) {
                const pts = [];
                for (let i = 0; i < n; i++) {
                    const xv = typeof t.x[i] === 'number' ? t.x[i] : i;
                    pts.push(`${sx(xv).toFixed(1)},${sy(t.y[i]).toFixed(1)}`);
                }
                svg.appendChild(svgEl('polyline', {
                    points: pts.join(' '), fill: 'none',
                    stroke: color, 'stroke-width': t.width || 1.5,
                    'stroke-dasharray': dashArray(t.dash),
                }));

                // Markers
                if (t.marker_size > 0) {
                    for (let i = 0; i < n; i++) {
                        const xv = typeof t.x[i] === 'number' ? t.x[i] : i;
                        const cx = sx(xv), cy = sy(t.y[i]);
                        const circle = svgEl('circle', {
                            cx: cx.toFixed(1), cy: cy.toFixed(1),
                            r: t.marker_size / 2, fill: color,
                            'data-idx': i, 'data-trace': ti,
                            style: 'cursor:pointer',
                        });
                        svg.appendChild(circle);
                        dataPoints.push({ el: circle, x: t.x[i], y: t.y[i], name: t.name, idx: i });
                    }
                }
            } else if (t.trace_type === 'scatter') {
                for (let i = 0; i < n; i++) {
                    const xv = typeof t.x[i] === 'number' ? t.x[i] : i;
                    const cx = sx(xv), cy = sy(t.y[i]);
                    const circle = svgEl('circle', {
                        cx: cx.toFixed(1), cy: cy.toFixed(1),
                        r: (t.marker_size || 6) / 2, fill: color,
                        opacity: t.opacity || 1, style: 'cursor:pointer',
                    });
                    svg.appendChild(circle);
                    dataPoints.push({ el: circle, x: t.x[i], y: t.y[i], name: t.name, idx: i });
                }
            } else if (t.trace_type === 'bar') {
                const barW = Math.max(3, pw / n * 0.7);
                for (let i = 0; i < n; i++) {
                    const xv = typeof t.x[i] === 'number' ? t.x[i] : i;
                    const bx = sx(xv) - barW / 2;
                    const byTop = sy(t.y[i]), byBottom = sy(yNice.min);
                    const rect = svgEl('rect', {
                        x: bx.toFixed(1), y: byTop.toFixed(1),
                        width: barW.toFixed(1), height: (byBottom - byTop).toFixed(1),
                        fill: color, opacity: t.opacity || 0.8,
                        style: 'cursor:pointer',
                    });
                    svg.appendChild(rect);
                    dataPoints.push({ el: rect, x: t.x[i], y: t.y[i], name: t.name, idx: i });
                }
            } else if (t.trace_type === 'area') {
                const pts = [];
                for (let i = 0; i < n; i++) {
                    const xv = typeof t.x[i] === 'number' ? t.x[i] : i;
                    pts.push(`${sx(xv).toFixed(1)},${sy(t.y[i]).toFixed(1)}`);
                }
                // Close area to x-axis
                const lastX = typeof t.x[n-1] === 'number' ? t.x[n-1] : n-1;
                const firstX = typeof t.x[0] === 'number' ? t.x[0] : 0;
                pts.push(`${sx(lastX).toFixed(1)},${sy(yNice.min).toFixed(1)}`);
                pts.push(`${sx(firstX).toFixed(1)},${sy(yNice.min).toFixed(1)}`);
                svg.appendChild(svgEl('polygon', {
                    points: pts.join(' '), fill: color, opacity: t.opacity || 0.2, stroke: 'none',
                }));
            }
        });

        // Special markers (OOC points, etc.)
        (spec.markers || []).forEach(m => {
            if (!m.indices || !spec.traces || !spec.traces[0]) return;
            const t0 = spec.traces[0];
            m.indices.forEach(idx => {
                if (idx >= t0.x.length || idx >= t0.y.length) return;
                const xv = typeof t0.x[idx] === 'number' ? t0.x[idx] : idx;
                svg.appendChild(svgEl('circle', {
                    cx: sx(xv).toFixed(1), cy: sy(t0.y[idx]).toFixed(1),
                    r: (m.size || 8) / 2, fill: 'none',
                    stroke: m.color || 'red', 'stroke-width': 2,
                }));
            });
        });

        // Axes
        svg.appendChild(svgEl('line', { x1: ml, y1: mt, x2: ml, y2: mt + ph, stroke: theme.axis, 'stroke-width': 1 }));
        svg.appendChild(svgEl('line', { x1: ml, y1: mt + ph, x2: ml + pw, y2: mt + ph, stroke: theme.axis, 'stroke-width': 1 }));

        // Axis labels
        const xLabel = (spec.x_axis || {}).label;
        const yLabel = (spec.y_axis || {}).label;
        if (xLabel) {
            svg.appendChild(svgEl('text', {
                x: ml + pw / 2, y: H - 8, 'text-anchor': 'middle',
                fill: theme.textSecondary, 'font-size': 11, 'font-family': theme.font,
            }, xLabel));
        }
        if (yLabel) {
            const yt = svgEl('text', {
                x: 14, y: mt + ph / 2, 'text-anchor': 'middle',
                fill: theme.textSecondary, 'font-size': 11, 'font-family': theme.font,
                transform: `rotate(-90,14,${mt + ph / 2})`,
            }, yLabel);
            svg.appendChild(yt);
        }

        // Mount
        container.innerHTML = '';
        container.appendChild(svg);

        // Tooltip
        const tip = createTooltip(container);
        dataPoints.forEach(dp => {
            dp.el.addEventListener('mouseenter', function(e) {
                const r = container.getBoundingClientRect();
                const x = e.clientX - r.left;
                const y = e.clientY - r.top;
                showTooltip(tip, x, y, `${dp.name ? dp.name + ': ' : ''}(${dp.x}, ${typeof dp.y === 'number' ? dp.y.toFixed(4) : dp.y})`);
            });
            dp.el.addEventListener('mouseleave', function() { hideTooltip(tip); });
            dp.el.addEventListener('click', function() {
                container.dispatchEvent(new CustomEvent('forgeviz:click', {
                    detail: { x: dp.x, y: dp.y, index: dp.idx, name: dp.name },
                    bubbles: true,
                }));
            });
        });

        // Return API for this chart instance
        return {
            svg: svg,
            toSVGString: function() { return new XMLSerializer().serializeToString(svg); },
            copyToClipboard: function() {
                const svgStr = new XMLSerializer().serializeToString(svg);
                const blob = new Blob([svgStr], { type: 'image/svg+xml' });
                navigator.clipboard.write([new ClipboardItem({ 'image/svg+xml': blob })]).catch(() => {
                    // Fallback: copy as text
                    navigator.clipboard.writeText(svgStr);
                });
            },
            downloadSVG: function(filename) {
                const svgStr = new XMLSerializer().serializeToString(svg);
                const blob = new Blob([svgStr], { type: 'image/svg+xml' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url; a.download = filename || 'chart.svg';
                a.click(); URL.revokeObjectURL(url);
            },
            downloadPNG: function(filename, scale) {
                scale = scale || 2;
                const svgStr = new XMLSerializer().serializeToString(svg);
                const img = new Image();
                img.onload = function() {
                    const canvas = document.createElement('canvas');
                    canvas.width = W * scale; canvas.height = H * scale;
                    const ctx = canvas.getContext('2d');
                    ctx.scale(scale, scale);
                    ctx.drawImage(img, 0, 0);
                    canvas.toBlob(function(blob) {
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url; a.download = filename || 'chart.png';
                        a.click(); URL.revokeObjectURL(url);
                    });
                };
                img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgStr)));
            },
        };
    }

    // ========================================================================
    // Responsive helper
    // ========================================================================

    function renderResponsive(container, spec, options) {
        const instance = render(container, spec, options);
        let resizeTimer;
        const observer = new ResizeObserver(function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function() { render(container, spec, options); }, 150);
        });
        observer.observe(container);
        return instance;
    }

    // ========================================================================
    // Public API
    // ========================================================================

    global.ForgeViz = {
        render: render,
        renderResponsive: renderResponsive,
        themes: THEMES,
        version: '0.1.0',
    };

})(typeof window !== 'undefined' ? window : this);

// ========================================================================
// PHASE 2 INNOVATIONS — Beyond Plotly / Tableau
// ========================================================================

(function(FV) {
    'use strict';

    // ────────────────────────────────────────────────────────────────────
    // Linked Brushing — select range on one chart, all charts highlight
    // ────────────────────────────────────────────────────────────────────

    const _linkedGroups = {};

    FV.linkCharts = function(groupName, containers) {
        _linkedGroups[groupName] = containers;
    };

    FV.brushRange = function(groupName, xMin, xMax) {
        const containers = _linkedGroups[groupName] || [];
        containers.forEach(function(c) {
            c.dispatchEvent(new CustomEvent('forgeviz:brush', {
                detail: { xMin: xMin, xMax: xMax, group: groupName },
                bubbles: true,
            }));
            // Highlight points within range
            const circles = c.querySelectorAll('circle[data-idx]');
            circles.forEach(function(el) {
                const x = parseFloat(el.getAttribute('cx'));
                // Dim points outside range
                if (x < xMin || x > xMax) {
                    el.setAttribute('opacity', '0.15');
                } else {
                    el.setAttribute('opacity', '1');
                }
            });
        });
    };

    FV.clearBrush = function(groupName) {
        const containers = _linkedGroups[groupName] || [];
        containers.forEach(function(c) {
            c.querySelectorAll('circle[data-idx]').forEach(function(el) {
                el.setAttribute('opacity', '1');
            });
        });
    };

    // ────────────────────────────────────────────────────────────────────
    // Annotation Mode — click to add notes directly on chart points
    // ────────────────────────────────────────────────────────────────────

    FV.enableAnnotation = function(container, callback) {
        container._annotationMode = true;
        container._annotationCallback = callback;

        container.addEventListener('forgeviz:click', function(e) {
            if (!container._annotationMode) return;
            const detail = e.detail;

            // Create input overlay
            const input = document.createElement('input');
            input.type = 'text';
            input.placeholder = 'Add note...';
            input.style.cssText = 'position:absolute;background:#1a1a2e;color:#e8efe8;border:1px solid #4a9f6e;padding:4px 8px;border-radius:4px;font-size:11px;font-family:Inter,system-ui;z-index:1001;width:200px;';

            const rect = container.getBoundingClientRect();
            input.style.left = (e.clientX || e.pageX) - rect.left + 'px';
            input.style.top = (e.clientY || e.pageY) - rect.top + 'px';

            container.appendChild(input);
            input.focus();

            input.addEventListener('keydown', function(ke) {
                if (ke.key === 'Enter' && input.value.trim()) {
                    const annotation = {
                        x: detail.x,
                        y: detail.y,
                        index: detail.index,
                        text: input.value.trim(),
                        timestamp: new Date().toISOString(),
                    };
                    // Add visual annotation to SVG
                    const svg = container.querySelector('svg');
                    if (svg) {
                        const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                        const bg = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                        const txt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                        txt.textContent = input.value.trim();
                        txt.setAttribute('font-size', '10');
                        txt.setAttribute('fill', '#e8c547');
                        txt.setAttribute('font-family', 'Inter, system-ui');
                        // Position near the click point
                        const cx = parseFloat(input.style.left);
                        const cy = parseFloat(input.style.top) - 16;
                        txt.setAttribute('x', cx);
                        txt.setAttribute('y', cy);
                        bg.setAttribute('x', cx - 2);
                        bg.setAttribute('y', cy - 10);
                        bg.setAttribute('width', input.value.length * 6 + 8);
                        bg.setAttribute('height', 14);
                        bg.setAttribute('fill', 'rgba(0,0,0,0.7)');
                        bg.setAttribute('rx', '3');
                        g.appendChild(bg);
                        g.appendChild(txt);
                        svg.appendChild(g);
                    }
                    container.removeChild(input);
                    if (container._annotationCallback) {
                        container._annotationCallback(annotation);
                    }
                } else if (ke.key === 'Escape') {
                    container.removeChild(input);
                }
            });
            input.addEventListener('blur', function() {
                if (input.parentNode) container.removeChild(input);
            });
        });
    };

    FV.disableAnnotation = function(container) {
        container._annotationMode = false;
    };

    // ────────────────────────────────────────────────────────────────────
    // Threshold Dragging — drag reference lines to explore what-if
    // ────────────────────────────────────────────────────────────────────

    FV.enableThresholdDrag = function(container, callback) {
        const svg = container.querySelector('svg');
        if (!svg) return;

        // Find reference lines (horizontal lines that span full width)
        const lines = svg.querySelectorAll('line');
        lines.forEach(function(line) {
            const x1 = parseFloat(line.getAttribute('x1'));
            const x2 = parseFloat(line.getAttribute('x2'));
            const dash = line.getAttribute('stroke-dasharray');

            // Reference lines span the full plot width and have dashes
            if (dash && (x2 - x1) > 100) {
                line.style.cursor = 'ns-resize';
                let dragging = false;
                let startY = 0;
                let origY = 0;

                line.addEventListener('mousedown', function(e) {
                    dragging = true;
                    startY = e.clientY;
                    origY = parseFloat(line.getAttribute('y1'));
                    e.preventDefault();
                });

                document.addEventListener('mousemove', function(e) {
                    if (!dragging) return;
                    const dy = e.clientY - startY;
                    const newY = origY + dy;
                    line.setAttribute('y1', newY);
                    line.setAttribute('y2', newY);

                    // Find associated label text
                    const nextEl = line.nextElementSibling;
                    if (nextEl && nextEl.tagName === 'text') {
                        nextEl.setAttribute('y', newY + 4);
                    }
                });

                document.addEventListener('mouseup', function() {
                    if (!dragging) return;
                    dragging = false;
                    // Compute new value from pixel position
                    // Emit event with new threshold value
                    const newY = parseFloat(line.getAttribute('y1'));
                    if (callback) {
                        callback({
                            originalLabel: line.nextElementSibling ? line.nextElementSibling.textContent.trim() : '',
                            pixelY: newY,
                            color: line.getAttribute('stroke'),
                        });
                    }
                    container.dispatchEvent(new CustomEvent('forgeviz:threshold-change', {
                        detail: { pixelY: newY, color: line.getAttribute('stroke') },
                        bubbles: true,
                    }));
                });
            }
        });
    };

    // ────────────────────────────────────────────────────────────────────
    // Chart Composition — stack charts with shared x-axis, sync cursors
    // ────────────────────────────────────────────────────────────────────

    FV.compose = function(container, specs, options) {
        options = options || {};
        const gap = options.gap || 8;
        const totalHeight = specs.reduce(function(sum, s) { return sum + (s.height || 300); }, 0) + gap * (specs.length - 1);

        container.innerHTML = '';
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.gap = gap + 'px';

        const instances = [];
        specs.forEach(function(spec, i) {
            const wrapper = document.createElement('div');
            wrapper.style.width = '100%';
            wrapper.style.height = (spec.height || 300) + 'px';
            container.appendChild(wrapper);

            // Hide x-axis label on all but last
            if (i < specs.length - 1) {
                spec = Object.assign({}, spec);
                spec.x_axis = Object.assign({}, spec.x_axis || {});
                spec.x_axis.label = '';
            }

            const inst = FV.render(wrapper, spec);
            instances.push(inst);
        });

        // Sync cursor crosshair across all charts
        container.addEventListener('mousemove', function(e) {
            const rect = container.getBoundingClientRect();
            const x = e.clientX - rect.left;
            // Draw vertical cursor line on all SVGs
            instances.forEach(function(inst) {
                let cursor = inst.svg.querySelector('.fv-cursor');
                if (!cursor) {
                    cursor = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    cursor.classList.add('fv-cursor');
                    cursor.setAttribute('stroke', 'rgba(255,255,255,0.3)');
                    cursor.setAttribute('stroke-width', '1');
                    cursor.setAttribute('stroke-dasharray', '4,4');
                    cursor.setAttribute('y1', '0');
                    cursor.setAttribute('y2', inst.svg.getAttribute('height'));
                    inst.svg.appendChild(cursor);
                }
                cursor.setAttribute('x1', x);
                cursor.setAttribute('x2', x);
                cursor.style.display = '';
            });
        });

        container.addEventListener('mouseleave', function() {
            instances.forEach(function(inst) {
                const cursor = inst.svg.querySelector('.fv-cursor');
                if (cursor) cursor.style.display = 'none';
            });
        });

        return instances;
    };

    // ────────────────────────────────────────────────────────────────────
    // Filter Chips — click category to filter all charts
    // ────────────────────────────────────────────────────────────────────

    FV.addFilterChips = function(container, categories, onFilter) {
        const chipBar = document.createElement('div');
        chipBar.style.cssText = 'display:flex;gap:4px;padding:4px 0;flex-wrap:wrap;';

        const activeFilters = new Set(categories);

        categories.forEach(function(cat) {
            const chip = document.createElement('button');
            chip.textContent = cat;
            chip.style.cssText = 'padding:2px 8px;border-radius:12px;border:1px solid rgba(255,255,255,0.2);background:rgba(74,159,110,0.15);color:#4a9f6e;font-size:10px;cursor:pointer;font-family:Inter,system-ui;transition:opacity 0.15s;';
            chip.addEventListener('click', function() {
                if (activeFilters.has(cat)) {
                    activeFilters.delete(cat);
                    chip.style.opacity = '0.3';
                    chip.style.background = 'transparent';
                } else {
                    activeFilters.add(cat);
                    chip.style.opacity = '1';
                    chip.style.background = 'rgba(74,159,110,0.15)';
                }
                if (onFilter) onFilter(Array.from(activeFilters));
            });
            chipBar.appendChild(chip);
        });

        container.insertBefore(chipBar, container.firstChild);
        return chipBar;
    };

})(ForgeViz);
