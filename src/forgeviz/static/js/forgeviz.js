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
    // Dict trace renderers (pie, donut, box, heatmap, contour, bullet, risk, parallel)
    // ========================================================================

    function _renderDictTrace(svg, t, ti, theme, ml, mt, pw, ph, W, H, spec) {
        const type = t.type || '';
        const colors = theme.colors || ['#4a9f6e','#4a9faf','#8a7fbf','#e8c547','#e89547','#ef4444','#60a5fa','#a78bfa'];

        if (type === 'pie' || type === 'donut') {
            _renderPieDonut(svg, t, colors, ml, mt, pw, ph, type === 'donut');
        } else if (type === 'box') {
            _renderBox(svg, t, ti, theme, ml, mt, pw, ph, spec);
        } else if (type === 'heatmap') {
            _renderHeatmap(svg, t, colors, ml, mt, pw, ph);
        } else if (type === 'risk_heatmap') {
            _renderRiskHeatmap(svg, t, ml, mt, pw, ph);
        } else if (type === 'contour') {
            _renderContour(svg, t, ml, mt, pw, ph);
        } else if (type === 'bullet_bar') {
            _renderBullet(svg, t, spec, ml, mt, pw, ph);
        } else if (type === 'parallel') {
            _renderParallel(svg, t, colors, ml, mt, pw, ph);
        }
    }

    function _renderPieDonut(svg, t, colors, ml, mt, pw, ph, isDonut) {
        const cx = ml + pw / 2, cy = mt + ph / 2;
        const R = Math.min(pw, ph) / 2 * 0.85;
        const hole = isDonut ? (t.hole || 0.55) : 0;
        const innerR = R * hole;
        const vals = t.values || [];
        const labels = t.labels || [];
        const total = vals.reduce((a, b) => a + b, 0);
        if (total === 0) return;

        let startAngle = -Math.PI / 2;
        vals.forEach((v, i) => {
            const slice = (v / total) * 2 * Math.PI;
            const endAngle = startAngle + slice;
            const large = slice > Math.PI ? 1 : 0;
            const x1 = cx + R * Math.cos(startAngle), y1 = cy + R * Math.sin(startAngle);
            const x2 = cx + R * Math.cos(endAngle), y2 = cy + R * Math.sin(endAngle);

            let d;
            if (isDonut) {
                const ix1 = cx + innerR * Math.cos(startAngle), iy1 = cy + innerR * Math.sin(startAngle);
                const ix2 = cx + innerR * Math.cos(endAngle), iy2 = cy + innerR * Math.sin(endAngle);
                d = `M${ix1},${iy1} L${x1},${y1} A${R},${R} 0 ${large} 1 ${x2},${y2} L${ix2},${iy2} A${innerR},${innerR} 0 ${large} 0 ${ix1},${iy1}`;
            } else {
                d = `M${cx},${cy} L${x1},${y1} A${R},${R} 0 ${large} 1 ${x2},${y2} Z`;
            }

            svg.appendChild(svgEl('path', { d: d, fill: colors[i % colors.length], stroke: '#0a0f0a', 'stroke-width': 1 }));

            // Label
            const mid = startAngle + slice / 2;
            const lx = cx + (R * 0.65) * Math.cos(mid), ly = cy + (R * 0.65) * Math.sin(mid);
            const pct = ((v / total) * 100).toFixed(0);
            if (slice > 0.15) {
                svg.appendChild(svgEl('text', {
                    x: lx, y: ly, fill: '#e8efe8', 'text-anchor': 'middle', 'dominant-baseline': 'middle',
                    'font-size': 10, 'font-family': 'Inter,system-ui,sans-serif',
                }, pct + '%'));
            }
            startAngle = endAngle;
        });
    }

    function _renderBox(svg, t, ti, theme, ml, mt, pw, ph, spec) {
        // Count box traces to determine width and position
        const boxTraces = (spec.traces || []).filter(tr => tr.type === 'box');
        const nBoxes = Math.max(boxTraces.length, 1);
        const idx = boxTraces.indexOf(t);
        const boxIdx = idx >= 0 ? idx : ti;

        const boxW = Math.min(60, pw / nBoxes * 0.6);
        const gap = pw / nBoxes;
        const bx = ml + gap * boxIdx + gap / 2;

        // Scale y to plot area
        const vals = [t.whisker_low || t.q1, t.whisker_high || t.q3, t.q1, t.q3, t.median];
        if (t.outliers) vals.push(...t.outliers);
        const yMin = Math.min(...vals) - 1;
        const yMax = Math.max(...vals) + 1;
        const sy = v => mt + ph - ((v - yMin) / (yMax - yMin)) * ph;

        const color = t.color || theme.colors[boxIdx % theme.colors.length];

        // Whiskers
        svg.appendChild(svgEl('line', { x1: bx, x2: bx, y1: sy(t.whisker_low || t.q1), y2: sy(t.q1), stroke: color, 'stroke-width': 1, 'stroke-dasharray': '4,2' }));
        svg.appendChild(svgEl('line', { x1: bx, x2: bx, y1: sy(t.q3), y2: sy(t.whisker_high || t.q3), stroke: color, 'stroke-width': 1, 'stroke-dasharray': '4,2' }));
        // Whisker caps
        svg.appendChild(svgEl('line', { x1: bx - boxW/4, x2: bx + boxW/4, y1: sy(t.whisker_low || t.q1), y2: sy(t.whisker_low || t.q1), stroke: color, 'stroke-width': 1 }));
        svg.appendChild(svgEl('line', { x1: bx - boxW/4, x2: bx + boxW/4, y1: sy(t.whisker_high || t.q3), y2: sy(t.whisker_high || t.q3), stroke: color, 'stroke-width': 1 }));
        // Box
        svg.appendChild(svgEl('rect', {
            x: bx - boxW/2, y: sy(t.q3), width: boxW, height: sy(t.q1) - sy(t.q3),
            fill: color, opacity: 0.3, stroke: color, 'stroke-width': 1.5,
        }));
        // Median
        svg.appendChild(svgEl('line', { x1: bx - boxW/2, x2: bx + boxW/2, y1: sy(t.median), y2: sy(t.median), stroke: '#e8efe8', 'stroke-width': 2 }));
        // Outliers
        (t.outliers || []).forEach(o => {
            svg.appendChild(svgEl('circle', { cx: bx, cy: sy(o), r: 3, fill: 'none', stroke: color, 'stroke-width': 1 }));
        });
        // Label
        if (t.name) {
            svg.appendChild(svgEl('text', {
                x: bx, y: mt + ph + 15, fill: '#9aaa9a', 'text-anchor': 'middle', 'font-size': 10,
            }, t.name));
        }
    }

    function _renderHeatmap(svg, t, colors, ml, mt, pw, ph) {
        const xLabels = t.x || [];
        const yLabels = t.y || [];
        const z = t.z || [];
        const nCols = xLabels.length;
        const nRows = yLabels.length;
        if (nCols === 0 || nRows === 0) return;

        const cellW = pw / nCols;
        const cellH = ph / nRows;

        // Find z range
        let zMin = Infinity, zMax = -Infinity;
        z.forEach(row => row.forEach(v => { if (v < zMin) zMin = v; if (v > zMax) zMax = v; }));
        if (zMin === zMax) { zMin -= 1; zMax += 1; }

        for (let r = 0; r < nRows; r++) {
            for (let c = 0; c < nCols; c++) {
                const val = (z[r] && z[r][c] !== undefined) ? z[r][c] : 0;
                const t_norm = (val - zMin) / (zMax - zMin);
                const hue = (1 - t_norm) * 120;  // green (120) to red (0)
                const color = `hsl(${hue}, 60%, ${20 + t_norm * 25}%)`;

                svg.appendChild(svgEl('rect', {
                    x: ml + c * cellW, y: mt + r * cellH, width: cellW - 1, height: cellH - 1,
                    fill: color, stroke: '#0a0f0a', 'stroke-width': 0.5,
                }));
                // Value text
                svg.appendChild(svgEl('text', {
                    x: ml + c * cellW + cellW / 2, y: mt + r * cellH + cellH / 2,
                    fill: '#e8efe8', 'text-anchor': 'middle', 'dominant-baseline': 'middle',
                    'font-size': Math.min(11, cellH * 0.4),
                }, typeof val === 'number' ? val.toFixed(2) : String(val)));
            }
        }
        // Axis labels
        xLabels.forEach((l, i) => {
            svg.appendChild(svgEl('text', {
                x: ml + i * cellW + cellW / 2, y: mt + ph + 14,
                fill: '#9aaa9a', 'text-anchor': 'middle', 'font-size': 9,
            }, String(l)));
        });
        yLabels.forEach((l, i) => {
            svg.appendChild(svgEl('text', {
                x: ml - 5, y: mt + i * cellH + cellH / 2,
                fill: '#9aaa9a', 'text-anchor': 'end', 'dominant-baseline': 'middle', 'font-size': 9,
            }, String(l)));
        });
    }

    function _renderRiskHeatmap(svg, t, ml, mt, pw, ph) {
        const xLabels = t.x || [];
        const yLabels = t.y || [];
        const z = t.z || [];
        const valueLabels = t.value_labels || null;
        const colorscale = t.colorscale || ['#1a2a1a', '#3b2a1a', '#3b1a1a'];
        const nCols = xLabels.length;
        const nRows = yLabels.length;
        if (nCols === 0 || nRows === 0) return;

        const cellW = pw / nCols;
        const cellH = ph / nRows;

        let zMin = Infinity, zMax = -Infinity;
        z.forEach(row => row.forEach(v => { if (v < zMin) zMin = v; if (v > zMax) zMax = v; }));
        if (zMin === zMax) { zMin = 0; zMax = 1; }

        for (let r = 0; r < nRows; r++) {
            for (let c = 0; c < nCols; c++) {
                const val = (z[r] && z[r][c] !== undefined) ? z[r][c] : 0;
                const t_norm = (val - zMin) / (zMax - zMin);
                // Interpolate between colorscale stops
                const ci = t_norm * (colorscale.length - 1);
                const lo = Math.floor(ci), hi = Math.min(colorscale.length - 1, lo + 1);
                const frac = ci - lo;
                const color = _interpolateColor(colorscale[lo], colorscale[hi], frac);

                svg.appendChild(svgEl('rect', {
                    x: ml + c * cellW, y: mt + r * cellH, width: cellW - 1, height: cellH - 1,
                    fill: color, stroke: '#0a0f0a', 'stroke-width': 0.5, rx: 3,
                }));
                // Cell label
                const label = (valueLabels && valueLabels[r] && valueLabels[r][c]) ? valueLabels[r][c] : String(val);
                svg.appendChild(svgEl('text', {
                    x: ml + c * cellW + cellW / 2, y: mt + r * cellH + cellH / 2,
                    fill: '#e8efe8', 'text-anchor': 'middle', 'dominant-baseline': 'middle',
                    'font-size': Math.min(12, cellH * 0.35), 'font-weight': 'bold',
                }, label));
            }
        }
        // Axis labels
        xLabels.forEach((l, i) => {
            svg.appendChild(svgEl('text', { x: ml + i * cellW + cellW / 2, y: mt + ph + 14, fill: '#9aaa9a', 'text-anchor': 'middle', 'font-size': 9 }, String(l)));
        });
        yLabels.forEach((l, i) => {
            svg.appendChild(svgEl('text', { x: ml - 5, y: mt + i * cellH + cellH / 2, fill: '#9aaa9a', 'text-anchor': 'end', 'dominant-baseline': 'middle', 'font-size': 9 }, String(l)));
        });
    }

    function _renderContour(svg, t, ml, mt, pw, ph) {
        // Simplified: render as a filled heatmap (true contours need marching squares)
        _renderHeatmap(svg, t, null, ml, mt, pw, ph);
    }

    function _renderBullet(svg, t, spec, ml, mt, pw, ph) {
        const val = t.value || 0;
        const min = t.min || 0;
        const max = t.max || 100;
        const color = t.color || '#4a9f6e';
        const barH = Math.min(ph * 0.4, 20);
        const cy = mt + ph / 2;

        // Background ranges (zones)
        (spec.zones || []).forEach(z => {
            const x1 = ml + ((z.low - min) / (max - min)) * pw;
            const x2 = ml + ((z.high - min) / (max - min)) * pw;
            svg.appendChild(svgEl('rect', {
                x: x1, y: cy - barH, width: x2 - x1, height: barH * 2,
                fill: z.color || '#1a261a', opacity: 0.8,
            }));
        });

        // Value bar
        const barEnd = ml + ((val - min) / (max - min)) * pw;
        svg.appendChild(svgEl('rect', {
            x: ml, y: cy - barH / 2, width: Math.max(0, barEnd - ml), height: barH,
            fill: color, opacity: 0.9, rx: 2,
        }));

        // Target markers (reference lines)
        (spec.reference_lines || []).forEach(r => {
            if (typeof r === 'object' && r.value !== undefined) {
                const tx = ml + ((r.value - min) / (max - min)) * pw;
                svg.appendChild(svgEl('line', {
                    x1: tx, x2: tx, y1: cy - barH * 1.2, y2: cy + barH * 1.2,
                    stroke: r.color || '#e8efe8', 'stroke-width': r.width || 2.5,
                }));
            }
        });
    }

    function _renderParallel(svg, t, colors, ml, mt, pw, ph) {
        const dims = t.dimensions || [];
        const data = t.data || {};
        const highlight = t.highlight || [];
        const nDims = dims.length;
        if (nDims < 2) return;

        // One vertical axis per dimension
        const gap = pw / (nDims - 1);

        // Compute ranges per dimension
        const ranges = dims.map(d => {
            const vals = data[d] || [];
            const mn = Math.min(...vals), mx = Math.max(...vals);
            return { min: mn, max: mx === mn ? mn + 1 : mx };
        });

        // Draw axes
        dims.forEach((d, i) => {
            const x = ml + i * gap;
            svg.appendChild(svgEl('line', { x1: x, x2: x, y1: mt, y2: mt + ph, stroke: '#333', 'stroke-width': 1 }));
            svg.appendChild(svgEl('text', {
                x: x, y: mt + ph + 14, fill: '#9aaa9a', 'text-anchor': 'middle', 'font-size': 9,
            }, d));
        });

        // Draw lines for each observation
        const nObs = (data[dims[0]] || []).length;
        for (let obs = 0; obs < nObs; obs++) {
            const pts = dims.map((d, i) => {
                const val = (data[d] || [])[obs] || 0;
                const r = ranges[i];
                const y = mt + ph - ((val - r.min) / (r.max - r.min)) * ph;
                return `${(ml + i * gap).toFixed(1)},${y.toFixed(1)}`;
            });
            const isHighlight = highlight.includes(obs);
            svg.appendChild(svgEl('polyline', {
                points: pts.join(' '), fill: 'none',
                stroke: isHighlight ? '#e8c547' : colors[obs % colors.length],
                'stroke-width': isHighlight ? 2 : 0.8,
                opacity: isHighlight ? 1 : 0.4,
            }));
        }
    }

    function _interpolateColor(c1, c2, frac) {
        // Simple hex interpolation
        const h2r = c => parseInt(c.slice(1, 3), 16);
        const h2g = c => parseInt(c.slice(3, 5), 16);
        const h2b = c => parseInt(c.slice(5, 7), 16);
        try {
            const r = Math.round(h2r(c1) + (h2r(c2) - h2r(c1)) * frac);
            const g = Math.round(h2g(c1) + (h2g(c2) - h2g(c1)) * frac);
            const b = Math.round(h2b(c1) + (h2b(c2) - h2b(c1)) * frac);
            return `rgb(${r},${g},${b})`;
        } catch (e) {
            return c1;
        }
    }

    // ========================================================================
    // Main render function
    // ========================================================================

    function render(container, spec, options) {
        options = options || {};
        var baseTheme = THEMES[spec.theme || 'svend_dark'] || THEMES.svend_dark;
        // Merge any inline style overrides (from color picker)
        const theme = spec._styleOverrides
            ? Object.assign({}, baseTheme, spec._styleOverrides)
            : baseTheme;

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
            // Dict traces — special chart types without x/y arrays
            if (!t.x || !t.y) {
                _renderDictTrace(svg, t, ti, theme, ml, mt, pw, ph, W, H, spec);
                return;
            }
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
                            'data-x': xv, 'data-y': t.y[i],
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
                        'data-idx': i, 'data-x': xv, 'data-y': t.y[i],
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

        // Store scale info for interactive features (threshold drag, brushing)
        container._scales = {
            sx: sx, sy: sy,
            xDomain: [xNice.min, xNice.max],
            yDomain: [yNice.min, yNice.max],
            xRange: [ml, ml + pw],
            yRange: [mt + ph, mt],
            // Inverse functions: pixel → data value
            invertX: function(px) { return xNice.min + (px - ml) / pw * (xNice.max - xNice.min); },
            invertY: function(py) { return yNice.max - (py - mt) / ph * (yNice.max - yNice.min); },
        };

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
        // Use FV.render (enhanced) so responsive charts get toolbar, spec storage, utilities
        const instance = FV.render(container, spec, options);
        let resizeTimer;
        const observer = new ResizeObserver(function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function() { FV.render(container, spec, options); }, 150);
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
            // Highlight points within range (compare data values, not pixel coords)
            const circles = c.querySelectorAll('circle[data-x]');
            circles.forEach(function(el) {
                const x = parseFloat(el.getAttribute('data-x'));
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
                    // Compute new value from pixel position using stored scale
                    const newY = parseFloat(line.getAttribute('y1'));
                    const scales = container._scales;
                    const dataValue = scales ? scales.invertY(newY) : null;
                    if (callback) {
                        callback({
                            originalLabel: line.nextElementSibling ? line.nextElementSibling.textContent.trim() : '',
                            value: dataValue,
                            pixelY: newY,
                            color: line.getAttribute('stroke'),
                        });
                    }
                    container.dispatchEvent(new CustomEvent('forgeviz:threshold-change', {
                        detail: { value: dataValue, pixelY: newY, color: line.getAttribute('stroke') },
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

// ========================================================================
// CHART UTILITIES — Color picker, inline editing, toolbar
// ========================================================================

(function(FV) {
    'use strict';

    // ────────────────────────────────────────────────────────────────────
    // Chart Toolbar — export, copy, theme, fullscreen
    // ────────────────────────────────────────────────────────────────────

    FV.addToolbar = function(container, chartInstance, options) {
        options = options || {};
        const bar = document.createElement('div');
        bar.style.cssText = 'display:flex;gap:4px;justify-content:flex-end;padding:4px 0;';

        const btnStyle = 'padding:2px 8px;border-radius:4px;border:1px solid rgba(255,255,255,0.15);background:transparent;color:#94a3b8;font-size:10px;cursor:pointer;font-family:Inter,system-ui;transition:background 0.15s;';

        // Copy to clipboard
        const copyBtn = document.createElement('button');
        copyBtn.textContent = 'Copy';
        copyBtn.style.cssText = btnStyle;
        copyBtn.addEventListener('click', function() {
            if (chartInstance.copyToClipboard) chartInstance.copyToClipboard();
            copyBtn.textContent = 'Copied';
            setTimeout(function() { copyBtn.textContent = 'Copy'; }, 1500);
        });
        bar.appendChild(copyBtn);

        // Download SVG
        const svgBtn = document.createElement('button');
        svgBtn.textContent = 'SVG';
        svgBtn.style.cssText = btnStyle;
        svgBtn.addEventListener('click', function() {
            if (chartInstance.downloadSVG) chartInstance.downloadSVG(options.filename || 'chart.svg');
        });
        bar.appendChild(svgBtn);

        // Download PNG
        const pngBtn = document.createElement('button');
        pngBtn.textContent = 'PNG';
        pngBtn.style.cssText = btnStyle;
        pngBtn.addEventListener('click', function() {
            if (chartInstance.downloadPNG) chartInstance.downloadPNG(options.filename || 'chart.png', 2);
        });
        bar.appendChild(pngBtn);

        // Theme toggle
        if (options.showThemeToggle !== false) {
            const themeBtn = document.createElement('button');
            themeBtn.textContent = 'Theme';
            themeBtn.style.cssText = btnStyle;
            let themeIdx = 0;
            const themeNames = Object.keys(FV.themes);
            themeBtn.addEventListener('click', function() {
                themeIdx = (themeIdx + 1) % themeNames.length;
                container._currentSpec.theme = themeNames[themeIdx];
                FV.render(container, container._currentSpec);
                themeBtn.textContent = themeNames[themeIdx];
            });
            bar.appendChild(themeBtn);
        }

        // Style panel
        const styleBtn = document.createElement('button');
        styleBtn.textContent = 'Style';
        styleBtn.style.cssText = btnStyle;
        styleBtn.addEventListener('click', function() {
            FV.openStylePanel(container, options.onStyleApply);
        });
        bar.appendChild(styleBtn);

        // Fullscreen toggle
        const fsBtn = document.createElement('button');
        fsBtn.textContent = 'Expand';
        fsBtn.style.cssText = btnStyle;
        fsBtn.addEventListener('click', function() {
            if (!document.fullscreenElement) {
                container.requestFullscreen().catch(function() {});
                fsBtn.textContent = 'Exit';
            } else {
                document.exitFullscreen();
                fsBtn.textContent = 'Expand';
            }
        });
        bar.appendChild(fsBtn);

        container.insertBefore(bar, container.firstChild);
        return bar;
    };

    // ────────────────────────────────────────────────────────────────────
    // Inline Title Editing — double-click title to edit
    // ────────────────────────────────────────────────────────────────────

    FV.enableTitleEdit = function(container, onSave) {
        const svg = container.querySelector('svg');
        if (!svg) return;

        const titleEl = svg.querySelector('text[text-anchor="middle"][font-weight]');
        if (!titleEl) return;

        titleEl.style.cursor = 'pointer';
        titleEl.addEventListener('dblclick', function(e) {
            const oldText = titleEl.textContent;
            const rect = container.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const input = document.createElement('input');
            input.type = 'text';
            input.value = oldText;
            input.style.cssText = `position:absolute;left:${x - 100}px;top:${y - 12}px;width:200px;background:#1a1a2e;color:#e8efe8;border:1px solid #4a9f6e;padding:2px 6px;border-radius:3px;font-size:13px;font-family:Inter,system-ui;text-align:center;z-index:1001;`;
            container.appendChild(input);
            input.focus();
            input.select();

            function commit() {
                const newText = input.value.trim() || oldText;
                titleEl.textContent = newText;
                if (input.parentNode) container.removeChild(input);
                if (container._currentSpec) container._currentSpec.title = newText;
                if (onSave) onSave(newText);
            }

            input.addEventListener('keydown', function(ke) {
                if (ke.key === 'Enter') commit();
                if (ke.key === 'Escape') { if (input.parentNode) container.removeChild(input); }
            });
            input.addEventListener('blur', commit);
        });
    };

    // ────────────────────────────────────────────────────────────────────
    // Color Picker — click trace to change color
    // ────────────────────────────────────────────────────────────────────

    // ────────────────────────────────────────────────────────────────────
    // Color Picker Utility — native <input type="color"> for any element
    // ────────────────────────────────────────────────────────────────────
    // Usage:
    //   FV.pickColor(currentHex, callback)           — inline picker
    //   FV.pickColor('#ff0000', function(hex) { ... })
    //
    // Also used internally by enableColorPicker (click-on-element) and
    // openStylePanel (the Style button panel).

    FV.pickColor = function(currentColor, onChange) {
        var input = document.createElement('input');
        input.type = 'color';
        input.value = currentColor || '#4a9f6e';
        input.style.cssText = 'position:fixed;top:-9999px;left:-9999px;opacity:0;width:0;height:0;';
        document.body.appendChild(input);

        input.addEventListener('input', function() {
            if (onChange) onChange(input.value);
        });
        input.addEventListener('change', function() {
            if (onChange) onChange(input.value);
            setTimeout(function() { document.body.removeChild(input); }, 50);
        });
        // If user cancels without changing, clean up on blur
        input.addEventListener('blur', function() {
            setTimeout(function() {
                if (input.parentNode) document.body.removeChild(input);
            }, 200);
        });

        input.click();
        return input;
    };

    // Apply color to any SVG element — resolves the right attribute
    FV._applyColor = function(el, color) {
        var tag = el.tagName.toLowerCase();
        if (tag === 'polyline' || tag === 'line' || tag === 'path') {
            el.setAttribute('stroke', color);
        } else if (tag === 'rect' || tag === 'circle' || tag === 'ellipse') {
            el.setAttribute('fill', color);
        } else if (tag === 'text') {
            el.setAttribute('fill', color);
        } else {
            // Generic fallback
            el.setAttribute('fill', color);
            el.setAttribute('stroke', color);
        }
    };

    // Click any SVG element to change its color via native picker
    FV.enableColorPicker = function(container, onColorChange) {
        var svg = container.querySelector('svg');
        if (!svg) return;

        // Make traces, bars, edges, borders clickable
        var targets = svg.querySelectorAll(
            'polyline, path[stroke], line[stroke], rect[fill], circle[fill], circle[data-trace], ellipse[fill]'
        );

        targets.forEach(function(el) {
            el.style.cursor = 'pointer';
            el.addEventListener('contextmenu', function(e) {
                e.preventDefault();
                var current = el.getAttribute('stroke') || el.getAttribute('fill') || '#4a9f6e';
                // Normalize rgb(...) to hex
                if (current.indexOf('rgb') === 0) {
                    var m = current.match(/(\d+)/g);
                    if (m && m.length >= 3) {
                        current = '#' + ((1<<24)+(+m[0]<<16)+(+m[1]<<8)+(+m[2])).toString(16).slice(1);
                    }
                }
                FV.pickColor(current, function(hex) {
                    FV._applyColor(el, hex);
                    if (onColorChange) onColorChange({ element: el.tagName, color: hex });
                });
            });
        });
    };

    // ────────────────────────────────────────────────────────────────────
    // Axis Label Editing — double-click axis labels to edit
    // ────────────────────────────────────────────────────────────────────

    FV.enableAxisEdit = function(container, onSave) {
        const svg = container.querySelector('svg');
        if (!svg) return;

        // Find axis labels (text elements near edges)
        svg.querySelectorAll('text').forEach(function(textEl) {
            const fontSize = parseFloat(textEl.getAttribute('font-size') || 0);
            const anchor = textEl.getAttribute('text-anchor');

            // Axis labels are font-size 11, positioned at edges
            if (fontSize === 11 && anchor === 'middle') {
                textEl.style.cursor = 'pointer';
                textEl.addEventListener('dblclick', function(e) {
                    const oldText = textEl.textContent;
                    const rect = container.getBoundingClientRect();

                    const input = document.createElement('input');
                    input.type = 'text';
                    input.value = oldText;
                    input.style.cssText = `position:absolute;left:${e.clientX - rect.left - 80}px;top:${e.clientY - rect.top - 10}px;width:160px;background:#1a1a2e;color:#e8efe8;border:1px solid #4a9f6e;padding:2px 6px;border-radius:3px;font-size:11px;font-family:Inter,system-ui;z-index:1001;`;
                    container.appendChild(input);
                    input.focus();
                    input.select();

                    function commit() {
                        textEl.textContent = input.value.trim() || oldText;
                        if (input.parentNode) container.removeChild(input);
                        if (onSave) onSave({ label: textEl.textContent, original: oldText });
                    }

                    input.addEventListener('keydown', function(ke) {
                        if (ke.key === 'Enter') commit();
                        if (ke.key === 'Escape') { if (input.parentNode) container.removeChild(input); }
                    });
                    input.addEventListener('blur', commit);
                });
            }
        });
    };

    // ────────────────────────────────────────────────────────────────────
    // Style Panel — visible color/title/axis editor
    // ────────────────────────────────────────────────────────────────────

    FV.openStylePanel = function(container, onApply) {
        // Toggle — remove if already open
        var existing = container.querySelector('.fv-style-panel');
        if (existing) { existing.remove(); return; }

        var spec = container._currentSpec;
        if (!spec) return;

        var panel = document.createElement('div');
        panel.className = 'fv-style-panel';
        panel.style.cssText = 'background:#111611;border:1px solid rgba(74,159,110,0.25);border-radius:4px;padding:10px 12px;font-family:Inter,system-ui,sans-serif;margin-top:4px;';

        var inputStyle = 'width:100%;background:#0a0f0a;border:1px solid rgba(74,159,110,0.15);color:#e8efe8;padding:4px 6px;border-radius:2px;font:12px/1 Inter,system-ui,sans-serif;box-sizing:border-box;';
        var labelStyle = 'font:600 9px/1 sans-serif;color:#7a8f7a;text-transform:uppercase;letter-spacing:0.08em;display:block;margin-bottom:3px;';
        var rowStyle = 'margin-bottom:8px;';
        var colorRowStyle = 'display:flex;align-items:center;gap:8px;margin-bottom:8px;';

        // Build panel HTML
        var titleVal = (spec.title || '').replace(/"/g, '&quot;');
        var xLabel = ((spec.x_axis && spec.x_axis.label) || '').replace(/"/g, '&quot;');
        var yLabel = ((spec.y_axis && spec.y_axis.label) || '').replace(/"/g, '&quot;');

        // Current trace color (first trace, or accent)
        var traceColor = '#4a9f6e';
        if (spec.traces && spec.traces.length) {
            var t0 = spec.traces[0];
            traceColor = (typeof t0 === 'object' ? t0.color : null) || traceColor;
        }

        // Current background
        var theme = FV.themes[spec.theme] || FV.themes.svend_dark;
        var bgColor = theme.bg || '#0d120d';

        // Current grid color
        var gridColor = theme.grid || 'rgba(255,255,255,0.06)';
        // Approximate grid hex for the color input
        var gridHex = '#1a1a1a';
        if (gridColor.indexOf('#') === 0) gridHex = gridColor;

        // Current axis/border color
        var axisColor = theme.axis || 'rgba(255,255,255,0.15)';
        var axisHex = '#333333';
        if (axisColor.indexOf('#') === 0) axisHex = axisColor;

        var colorInputStyle = 'width:32px;height:22px;border:1px solid rgba(74,159,110,0.2);border-radius:2px;background:none;cursor:pointer;padding:0;';
        var colorLabelStyle = 'font:600 9px/1 sans-serif;color:#7a8f7a;text-transform:uppercase;letter-spacing:0.05em;';
        var colorCellStyle = 'display:flex;flex-direction:column;align-items:center;gap:3px;';

        var html = '';

        // Row 1: text fields — Title, X, Y
        html += '<div style="display:flex;gap:6px;margin-bottom:6px;align-items:flex-end;">';
        html += '<div style="flex:2;"><label style="' + labelStyle + '">Title</label><input class="fv-style-title" type="text" value="' + titleVal + '" placeholder="Chart title" style="' + inputStyle + '"></div>';
        html += '<div style="flex:1;"><label style="' + labelStyle + '">X Axis</label><input class="fv-style-xaxis" type="text" value="' + xLabel + '" placeholder="X" style="' + inputStyle + 'font-size:11px;"></div>';
        html += '<div style="flex:1;"><label style="' + labelStyle + '">Y Axis</label><input class="fv-style-yaxis" type="text" value="' + yLabel + '" placeholder="Y" style="' + inputStyle + 'font-size:11px;"></div>';
        html += '</div>';

        // Row 2: color pickers — all in one horizontal row
        html += '<div style="display:flex;gap:10px;align-items:flex-start;margin-bottom:6px;">';
        html += '<div style="' + colorCellStyle + '"><label style="' + colorLabelStyle + '">Trace</label><input class="fv-style-trace-color" type="color" value="' + traceColor + '" style="' + colorInputStyle + '"></div>';
        html += '<div style="' + colorCellStyle + '"><label style="' + colorLabelStyle + '">Background</label><input class="fv-style-bg-color" type="color" value="' + bgColor + '" style="' + colorInputStyle + '"></div>';
        html += '<div style="' + colorCellStyle + '"><label style="' + colorLabelStyle + '">Grid</label><input class="fv-style-grid-color" type="color" value="' + gridHex + '" style="' + colorInputStyle + '"></div>';
        html += '<div style="' + colorCellStyle + '"><label style="' + colorLabelStyle + '">Axis</label><input class="fv-style-axis-color" type="color" value="' + axisHex + '" style="' + colorInputStyle + '"></div>';
        html += '<button class="fv-style-apply" style="padding:4px 12px;font:700 10px/1 sans-serif;text-transform:uppercase;letter-spacing:0.08em;background:rgba(74,159,110,0.15);border:1px solid rgba(74,159,110,0.3);color:#4a9f6e;border-radius:2px;cursor:pointer;align-self:flex-end;margin-bottom:1px;">Apply</button>';
        html += '<span class="fv-style-close" style="cursor:pointer;color:#7a8f7a;font-size:14px;line-height:1;align-self:flex-start;margin-left:auto;">&times;</span>';
        html += '</div>';

        panel.innerHTML = html;
        container.appendChild(panel);

        // ── Wire interactions ──

        // Close
        panel.querySelector('.fv-style-close').addEventListener('click', function() { panel.remove(); });

        // Apply
        panel.querySelector('.fv-style-apply').addEventListener('click', function() {
            var newTitle = panel.querySelector('.fv-style-title').value;
            var newXAxis = panel.querySelector('.fv-style-xaxis').value;
            var newYAxis = panel.querySelector('.fv-style-yaxis').value;
            var newTraceColor = panel.querySelector('.fv-style-trace-color').value;
            var newBgColor = panel.querySelector('.fv-style-bg-color').value;
            var newGridColor = panel.querySelector('.fv-style-grid-color').value;
            var newAxisColor = panel.querySelector('.fv-style-axis-color').value;

            // Update spec
            spec.title = newTitle;
            if (!spec.x_axis) spec.x_axis = {};
            if (!spec.y_axis) spec.y_axis = {};
            spec.x_axis.label = newXAxis;
            spec.y_axis.label = newYAxis;

            // Apply trace color to all traces
            if (spec.traces) {
                spec.traces.forEach(function(t) {
                    if (typeof t === 'object') t.color = newTraceColor;
                });
            }

            // Apply background, grid, axis via inline theme override
            if (!spec._styleOverrides) spec._styleOverrides = {};
            spec._styleOverrides.bg = newBgColor;
            spec._styleOverrides.plotBg = newBgColor;
            spec._styleOverrides.grid = newGridColor;
            spec._styleOverrides.axis = newAxisColor;

            // Re-render
            panel.remove();
            FV.render(container, spec, container._renderOptions || {});

            if (onApply) onApply(spec);
        });
    };

    // ────────────────────────────────────────────────────────────────────
    // Data Table — show underlying data on hover/click
    // ────────────────────────────────────────────────────────────────────

    FV.showDataTable = function(container, spec) {
        if (!spec.traces || !spec.traces.length) return;

        const table = document.createElement('div');
        table.style.cssText = 'max-height:200px;overflow-y:auto;font-size:11px;font-family:"JetBrains Mono",monospace;border:1px solid rgba(255,255,255,0.1);border-radius:4px;margin-top:4px;';

        let html = '<table style="width:100%;border-collapse:collapse;color:#e8efe8;">';
        html += '<thead><tr style="background:rgba(74,159,110,0.1);">';

        // Headers from first trace
        const t0 = spec.traces[0];
        html += '<th style="padding:3px 6px;text-align:left;border-bottom:1px solid rgba(255,255,255,0.1);">#</th>';
        html += '<th style="padding:3px 6px;text-align:right;border-bottom:1px solid rgba(255,255,255,0.1);">X</th>';
        spec.traces.forEach(function(t, i) {
            html += `<th style="padding:3px 6px;text-align:right;border-bottom:1px solid rgba(255,255,255,0.1);">${t.name || 'Y' + (i + 1)}</th>`;
        });
        html += '</tr></thead><tbody>';

        const n = t0.x ? t0.x.length : 0;
        for (let i = 0; i < n; i++) {
            html += `<tr style="border-bottom:1px solid rgba(255,255,255,0.03);">`;
            html += `<td style="padding:2px 6px;color:#7a8f7a;">${i + 1}</td>`;
            html += `<td style="padding:2px 6px;text-align:right;">${t0.x[i]}</td>`;
            spec.traces.forEach(function(t) {
                const val = t.y && t.y[i] !== undefined ? (typeof t.y[i] === 'number' ? t.y[i].toFixed(4) : t.y[i]) : '—';
                html += `<td style="padding:2px 6px;text-align:right;">${val}</td>`;
            });
            html += '</tr>';
        }
        html += '</tbody></table>';
        table.innerHTML = html;
        container.appendChild(table);

        return table;
    };

    // ────────────────────────────────────────────────────────────────────
    // Enhanced render that stores spec + auto-enables utilities
    // ────────────────────────────────────────────────────────────────────

    const _originalRender = FV.render;

    FV.render = function(container, spec, options) {
        container._currentSpec = spec;
        container._renderOptions = options;
        const instance = _originalRender(container, spec, options);

        // Auto-enable utilities if options say so
        options = options || {};
        if (options.toolbar === true) {
            FV.addToolbar(container, instance, options);
        }
        if (options.editableTitle) {
            FV.enableTitleEdit(container, options.onTitleSave);
        }
        if (options.editableAxes) {
            FV.enableAxisEdit(container, options.onAxisSave);
        }
        if (options.colorPicker) {
            FV.enableColorPicker(container, options.onColorChange);
        }
        if (options.showTable) {
            FV.showDataTable(container, spec);
        }
        if (options.stylePanel) {
            FV.openStylePanel(container, options.onStyleApply);
        }

        return instance;
    };

})(ForgeViz);

// ========================================================================
// COUNTERFACTUAL / SLIDER SYSTEM — What-if exploration
// ========================================================================

(function(FV) {
    'use strict';

    FV.slider = function(container, spec, options) {
        options = options || {};
        const interactive = spec.interactive;
        if (!interactive || interactive.type !== 'slider') {
            return FV.render(container, spec, options);
        }

        const factors = interactive.factors;
        const coefficients = interactive.coefficients;
        const responseName = interactive.response_name || 'Response';
        let currentValues = Object.assign({}, interactive.current_values);

        // Create layout: sliders on left, chart on right
        container.innerHTML = '';
        container.style.display = 'flex';
        container.style.gap = '16px';

        // Slider panel
        const sliderPanel = document.createElement('div');
        sliderPanel.style.cssText = 'width:200px;flex-shrink:0;display:flex;flex-direction:column;gap:10px;padding:8px;';
        container.appendChild(sliderPanel);

        // Prediction display
        const predDisplay = document.createElement('div');
        predDisplay.style.cssText = 'font-size:13px;font-weight:600;color:#4a9f6e;font-family:Inter,system-ui;padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.1);margin-bottom:4px;';
        sliderPanel.appendChild(predDisplay);

        // Chart area
        const chartArea = document.createElement('div');
        chartArea.style.cssText = 'flex:1;min-width:0;';
        container.appendChild(chartArea);

        // Build sliders
        const sliderEls = {};
        factors.forEach(function(factor) {
            const row = document.createElement('div');
            row.style.cssText = 'display:flex;flex-direction:column;gap:2px;';

            const label = document.createElement('div');
            label.style.cssText = 'font-size:10px;color:#9aaa9a;font-family:Inter,system-ui;display:flex;justify-content:space-between;';
            const nameSpan = document.createElement('span');
            nameSpan.textContent = factor.name;
            const valSpan = document.createElement('span');
            valSpan.style.fontFamily = 'JetBrains Mono, monospace';
            valSpan.textContent = (currentValues[factor.name] || 0).toFixed(2);
            label.appendChild(nameSpan);
            label.appendChild(valSpan);
            row.appendChild(label);

            const slider = document.createElement('input');
            slider.type = 'range';
            slider.min = factor.low;
            slider.max = factor.high;
            slider.step = factor.step || ((factor.high - factor.low) / 100);
            slider.value = currentValues[factor.name] || ((factor.low + factor.high) / 2);
            slider.style.cssText = 'width:100%;accent-color:#4a9f6e;';
            row.appendChild(slider);

            sliderEls[factor.name] = { slider: slider, valSpan: valSpan };

            slider.addEventListener('input', function() {
                currentValues[factor.name] = parseFloat(slider.value);
                valSpan.textContent = parseFloat(slider.value).toFixed(2);
                updateChart();
            });

            sliderPanel.appendChild(row);
        });

        // Reset button
        const resetBtn = document.createElement('button');
        resetBtn.textContent = 'Reset';
        resetBtn.style.cssText = 'padding:4px 8px;border-radius:4px;border:1px solid rgba(255,255,255,0.15);background:transparent;color:#94a3b8;font-size:10px;cursor:pointer;margin-top:8px;';
        resetBtn.addEventListener('click', function() {
            currentValues = Object.assign({}, interactive.current_values);
            factors.forEach(function(f) {
                sliderEls[f.name].slider.value = currentValues[f.name];
                sliderEls[f.name].valSpan.textContent = currentValues[f.name].toFixed(2);
            });
            updateChart();
        });
        sliderPanel.appendChild(resetBtn);

        function evaluateModel(values) {
            let pred = coefficients['Intercept'] || 0;
            const names = Object.keys(values);
            names.forEach(function(name) {
                pred += (coefficients[name] || 0) * values[name];
            });
            for (let i = 0; i < names.length; i++) {
                for (let j = i + 1; j < names.length; j++) {
                    const term = names[i] + '*' + names[j];
                    pred += (coefficients[term] || 0) * values[names[i]] * values[names[j]];
                }
            }
            names.forEach(function(name) {
                const term = name + '^2';
                pred += (coefficients[term] || 0) * values[name] * values[name];
            });
            return pred;
        }

        function updateChart() {
            const pred = evaluateModel(currentValues);
            predDisplay.textContent = responseName + ': ' + pred.toFixed(4);

            // Sweep primary factor
            const primary = factors[0];
            const nPts = 50;
            const step = (primary.high - primary.low) / nPts;
            const sweepX = [];
            const sweepY = [];
            for (let i = 0; i <= nPts; i++) {
                const x = primary.low + i * step;
                sweepX.push(x);
                const vals = Object.assign({}, currentValues);
                vals[primary.name] = x;
                sweepY.push(evaluateModel(vals));
            }

            const updatedSpec = Object.assign({}, spec, {
                traces: [
                    { x: sweepX, y: sweepY, name: responseName + ' vs ' + primary.name, trace_type: 'line', color: '#4a9f6e', width: 2, marker_size: 0, dash: '', fill: '', opacity: 1, metadata: {} },
                    { x: [currentValues[primary.name]], y: [pred], name: 'Current', trace_type: 'scatter', color: '#f59e0b', width: 1, marker_size: 10, dash: '', fill: '', opacity: 1, metadata: {} },
                ],
                interactive: null, // prevent recursion
            });

            FV.render(chartArea, updatedSpec, { toolbar: false });
        }

        updateChart();
    };

})(ForgeViz);
