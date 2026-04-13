/**
 * ForgeViz Interact — Advanced interaction extension for ForgeViz charts.
 *
 * Depends on forgeviz.js being loaded first (ForgeViz global must exist).
 *
 * Features:
 *   - Zoom & Pan (box zoom, scroll zoom, drag pan, double-click reset)
 *   - Lasso & Box Selection with CustomEvent dispatch
 *   - Crosshair with coordinate display and snap-to-point
 *   - Data Point Annotations (right-click to annotate)
 *   - Linked Brushing across dashboard charts
 *   - Floating toolbar with SVEND dark theme styling
 *   - Touch support (pinch-to-zoom, drag-to-pan)
 *
 * Usage:
 *   const api = ForgeViz.interact(container, { crosshair: true });
 *   // or auto-enhance:
 *   ForgeViz.render(container, spec, { interactive: true });
 */

(function(FV) {
    'use strict';

    // ====================================================================
    // Constants
    // ====================================================================

    var SNAP_RADIUS = 20;  // px — snap crosshair to nearest point within this
    var MIN_ZOOM_BOX = 8;  // px — minimum drag distance to trigger box zoom
    var ZOOM_FACTOR  = 0.1; // scroll zoom sensitivity
    var TOOLBAR_BG   = 'rgba(13,18,13,0.9)';
    var TOOLBAR_BORDER = '1px solid rgba(255,255,255,0.1)';
    var ACCENT       = '#4a9f6e';

    // ====================================================================
    // Per-instance state (WeakMap keyed by container element)
    // ====================================================================

    var instances = new WeakMap();

    // ====================================================================
    // SVG namespace helper
    // ====================================================================

    function svgEl(tag, attrs) {
        var el = document.createElementNS('http://www.w3.org/2000/svg', tag);
        if (attrs) {
            Object.keys(attrs).forEach(function(k) { el.setAttribute(k, attrs[k]); });
        }
        return el;
    }

    // ====================================================================
    // Geometry helpers
    // ====================================================================

    function clamp(val, lo, hi) {
        return Math.max(lo, Math.min(hi, val));
    }

    function pointInRect(px, py, x1, y1, x2, y2) {
        var minX = Math.min(x1, x2), maxX = Math.max(x1, x2);
        var minY = Math.min(y1, y2), maxY = Math.max(y1, y2);
        return px >= minX && px <= maxX && py >= minY && py <= maxY;
    }

    function pointInPolygon(px, py, polygon) {
        // Ray-casting algorithm
        var inside = false;
        for (var i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
            var xi = polygon[i][0], yi = polygon[i][1];
            var xj = polygon[j][0], yj = polygon[j][1];
            if ((yi > py) !== (yj > py) &&
                px < (xj - xi) * (py - yi) / (yj - yi) + xi) {
                inside = !inside;
            }
        }
        return inside;
    }

    function dist(x1, y1, x2, y2) {
        var dx = x2 - x1, dy = y2 - y1;
        return Math.sqrt(dx * dx + dy * dy);
    }

    // ====================================================================
    // Collect data points from an existing rendered SVG
    // ====================================================================

    function collectDataPoints(svg) {
        var points = [];
        var circles = svg.querySelectorAll('circle[data-idx]');
        circles.forEach(function(el) {
            points.push({
                el: el,
                cx: parseFloat(el.getAttribute('cx')),
                cy: parseFloat(el.getAttribute('cy')),
                idx: parseInt(el.getAttribute('data-idx'), 10),
                trace: parseInt(el.getAttribute('data-trace') || '0', 10),
                dataX: parseFloat(el.getAttribute('data-x')),
                dataY: parseFloat(el.getAttribute('data-y')),
                origR: parseFloat(el.getAttribute('r')) || 3,
                origFill: el.getAttribute('fill'),
            });
        });
        return points;
    }

    // ====================================================================
    // Read plot geometry from container._scales (set by forgeviz.js)
    // ====================================================================

    function getPlotBounds(container) {
        var s = container._scales;
        if (!s) return null;
        return {
            plotLeft: s.xRange[0],
            plotRight: s.xRange[1],
            plotTop: s.yRange[1],     // yRange is [bottom, top] in SVG coords
            plotBottom: s.yRange[0],
            plotWidth: s.xRange[1] - s.xRange[0],
            plotHeight: s.yRange[0] - s.yRange[1],
            xDomain: s.xDomain.slice(),
            yDomain: s.yDomain.slice(),
            invertX: s.invertX,
            invertY: s.invertY,
            sx: s.sx,
            sy: s.sy,
        };
    }

    // ====================================================================
    // SVG icon paths (simple 16x16 viewBox icons)
    // ====================================================================

    var ICONS = {
        zoomIn:    'M11 5H7m0 0H3m4 0V1m0 4v4m5 4l3 3M7 11A6 6 0 107 1a6 6 0 000 10z',
        zoomOut:   'M3 5h8m5 8l-3-3M7 11A6 6 0 107 1a6 6 0 000 10z',
        zoomReset: 'M2 2l4 4m8-4l-4 4m-8 8l4-4m8 4l-4-4M8 4v8M4 8h8',
        boxSelect: 'M2 2h4v4H2zm8 8h4v4h-4zM6 6l4 4',
        lasso:     'M12 3c0-1.1-.9-2-2-2S8 1.9 8 3c0 .7.4 1.4 1 1.7V8l-5 4v2h2l4-3.5L14 14h2v-2l-5-4V4.7c.6-.3 1-1 1-1.7z',
        crosshair: 'M8 1v14M1 8h14M8 5a3 3 0 100 6 3 3 0 000-6z',
        download:  'M8 1v10m0 0l-3-3m3 3l3-3M2 12v2h12v-2',
        fullscreen:'M2 6V2h4m4 0h4v4m0 4v4h-4m-4 0H2v-4',
        pan:       'M8 1v4m0 6v4M1 8h4m6 0h4M5 5L3 3m10 10l-2-2m0-6l2-2M5 11l-2 2',
    };

    function createIcon(name, size) {
        size = size || 14;
        var svg = svgEl('svg', {
            width: size, height: size, viewBox: '0 0 16 16',
            fill: 'none', stroke: ACCENT, 'stroke-width': '1.5',
            'stroke-linecap': 'round', 'stroke-linejoin': 'round',
        });
        svg.innerHTML = '<path d="' + (ICONS[name] || '') + '"/>';
        return svg;
    }

    // ====================================================================
    // Toolbar
    // ====================================================================

    function createToolbar(container, state, api) {
        var bar = document.createElement('div');
        bar.className = 'fvi-toolbar';
        bar.style.cssText = [
            'position:absolute', 'top:4px', 'right:4px',
            'display:flex', 'gap:2px', 'padding:3px 4px',
            'background:' + TOOLBAR_BG, 'border:' + TOOLBAR_BORDER,
            'border-radius:6px', 'z-index:1002',
            'opacity:0', 'transition:opacity 0.15s',
            'pointer-events:none',
        ].join(';') + ';';

        function makeBtn(iconName, title, onClick) {
            var btn = document.createElement('button');
            btn.title = title;
            btn.style.cssText = [
                'background:none', 'border:none', 'padding:3px',
                'cursor:pointer', 'border-radius:3px', 'display:flex',
                'align-items:center', 'justify-content:center',
                'transition:background 0.1s',
            ].join(';') + ';';
            btn.appendChild(createIcon(iconName));
            btn.addEventListener('click', function(e) {
                e.stopPropagation();
                onClick(btn);
            });
            btn.addEventListener('mouseenter', function() {
                btn.style.background = 'rgba(74,159,110,0.2)';
            });
            btn.addEventListener('mouseleave', function() {
                btn.style.background = 'none';
            });
            return btn;
        }

        // Mode toggle helper — highlights active button
        var modeButtons = {};
        function setActiveMode(mode) {
            state.mode = mode;
            Object.keys(modeButtons).forEach(function(k) {
                modeButtons[k].style.background =
                    (k === mode) ? 'rgba(74,159,110,0.3)' : 'none';
            });
        }

        // Zoom In
        bar.appendChild(makeBtn('zoomIn', 'Zoom In', function() {
            zoomBy(container, state, 0.3);
        }));

        // Zoom Out
        bar.appendChild(makeBtn('zoomOut', 'Zoom Out', function() {
            zoomBy(container, state, -0.3);
        }));

        // Reset Zoom
        bar.appendChild(makeBtn('zoomReset', 'Reset Zoom (double-click)', function() {
            api.resetZoom();
        }));

        // Separator
        var sep1 = document.createElement('div');
        sep1.style.cssText = 'width:1px;background:rgba(255,255,255,0.1);margin:2px 2px;';
        bar.appendChild(sep1);

        // Pan mode
        var panBtn = makeBtn('pan', 'Pan Mode', function() {
            setActiveMode(state.mode === 'pan' ? 'default' : 'pan');
            updateCursor(container, state);
        });
        modeButtons.pan = panBtn;
        bar.appendChild(panBtn);

        // Box select
        var boxBtn = makeBtn('boxSelect', 'Box Select (Shift+drag)', function() {
            setActiveMode(state.mode === 'select-box' ? 'default' : 'select-box');
            updateCursor(container, state);
        });
        modeButtons['select-box'] = boxBtn;
        bar.appendChild(boxBtn);

        // Lasso select
        var lassoBtn = makeBtn('lasso', 'Lasso Select (Alt+drag)', function() {
            setActiveMode(state.mode === 'select-lasso' ? 'default' : 'select-lasso');
            updateCursor(container, state);
        });
        modeButtons['select-lasso'] = lassoBtn;
        bar.appendChild(lassoBtn);

        // Separator
        var sep2 = document.createElement('div');
        sep2.style.cssText = 'width:1px;background:rgba(255,255,255,0.1);margin:2px 2px;';
        bar.appendChild(sep2);

        // Crosshair toggle
        var chBtn = makeBtn('crosshair', 'Toggle Crosshair', function(btn) {
            state.crosshair = !state.crosshair;
            btn.style.background = state.crosshair
                ? 'rgba(74,159,110,0.3)' : 'none';
            if (!state.crosshair) removeCrosshair(state);
        });
        bar.appendChild(chBtn);

        // Download SVG
        bar.appendChild(makeBtn('download', 'Download SVG', function() {
            var svg = container.querySelector('svg');
            if (!svg) return;
            var svgStr = new XMLSerializer().serializeToString(svg);
            var blob = new Blob([svgStr], { type: 'image/svg+xml' });
            var url = URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.href = url; a.download = 'chart.svg'; a.click();
            URL.revokeObjectURL(url);
        }));

        // Fullscreen
        bar.appendChild(makeBtn('fullscreen', 'Fullscreen', function() {
            if (!document.fullscreenElement) {
                container.requestFullscreen().catch(function() {});
            } else {
                document.exitFullscreen();
            }
        }));

        container.appendChild(bar);

        // Show/hide toolbar on hover
        container.addEventListener('mouseenter', function() {
            bar.style.opacity = '1';
            bar.style.pointerEvents = 'auto';
        });
        container.addEventListener('mouseleave', function() {
            bar.style.opacity = '0';
            bar.style.pointerEvents = 'none';
        });

        return bar;
    }

    // ====================================================================
    // Cursor management
    // ====================================================================

    function updateCursor(container, state) {
        var svg = container.querySelector('svg');
        if (!svg) return;
        switch (state.mode) {
            case 'pan':          svg.style.cursor = 'grab'; break;
            case 'select-box':   svg.style.cursor = 'crosshair'; break;
            case 'select-lasso': svg.style.cursor = 'crosshair'; break;
            default:             svg.style.cursor = 'default'; break;
        }
    }

    // ====================================================================
    // Crosshair
    // ====================================================================

    function ensureCrosshairLayer(state, svg) {
        if (state._crosshairGroup) return state._crosshairGroup;
        var g = svgEl('g', { class: 'fvi-crosshair' });
        var hLine = svgEl('line', {
            stroke: 'rgba(255,255,255,0.25)', 'stroke-width': '1',
            'stroke-dasharray': '4,3', 'pointer-events': 'none',
        });
        var vLine = svgEl('line', {
            stroke: 'rgba(255,255,255,0.25)', 'stroke-width': '1',
            'stroke-dasharray': '4,3', 'pointer-events': 'none',
        });
        var label = svgEl('text', {
            fill: '#e8efe8', 'font-size': '10',
            'font-family': 'JetBrains Mono,monospace',
            'pointer-events': 'none',
        });
        // Background rect behind label for readability
        var labelBg = svgEl('rect', {
            fill: 'rgba(13,18,13,0.85)', rx: '3', 'pointer-events': 'none',
        });
        g.appendChild(hLine);
        g.appendChild(vLine);
        g.appendChild(labelBg);
        g.appendChild(label);
        svg.appendChild(g);
        state._crosshairGroup = g;
        state._chH = hLine;
        state._chV = vLine;
        state._chLabel = label;
        state._chLabelBg = labelBg;
        return g;
    }

    function updateCrosshair(state, container, mx, my) {
        var svg = container.querySelector('svg');
        if (!svg) return;
        var bounds = getPlotBounds(container);
        if (!bounds) return;

        // Clamp to plot area
        var px = clamp(mx, bounds.plotLeft, bounds.plotRight);
        var py = clamp(my, bounds.plotTop, bounds.plotBottom);

        // Check if cursor is within plot area
        if (mx < bounds.plotLeft || mx > bounds.plotRight ||
            my < bounds.plotTop  || my > bounds.plotBottom) {
            removeCrosshair(state);
            return;
        }

        var g = ensureCrosshairLayer(state, svg);
        g.style.display = '';

        // Snap to nearest data point
        var dataX = bounds.invertX(px);
        var dataY = bounds.invertY(py);
        var snapped = false;
        var points = state._dataPoints || [];

        var nearest = null, nearestDist = SNAP_RADIUS;
        for (var i = 0; i < points.length; i++) {
            var d = dist(px, py, points[i].cx, points[i].cy);
            if (d < nearestDist) {
                nearestDist = d;
                nearest = points[i];
            }
        }

        if (nearest) {
            px = nearest.cx;
            py = nearest.cy;
            dataX = nearest.dataX;
            dataY = nearest.dataY;
            snapped = true;
        }

        // Draw crosshair lines
        state._chH.setAttribute('x1', bounds.plotLeft);
        state._chH.setAttribute('x2', bounds.plotRight);
        state._chH.setAttribute('y1', py);
        state._chH.setAttribute('y2', py);
        state._chV.setAttribute('x1', px);
        state._chV.setAttribute('x2', px);
        state._chV.setAttribute('y1', bounds.plotTop);
        state._chV.setAttribute('y2', bounds.plotBottom);

        // Coordinate label
        var xStr = typeof dataX === 'number' ? dataX.toFixed(2) : dataX;
        var yStr = typeof dataY === 'number' ? dataY.toFixed(2) : dataY;
        var labelText = xStr + ', ' + yStr;
        state._chLabel.textContent = labelText;

        // Position label — offset from crosshair to avoid overlap
        var labelX = px + 8;
        var labelY = py - 10;
        // Flip if near edges
        if (labelX + 80 > bounds.plotRight) labelX = px - 80;
        if (labelY - 6 < bounds.plotTop) labelY = py + 16;

        state._chLabel.setAttribute('x', labelX);
        state._chLabel.setAttribute('y', labelY);

        // Background for label
        var textLen = labelText.length * 6.2 + 8;
        state._chLabelBg.setAttribute('x', labelX - 4);
        state._chLabelBg.setAttribute('y', labelY - 11);
        state._chLabelBg.setAttribute('width', textLen);
        state._chLabelBg.setAttribute('height', 15);

        // Highlight snapped point
        if (snapped) {
            state._chH.setAttribute('stroke', 'rgba(74,159,110,0.5)');
            state._chV.setAttribute('stroke', 'rgba(74,159,110,0.5)');
        } else {
            state._chH.setAttribute('stroke', 'rgba(255,255,255,0.25)');
            state._chV.setAttribute('stroke', 'rgba(255,255,255,0.25)');
        }
    }

    function removeCrosshair(state) {
        if (state._crosshairGroup) {
            state._crosshairGroup.style.display = 'none';
        }
    }

    // ====================================================================
    // Zoom & Pan
    // ====================================================================

    /**
     * Apply a zoom/pan transform by re-rendering with modified view bounds.
     * We store the current view in state.viewBox and re-render the chart.
     */
    function rerender(container, state) {
        if (!container._currentSpec) return;
        var spec = container._currentSpec;
        var opts = container._renderOptions || {};

        // If we have a viewBox override, inject it as axis overrides
        if (state.viewBox) {
            if (!spec.x_axis) spec.x_axis = {};
            if (!spec.y_axis) spec.y_axis = {};
            spec.x_axis._viewMin = state.viewBox.xMin;
            spec.x_axis._viewMax = state.viewBox.xMax;
            spec.y_axis._viewMin = state.viewBox.yMin;
            spec.y_axis._viewMax = state.viewBox.yMax;
        } else {
            // Clear view overrides
            if (spec.x_axis) { delete spec.x_axis._viewMin; delete spec.x_axis._viewMax; }
            if (spec.y_axis) { delete spec.y_axis._viewMin; delete spec.y_axis._viewMax; }
        }

        // Re-render (this calls FV.render which resets the SVG)
        // We suppress the interact auto-hook to avoid infinite loop
        state._suppressAutoInteract = true;
        FV.render(container, spec, opts);
        state._suppressAutoInteract = false;

        // Re-collect data points and re-attach event listeners
        var svg = container.querySelector('svg');
        if (svg) {
            state._dataPoints = collectDataPoints(svg);
            attachSVGListeners(container, state, svg);
            updateCursor(container, state);
            // Restore selection highlights
            restoreSelection(state);
            // Restore annotations
            restoreAnnotations(container, state, svg);
        }
    }

    function zoomBy(container, state, factor, centerX, centerY) {
        var bounds = getPlotBounds(container);
        if (!bounds) return;

        var vb = state.viewBox || {
            xMin: bounds.xDomain[0], xMax: bounds.xDomain[1],
            yMin: bounds.yDomain[0], yMax: bounds.yDomain[1],
        };

        var xRange = vb.xMax - vb.xMin;
        var yRange = vb.yMax - vb.yMin;

        // Zoom center in data coordinates — default to center of view
        var cx = (centerX !== undefined) ? bounds.invertX(centerX) : (vb.xMin + vb.xMax) / 2;
        var cy = (centerY !== undefined) ? bounds.invertY(centerY) : (vb.yMin + vb.yMax) / 2;

        // Clamp center within current view
        cx = clamp(cx, vb.xMin, vb.xMax);
        cy = clamp(cy, vb.yMin, vb.yMax);

        var zf = 1 - factor; // factor > 0 zooms in
        var newXRange = xRange * zf;
        var newYRange = yRange * zf;

        // Maintain center point proportion
        var cxRatio = (cx - vb.xMin) / xRange;
        var cyRatio = (cy - vb.yMin) / yRange;

        state.viewBox = {
            xMin: cx - newXRange * cxRatio,
            xMax: cx + newXRange * (1 - cxRatio),
            yMin: cy - newYRange * cyRatio,
            yMax: cy + newYRange * (1 - cyRatio),
        };

        rerender(container, state);
    }

    function zoomToRect(container, state, px1, py1, px2, py2) {
        var bounds = getPlotBounds(container);
        if (!bounds) return;

        // Convert pixel coordinates to data coordinates
        var x1 = bounds.invertX(Math.min(px1, px2));
        var x2 = bounds.invertX(Math.max(px1, px2));
        var y1 = bounds.invertY(Math.max(py1, py2)); // SVG y is inverted
        var y2 = bounds.invertY(Math.min(py1, py2));

        state.viewBox = { xMin: x1, xMax: x2, yMin: y1, yMax: y2 };
        rerender(container, state);
    }

    // ====================================================================
    // Selection
    // ====================================================================

    function selectPointsInRect(state, x1, y1, x2, y2) {
        var selected = [];
        var points = state._dataPoints || [];
        for (var i = 0; i < points.length; i++) {
            var p = points[i];
            if (pointInRect(p.cx, p.cy, x1, y1, x2, y2)) {
                selected.push(p);
            }
        }
        return selected;
    }

    function selectPointsInLasso(state, polygon) {
        var selected = [];
        var points = state._dataPoints || [];
        for (var i = 0; i < points.length; i++) {
            var p = points[i];
            if (pointInPolygon(p.cx, p.cy, polygon)) {
                selected.push(p);
            }
        }
        return selected;
    }

    function applySelection(container, state, selected) {
        // Clear previous selection highlights
        clearSelectionHighlight(state);

        state.selection = selected.map(function(p) { return p.idx; });
        state._selectedPoints = selected;

        // Highlight selected points
        selected.forEach(function(p) {
            p.el.setAttribute('r', p.origR * 1.8);
            p.el.setAttribute('stroke', '#ffffff');
            p.el.setAttribute('stroke-width', '2');
            p.el.setAttribute('opacity', '1');
        });

        // Dim unselected points
        var allPoints = state._dataPoints || [];
        var selectedSet = new Set(selected.map(function(p) { return p.el; }));
        allPoints.forEach(function(p) {
            if (!selectedSet.has(p.el)) {
                p.el.setAttribute('opacity', '0.25');
            }
        });

        // Emit selection event
        container.dispatchEvent(new CustomEvent('forgeviz:select', {
            detail: {
                indices: state.selection.slice(),
                points: selected.map(function(p) {
                    return { x: p.dataX, y: p.dataY, index: p.idx, trace: p.trace };
                }),
            },
            bubbles: true,
        }));

        // Emit brush for linked charts
        if (state.linked) {
            emitBrush(container, state, selected);
        }
    }

    function clearSelectionHighlight(state) {
        var points = state._dataPoints || [];
        points.forEach(function(p) {
            p.el.setAttribute('r', p.origR);
            p.el.removeAttribute('stroke-width');
            p.el.setAttribute('opacity', '1');
            if (p.origFill) p.el.setAttribute('fill', p.origFill);
        });
    }

    function restoreSelection(state) {
        // Re-highlight previously selected indices after re-render
        if (!state.selection || !state.selection.length) return;
        var points = state._dataPoints || [];
        var selSet = new Set(state.selection);
        var selected = points.filter(function(p) { return selSet.has(p.idx); });
        if (selected.length) {
            selected.forEach(function(p) {
                p.el.setAttribute('r', p.origR * 1.8);
                p.el.setAttribute('stroke', '#ffffff');
                p.el.setAttribute('stroke-width', '2');
                p.el.setAttribute('opacity', '1');
            });
            var selectedEls = new Set(selected.map(function(p) { return p.el; }));
            points.forEach(function(p) {
                if (!selectedEls.has(p.el)) {
                    p.el.setAttribute('opacity', '0.25');
                }
            });
        }
    }

    // ====================================================================
    // Annotations
    // ====================================================================

    function addAnnotation(container, state, dataX, dataY, text) {
        var annotation = {
            x: dataX,
            y: dataY,
            text: text,
            id: 'ann-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6),
            timestamp: new Date().toISOString(),
        };
        state.annotations.push(annotation);
        renderAnnotation(container, state, annotation);

        container.dispatchEvent(new CustomEvent('forgeviz:annotate', {
            detail: annotation,
            bubbles: true,
        }));

        return annotation;
    }

    function renderAnnotation(container, state, ann) {
        var svg = container.querySelector('svg');
        var bounds = getPlotBounds(container);
        if (!svg || !bounds) return;

        var px = bounds.sx(ann.x);
        var py = bounds.sy(ann.y);

        var g = svgEl('g', {
            class: 'fvi-annotation',
            'data-ann-id': ann.id,
        });

        // Arrow line from label to point
        var labelX = px + 20;
        var labelY = py - 24;
        // Flip if near right edge
        if (labelX + 60 > bounds.plotRight) labelX = px - 80;
        if (labelY < bounds.plotTop + 10) labelY = py + 24;

        g.appendChild(svgEl('line', {
            x1: px, y1: py, x2: labelX, y2: labelY + 6,
            stroke: '#e8c547', 'stroke-width': '1', 'stroke-dasharray': '3,2',
            'pointer-events': 'none',
        }));

        // Small circle at the point
        g.appendChild(svgEl('circle', {
            cx: px, cy: py, r: '3', fill: '#e8c547',
            'pointer-events': 'none',
        }));

        // Label background
        var textW = ann.text.length * 6.2 + 12;
        g.appendChild(svgEl('rect', {
            x: labelX - 4, y: labelY - 10,
            width: textW, height: 16,
            fill: 'rgba(0,0,0,0.8)', rx: '3',
            stroke: '#e8c547', 'stroke-width': '0.5',
            'pointer-events': 'none',
        }));

        // Label text
        g.appendChild(svgEl('text', {
            x: labelX + 2, y: labelY + 2,
            fill: '#e8c547', 'font-size': '10',
            'font-family': 'Inter,system-ui,sans-serif',
            'pointer-events': 'none',
        })).textContent = ann.text;

        svg.appendChild(g);
    }

    function restoreAnnotations(container, state, svg) {
        state.annotations.forEach(function(ann) {
            renderAnnotation(container, state, ann);
        });
    }

    function showAnnotationInput(container, state, dataX, dataY, pixelX, pixelY) {
        var input = document.createElement('input');
        input.type = 'text';
        input.placeholder = 'Add annotation...';
        input.style.cssText = [
            'position:absolute',
            'background:rgba(13,18,13,0.95)',
            'color:#e8efe8',
            'border:1px solid ' + ACCENT,
            'padding:4px 8px',
            'border-radius:4px',
            'font-size:11px',
            'font-family:Inter,system-ui,sans-serif',
            'z-index:1003',
            'width:180px',
            'outline:none',
            'left:' + (pixelX + 8) + 'px',
            'top:' + (pixelY - 12) + 'px',
        ].join(';') + ';';

        container.appendChild(input);
        input.focus();

        function commit() {
            var text = input.value.trim();
            if (text) {
                addAnnotation(container, state, dataX, dataY, text);
            }
            cleanup();
        }

        function cleanup() {
            if (input.parentNode) input.parentNode.removeChild(input);
        }

        input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') commit();
            else if (e.key === 'Escape') cleanup();
        });
        input.addEventListener('blur', function() {
            // Slight delay to allow Enter to fire first
            setTimeout(cleanup, 100);
        });
    }

    // ====================================================================
    // Linked Brushing
    // ====================================================================

    var _linkGroups = {};  // groupName -> Set<container>

    function emitBrush(container, state, selected) {
        var groupName = state.linkGroup;
        if (!groupName) return;

        var detail = {
            group: groupName,
            source: container,
            indices: selected.map(function(p) { return p.idx; }),
            field: state.linkField || null,
            values: selected.map(function(p) {
                return { x: p.dataX, y: p.dataY, index: p.idx };
            }),
        };

        container.dispatchEvent(new CustomEvent('forgeviz:brush', {
            detail: detail,
            bubbles: true,
        }));

        // Notify other charts in the same link group
        var group = _linkGroups[groupName];
        if (!group) return;
        group.forEach(function(peer) {
            if (peer === container) return;
            var peerState = instances.get(peer);
            if (!peerState) return;
            highlightLinkedPoints(peer, peerState, detail.indices, detail.field);
        });
    }

    function highlightLinkedPoints(container, state, indices, field) {
        var points = state._dataPoints || [];
        var idxSet = new Set(indices);

        points.forEach(function(p) {
            if (idxSet.has(p.idx)) {
                p.el.setAttribute('r', p.origR * 1.8);
                p.el.setAttribute('stroke', '#e8c547');
                p.el.setAttribute('stroke-width', '2');
                p.el.setAttribute('opacity', '1');
            } else {
                p.el.setAttribute('opacity', '0.2');
            }
        });
    }

    function joinLinkGroup(container, state, groupName) {
        state.linkGroup = groupName;
        state.linked = true;
        if (!_linkGroups[groupName]) _linkGroups[groupName] = new Set();
        _linkGroups[groupName].add(container);
    }

    function leaveLinkGroup(container, state) {
        if (state.linkGroup && _linkGroups[state.linkGroup]) {
            _linkGroups[state.linkGroup].delete(container);
        }
        state.linkGroup = null;
        state.linked = false;
    }

    // ====================================================================
    // Overlay elements (selection rectangles, lasso paths)
    // ====================================================================

    function createOverlayRect(svg) {
        var rect = svgEl('rect', {
            fill: 'rgba(74,159,110,0.12)',
            stroke: ACCENT,
            'stroke-width': '1',
            'stroke-dasharray': '4,3',
            'pointer-events': 'none',
        });
        svg.appendChild(rect);
        return rect;
    }

    function updateOverlayRect(rect, x1, y1, x2, y2) {
        rect.setAttribute('x', Math.min(x1, x2));
        rect.setAttribute('y', Math.min(y1, y2));
        rect.setAttribute('width', Math.abs(x2 - x1));
        rect.setAttribute('height', Math.abs(y2 - y1));
    }

    function createLassoPath(svg) {
        var path = svgEl('path', {
            fill: 'rgba(74,159,110,0.08)',
            stroke: ACCENT,
            'stroke-width': '1',
            'stroke-dasharray': '3,2',
            'pointer-events': 'none',
        });
        svg.appendChild(path);
        return path;
    }

    function updateLassoPath(path, points) {
        if (points.length < 2) return;
        var d = 'M' + points[0][0] + ',' + points[0][1];
        for (var i = 1; i < points.length; i++) {
            d += 'L' + points[i][0] + ',' + points[i][1];
        }
        d += 'Z';
        path.setAttribute('d', d);
    }

    // ====================================================================
    // SVG Mouse/Touch event listeners
    // ====================================================================

    function attachSVGListeners(container, state, svg) {
        // Remove previous listener controller if any
        if (state._abortController) state._abortController.abort();
        var ac = new AbortController();
        state._abortController = ac;
        var signal = ac.signal;

        var dragState = {
            active: false,
            startX: 0, startY: 0,
            lastX: 0, lastY: 0,
            overlay: null,   // rect or path element
            lassoPoints: [], // for lasso selection
            type: null,      // 'zoom', 'pan', 'select-box', 'select-lasso'
        };

        function getSVGCoords(e) {
            var rect = svg.getBoundingClientRect();
            return {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top,
            };
        }

        // --- Mouse Down ---
        svg.addEventListener('mousedown', function(e) {
            if (e.button !== 0) return; // left click only
            var pos = getSVGCoords(e);
            var bounds = getPlotBounds(container);
            if (!bounds) return;

            // Outside plot area — ignore
            if (pos.x < bounds.plotLeft || pos.x > bounds.plotRight ||
                pos.y < bounds.plotTop  || pos.y > bounds.plotBottom) return;

            var mode = state.mode;

            // Modifier keys override mode
            if (e.shiftKey) mode = 'select-box';
            else if (e.altKey) mode = 'select-lasso';

            // If no explicit mode and viewBox exists (zoomed in), default to box zoom
            if (mode === 'default') {
                mode = state.viewBox ? 'pan' : 'zoom';
            }

            dragState.active = true;
            dragState.startX = pos.x;
            dragState.startY = pos.y;
            dragState.lastX = pos.x;
            dragState.lastY = pos.y;
            dragState.type = mode;
            dragState.lassoPoints = [[pos.x, pos.y]];

            if (mode === 'zoom' || mode === 'select-box') {
                dragState.overlay = createOverlayRect(svg);
            } else if (mode === 'select-lasso') {
                dragState.overlay = createLassoPath(svg);
            } else if (mode === 'pan') {
                svg.style.cursor = 'grabbing';
            }

            e.preventDefault();
        }, { signal: signal });

        // --- Mouse Move ---
        svg.addEventListener('mousemove', function(e) {
            var pos = getSVGCoords(e);

            // Crosshair
            if (state.crosshair && !dragState.active) {
                requestAnimationFrame(function() {
                    updateCrosshair(state, container, pos.x, pos.y);
                });
            }

            if (!dragState.active) return;

            var dx = pos.x - dragState.lastX;
            var dy = pos.y - dragState.lastY;
            dragState.lastX = pos.x;
            dragState.lastY = pos.y;

            if (dragState.type === 'zoom' || dragState.type === 'select-box') {
                updateOverlayRect(dragState.overlay, dragState.startX, dragState.startY, pos.x, pos.y);
            } else if (dragState.type === 'select-lasso') {
                dragState.lassoPoints.push([pos.x, pos.y]);
                updateLassoPath(dragState.overlay, dragState.lassoPoints);
            } else if (dragState.type === 'pan') {
                // Pan: shift viewBox by pixel delta converted to data units
                var bounds = getPlotBounds(container);
                if (!bounds) return;
                var vb = state.viewBox || {
                    xMin: bounds.xDomain[0], xMax: bounds.xDomain[1],
                    yMin: bounds.yDomain[0], yMax: bounds.yDomain[1],
                };
                var xRange = vb.xMax - vb.xMin;
                var yRange = vb.yMax - vb.yMin;
                var dxData = -dx / bounds.plotWidth * xRange;
                var dyData = dy / bounds.plotHeight * yRange;

                state.viewBox = {
                    xMin: vb.xMin + dxData,
                    xMax: vb.xMax + dxData,
                    yMin: vb.yMin + dyData,
                    yMax: vb.yMax + dyData,
                };
                rerender(container, state);
            }

            e.preventDefault();
        }, { signal: signal });

        // --- Mouse Up ---
        svg.addEventListener('mouseup', function(e) {
            if (!dragState.active) return;
            dragState.active = false;
            var pos = getSVGCoords(e);

            var dragDist = dist(dragState.startX, dragState.startY, pos.x, pos.y);

            if (dragState.type === 'zoom') {
                if (dragState.overlay) dragState.overlay.remove();
                if (dragDist > MIN_ZOOM_BOX) {
                    zoomToRect(container, state,
                        dragState.startX, dragState.startY, pos.x, pos.y);
                }
            } else if (dragState.type === 'select-box') {
                if (dragState.overlay) dragState.overlay.remove();
                if (dragDist > MIN_ZOOM_BOX) {
                    var selected = selectPointsInRect(state,
                        dragState.startX, dragState.startY, pos.x, pos.y);
                    applySelection(container, state, selected);
                }
            } else if (dragState.type === 'select-lasso') {
                if (dragState.overlay) dragState.overlay.remove();
                if (dragState.lassoPoints.length > 4) {
                    var selected = selectPointsInLasso(state, dragState.lassoPoints);
                    applySelection(container, state, selected);
                }
            } else if (dragState.type === 'pan') {
                svg.style.cursor = state.mode === 'pan' ? 'grab' : 'default';
            }

            dragState.overlay = null;
            dragState.lassoPoints = [];
        }, { signal: signal });

        // --- Double Click: reset zoom ---
        svg.addEventListener('dblclick', function(e) {
            e.preventDefault();
            state.viewBox = null;
            state.selection = [];
            clearSelectionHighlight(state);
            rerender(container, state);
        }, { signal: signal });

        // --- Mouse Wheel: scroll zoom ---
        svg.addEventListener('wheel', function(e) {
            e.preventDefault();
            var pos = getSVGCoords(e);
            var bounds = getPlotBounds(container);
            if (!bounds) return;

            // Outside plot area — ignore
            if (pos.x < bounds.plotLeft || pos.x > bounds.plotRight ||
                pos.y < bounds.plotTop  || pos.y > bounds.plotBottom) return;

            var factor = e.deltaY < 0 ? ZOOM_FACTOR : -ZOOM_FACTOR;
            zoomBy(container, state, factor, pos.x, pos.y);
        }, { passive: false, signal: signal });

        // --- Right Click: annotation ---
        svg.addEventListener('contextmenu', function(e) {
            var pos = getSVGCoords(e);
            var bounds = getPlotBounds(container);
            if (!bounds) return;

            // Check if near a data point
            var points = state._dataPoints || [];
            var nearest = null, nearestDist = SNAP_RADIUS;
            for (var i = 0; i < points.length; i++) {
                var d = dist(pos.x, pos.y, points[i].cx, points[i].cy);
                if (d < nearestDist) {
                    nearestDist = d;
                    nearest = points[i];
                }
            }

            if (nearest) {
                e.preventDefault();
                var cRect = container.getBoundingClientRect();
                showAnnotationInput(container, state,
                    nearest.dataX, nearest.dataY,
                    e.clientX - cRect.left, e.clientY - cRect.top);
            }
        }, { signal: signal });

        // --- Click on empty space: clear selection ---
        svg.addEventListener('click', function(e) {
            // If the click target is the SVG itself (not a data point), clear selection
            if (e.target === svg || e.target.tagName === 'line' || e.target.tagName === 'rect') {
                if (state.selection.length > 0 && !e.shiftKey && !e.altKey) {
                    state.selection = [];
                    state._selectedPoints = [];
                    clearSelectionHighlight(state);

                    // Notify linked charts
                    if (state.linked) {
                        var groupName = state.linkGroup;
                        if (groupName && _linkGroups[groupName]) {
                            _linkGroups[groupName].forEach(function(peer) {
                                if (peer === container) return;
                                var ps = instances.get(peer);
                                if (ps) clearSelectionHighlight(ps);
                            });
                        }
                    }
                }
            }
        }, { signal: signal });

        // --- Mouse Leave: hide crosshair ---
        svg.addEventListener('mouseleave', function() {
            removeCrosshair(state);
            if (dragState.active) {
                dragState.active = false;
                if (dragState.overlay) {
                    dragState.overlay.remove();
                    dragState.overlay = null;
                }
            }
        }, { signal: signal });

        // --- Touch Support ---
        attachTouchListeners(container, state, svg, signal);
    }

    // ====================================================================
    // Touch event support (pinch-to-zoom, drag-to-pan)
    // ====================================================================

    function attachTouchListeners(container, state, svg, signal) {
        var touchState = {
            tracking: false,
            startTouches: null,
            lastPinchDist: 0,
            lastCenterX: 0,
            lastCenterY: 0,
        };

        function getTouchCenter(touches) {
            if (touches.length === 1) {
                var rect = svg.getBoundingClientRect();
                return { x: touches[0].clientX - rect.left, y: touches[0].clientY - rect.top };
            }
            var rect = svg.getBoundingClientRect();
            return {
                x: (touches[0].clientX + touches[1].clientX) / 2 - rect.left,
                y: (touches[0].clientY + touches[1].clientY) / 2 - rect.top,
            };
        }

        function getPinchDist(touches) {
            if (touches.length < 2) return 0;
            var dx = touches[1].clientX - touches[0].clientX;
            var dy = touches[1].clientY - touches[0].clientY;
            return Math.sqrt(dx * dx + dy * dy);
        }

        svg.addEventListener('touchstart', function(e) {
            if (e.touches.length === 1) {
                // Single finger: pan
                touchState.tracking = true;
                touchState.startTouches = e.touches;
                var center = getTouchCenter(e.touches);
                touchState.lastCenterX = center.x;
                touchState.lastCenterY = center.y;
            } else if (e.touches.length === 2) {
                // Two fingers: pinch zoom
                touchState.tracking = true;
                touchState.lastPinchDist = getPinchDist(e.touches);
                var center = getTouchCenter(e.touches);
                touchState.lastCenterX = center.x;
                touchState.lastCenterY = center.y;
            }
            e.preventDefault();
        }, { passive: false, signal: signal });

        svg.addEventListener('touchmove', function(e) {
            if (!touchState.tracking) return;
            e.preventDefault();

            var bounds = getPlotBounds(container);
            if (!bounds) return;

            if (e.touches.length === 1) {
                // Pan
                var center = getTouchCenter(e.touches);
                var dx = center.x - touchState.lastCenterX;
                var dy = center.y - touchState.lastCenterY;

                var vb = state.viewBox || {
                    xMin: bounds.xDomain[0], xMax: bounds.xDomain[1],
                    yMin: bounds.yDomain[0], yMax: bounds.yDomain[1],
                };
                var xRange = vb.xMax - vb.xMin;
                var yRange = vb.yMax - vb.yMin;
                var dxData = -dx / bounds.plotWidth * xRange;
                var dyData = dy / bounds.plotHeight * yRange;

                state.viewBox = {
                    xMin: vb.xMin + dxData,
                    xMax: vb.xMax + dxData,
                    yMin: vb.yMin + dyData,
                    yMax: vb.yMax + dyData,
                };

                touchState.lastCenterX = center.x;
                touchState.lastCenterY = center.y;
                rerender(container, state);
            } else if (e.touches.length === 2) {
                // Pinch zoom
                var newDist = getPinchDist(e.touches);
                var center = getTouchCenter(e.touches);

                if (touchState.lastPinchDist > 0) {
                    var scale = newDist / touchState.lastPinchDist;
                    var factor = (scale - 1) * 0.5;
                    zoomBy(container, state, factor, center.x, center.y);
                }

                touchState.lastPinchDist = newDist;
                touchState.lastCenterX = center.x;
                touchState.lastCenterY = center.y;
            }
        }, { passive: false, signal: signal });

        svg.addEventListener('touchend', function(e) {
            if (e.touches.length === 0) {
                touchState.tracking = false;
            }
        }, { signal: signal });
    }

    // ====================================================================
    // Main entry point: FV.interact()
    // ====================================================================

    FV.interact = function(container, options) {
        options = options || {};

        var svg = container.querySelector('svg');
        if (!svg) return null;

        // Ensure container is positioned for absolute children
        if (getComputedStyle(container).position === 'static') {
            container.style.position = 'relative';
        }

        // Build state
        var state = {
            mode: options.mode || 'default',
            viewBox: null,
            selection: [],
            _selectedPoints: [],
            annotations: [],
            crosshair: options.crosshair || false,
            linked: false,
            linkGroup: null,
            linkField: options.linkField || null,
            _dataPoints: collectDataPoints(svg),
            _crosshairGroup: null,
            _abortController: null,
            _suppressAutoInteract: false,
        };

        instances.set(container, state);

        // Attach event listeners
        attachSVGListeners(container, state, svg);

        // Public API (defined before toolbar so toolbar callbacks can reference it)
        var toolbar = null;
        var api = {
            setMode: function(mode) {
                state.mode = mode;
                updateCursor(container, state);
            },
            enableCrosshair: function(on) {
                state.crosshair = on !== false;
                if (!state.crosshair) removeCrosshair(state);
            },
            enableLinking: function(groupName, field) {
                if (groupName) {
                    joinLinkGroup(container, state, groupName);
                    if (field) state.linkField = field;
                } else {
                    leaveLinkGroup(container, state);
                }
            },
            getSelection: function() {
                return state.selection.slice();
            },
            getSelectedPoints: function() {
                return (state._selectedPoints || []).map(function(p) {
                    return { x: p.dataX, y: p.dataY, index: p.idx, trace: p.trace };
                });
            },
            clearSelection: function() {
                state.selection = [];
                state._selectedPoints = [];
                clearSelectionHighlight(state);
            },
            addAnnotation: function(x, y, text) {
                return addAnnotation(container, state, x, y, text);
            },
            getAnnotations: function() {
                return state.annotations.slice();
            },
            removeAnnotation: function(id) {
                state.annotations = state.annotations.filter(function(a) { return a.id !== id; });
                var el = container.querySelector('[data-ann-id="' + id + '"]');
                if (el) el.remove();
            },
            clearAnnotations: function() {
                state.annotations = [];
                var svg = container.querySelector('svg');
                if (svg) {
                    svg.querySelectorAll('.fvi-annotation').forEach(function(el) { el.remove(); });
                }
            },
            resetZoom: function() {
                state.viewBox = null;
                rerender(container, state);
            },
            zoomTo: function(xMin, xMax, yMin, yMax) {
                state.viewBox = { xMin: xMin, xMax: xMax, yMin: yMin, yMax: yMax };
                rerender(container, state);
            },
            getViewBox: function() {
                return state.viewBox ? Object.assign({}, state.viewBox) : null;
            },
            destroy: function() {
                if (state._abortController) state._abortController.abort();
                if (toolbar && toolbar.parentNode) toolbar.remove();
                removeCrosshair(state);
                leaveLinkGroup(container, state);
                instances.delete(container);
            },
        };

        // Create toolbar (after api is defined so reset button can call api.resetZoom)
        toolbar = createToolbar(container, state, api);

        // Enable crosshair if requested
        if (state.crosshair) {
            var chBtns = toolbar.querySelectorAll('button');
            // The crosshair toggle is the 7th button (index 6)
            if (chBtns[6]) chBtns[6].style.background = 'rgba(74,159,110,0.3)';
        }

        // Auto-join link group if specified
        if (options.linkGroup) {
            api.enableLinking(options.linkGroup, options.linkField);
        }

        return api;
    };

    // ====================================================================
    // Auto-enhance: patch FV.render to optionally add interactions
    // ====================================================================

    var _prevRender = FV.render;

    FV.render = function(container, spec, options) {
        var result = _prevRender.call(this, container, spec, options);

        // Check for suppression flag (prevents infinite loop during rerender)
        var existingState = instances.get(container);
        if (existingState && existingState._suppressAutoInteract) {
            return result;
        }

        if (options && options.interactive) {
            // Destroy previous interact instance if present
            if (existingState) {
                if (existingState._abortController) existingState._abortController.abort();
                var oldToolbar = container.querySelector('.fvi-toolbar');
                if (oldToolbar) oldToolbar.remove();
                instances.delete(container);
            }
            FV.interact(container, typeof options.interactive === 'object' ? options.interactive : {});
        }

        return result;
    };

    // ====================================================================
    // Static linked brushing helpers (for dashboard use without interact())
    // ====================================================================

    FV.linkInteract = function(groupName, containers, options) {
        options = options || {};
        containers.forEach(function(c) {
            var api = FV.interact(c, {
                linkGroup: groupName,
                linkField: options.field,
                crosshair: options.crosshair || false,
            });
        });
    };

})(ForgeViz);
