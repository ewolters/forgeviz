/**
 * ForgeViz Dashboard Engine
 *
 * Renders a DashboardSpec JSON into a fully interactive dashboard with
 * CSS Grid layout, cross-filtering, global filter controls, fullscreen
 * toggle, panel export, and optional drag reorder.
 *
 * Depends on forgeviz.js being loaded first (ForgeViz.render).
 *
 * Usage:
 *   const api = ForgeViz.dashboard(container, dashboardSpecJSON, options);
 *   api.setFilter('shift', 'A');
 *   api.clearFilters();
 *   api.destroy();
 */
(function (FV) {
    'use strict';

    /* ================================================================
     * Theme tokens (match core/colors.py svend_dark)
     * ================================================================ */
    const THEME = {
        bg: '#0d120d',
        cardBg: '#121a12',
        border: 'rgba(255,255,255,0.08)',
        borderAccent: 'rgba(74,159,110,0.3)',
        accent: '#4a9f6e',
        text: '#e8efe8',
        textSecondary: '#9aaa9a',
        textDim: '#7a8f7a',
        font: "Inter, system-ui, sans-serif",
    };

    /* ================================================================
     * Utility helpers
     * ================================================================ */

    function el(tag, attrs, children) {
        const e = document.createElement(tag);
        if (attrs) {
            Object.keys(attrs).forEach(function (k) {
                if (k === 'style' && typeof attrs[k] === 'object') {
                    Object.assign(e.style, attrs[k]);
                } else if (k === 'className') {
                    e.className = attrs[k];
                } else if (k.startsWith('on')) {
                    e.addEventListener(k.slice(2).toLowerCase(), attrs[k]);
                } else {
                    e.setAttribute(k, attrs[k]);
                }
            });
        }
        if (children) {
            (Array.isArray(children) ? children : [children]).forEach(function (c) {
                if (typeof c === 'string') e.appendChild(document.createTextNode(c));
                else if (c) e.appendChild(c);
            });
        }
        return e;
    }

    function css(styles) {
        return Object.keys(styles).map(function (k) {
            return k.replace(/([A-Z])/g, '-$1').toLowerCase() + ':' + styles[k];
        }).join(';');
    }

    function svgIcon(path, size) {
        size = size || 16;
        var ns = 'http://www.w3.org/2000/svg';
        var svg = document.createElementNS(ns, 'svg');
        svg.setAttribute('width', size);
        svg.setAttribute('height', size);
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', THEME.textDim);
        svg.setAttribute('stroke-width', '2');
        svg.setAttribute('stroke-linecap', 'round');
        svg.setAttribute('stroke-linejoin', 'round');
        var p = document.createElementNS(ns, 'path');
        p.setAttribute('d', path);
        svg.appendChild(p);
        return svg;
    }

    // Icons (Feather-style SVG paths)
    var ICONS = {
        maximize: 'M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3',
        minimize: 'M4 14h6v6m10-10h-6V4m0 6l7-7M3 21l7-7',
        download: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4m4-5l5 5 5-5m-5 5V3',
        x: 'M18 6L6 18M6 6l12 12',
        filter: 'M22 3H2l8 9.46V19l4 2v-8.54L22 3',
    };

    /* ================================================================
     * Global Filter Bar
     * ================================================================ */

    function buildFilterBar(filters, filterState, onChange) {
        var bar = el('div', {
            style: {
                display: 'flex',
                flexWrap: 'wrap',
                gap: '12px',
                padding: '12px 16px',
                background: THEME.cardBg,
                borderBottom: '1px solid ' + THEME.border,
                alignItems: 'center',
                fontFamily: THEME.font,
            },
        });

        // Filter icon label
        bar.appendChild(el('span', {
            style: {
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                color: THEME.textDim,
                fontSize: '12px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
            },
        }, [svgIcon(ICONS.filter, 14), 'Filters']));

        filters.forEach(function (f) {
            var wrapper = el('div', {
                style: {
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px',
                },
            });

            var label = el('label', {
                style: {
                    fontSize: '11px',
                    color: THEME.textDim,
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                },
            }, f.label || f.field);
            wrapper.appendChild(label);

            if (f.type === 'select') {
                var select = el('select', {
                    style: {
                        background: THEME.bg,
                        color: THEME.text,
                        border: '1px solid ' + THEME.border,
                        borderRadius: '4px',
                        padding: '4px 8px',
                        fontSize: '13px',
                        fontFamily: THEME.font,
                        cursor: 'pointer',
                        minWidth: '120px',
                    },
                    onChange: function () {
                        if (this.value === '') {
                            delete filterState[f.field];
                        } else {
                            filterState[f.field] = this.value;
                        }
                        onChange();
                    },
                });
                select.appendChild(el('option', { value: '' }, 'All'));
                (f.options || []).forEach(function (opt) {
                    select.appendChild(el('option', { value: String(opt) }, String(opt)));
                });
                wrapper.appendChild(select);
            } else if (f.type === 'range') {
                var rangeWrapper = el('div', { style: { display: 'flex', gap: '4px', alignItems: 'center' } });
                var minInput = el('input', {
                    type: 'number',
                    placeholder: 'min',
                    style: {
                        width: '70px',
                        background: THEME.bg,
                        color: THEME.text,
                        border: '1px solid ' + THEME.border,
                        borderRadius: '4px',
                        padding: '4px 6px',
                        fontSize: '13px',
                        fontFamily: THEME.font,
                    },
                    onChange: function () {
                        filterState[f.field + '_min'] = this.value ? Number(this.value) : undefined;
                        if (filterState[f.field + '_min'] === undefined) delete filterState[f.field + '_min'];
                        onChange();
                    },
                });
                var maxInput = el('input', {
                    type: 'number',
                    placeholder: 'max',
                    style: {
                        width: '70px',
                        background: THEME.bg,
                        color: THEME.text,
                        border: '1px solid ' + THEME.border,
                        borderRadius: '4px',
                        padding: '4px 6px',
                        fontSize: '13px',
                        fontFamily: THEME.font,
                    },
                    onChange: function () {
                        filterState[f.field + '_max'] = this.value ? Number(this.value) : undefined;
                        if (filterState[f.field + '_max'] === undefined) delete filterState[f.field + '_max'];
                        onChange();
                    },
                });
                rangeWrapper.appendChild(minInput);
                rangeWrapper.appendChild(el('span', { style: { color: THEME.textDim, fontSize: '12px' } }, '\u2013'));
                rangeWrapper.appendChild(maxInput);
                wrapper.appendChild(rangeWrapper);
            } else if (f.type === 'date_range') {
                var dateWrapper = el('div', { style: { display: 'flex', gap: '4px', alignItems: 'center' } });
                var startInput = el('input', {
                    type: 'date',
                    style: {
                        background: THEME.bg,
                        color: THEME.text,
                        border: '1px solid ' + THEME.border,
                        borderRadius: '4px',
                        padding: '4px 6px',
                        fontSize: '13px',
                        fontFamily: THEME.font,
                    },
                    onChange: function () {
                        filterState[f.field + '_start'] = this.value || undefined;
                        if (!filterState[f.field + '_start']) delete filterState[f.field + '_start'];
                        onChange();
                    },
                });
                var endInput = el('input', {
                    type: 'date',
                    style: {
                        background: THEME.bg,
                        color: THEME.text,
                        border: '1px solid ' + THEME.border,
                        borderRadius: '4px',
                        padding: '4px 6px',
                        fontSize: '13px',
                        fontFamily: THEME.font,
                    },
                    onChange: function () {
                        filterState[f.field + '_end'] = this.value || undefined;
                        if (!filterState[f.field + '_end']) delete filterState[f.field + '_end'];
                        onChange();
                    },
                });
                dateWrapper.appendChild(startInput);
                dateWrapper.appendChild(el('span', { style: { color: THEME.textDim, fontSize: '12px' } }, '\u2013'));
                dateWrapper.appendChild(endInput);
                wrapper.appendChild(dateWrapper);
            }

            bar.appendChild(wrapper);
        });

        // Clear all button
        var clearBtn = el('button', {
            style: {
                marginLeft: 'auto',
                background: 'transparent',
                color: THEME.textDim,
                border: '1px solid ' + THEME.border,
                borderRadius: '4px',
                padding: '4px 10px',
                fontSize: '12px',
                cursor: 'pointer',
                fontFamily: THEME.font,
            },
            onClick: function () {
                Object.keys(filterState).forEach(function (k) { delete filterState[k]; });
                // Reset all inputs
                bar.querySelectorAll('select').forEach(function (s) { s.value = ''; });
                bar.querySelectorAll('input').forEach(function (i) { i.value = ''; });
                onChange();
            },
        }, 'Clear All');
        bar.appendChild(clearBtn);

        return bar;
    }

    /* ================================================================
     * Panel Chrome
     * ================================================================ */

    function buildPanel(panelSpec, filterState, opts) {
        var gridRow = (panelSpec.row + 1) + ' / span ' + panelSpec.row_span;
        var gridCol = (panelSpec.col + 1) + ' / span ' + panelSpec.col_span;

        var panel = el('div', {
            'data-panel-id': panelSpec.id,
            style: {
                gridRow: gridRow,
                gridColumn: gridCol,
                background: THEME.cardBg,
                border: '1px solid ' + THEME.border,
                borderRadius: '6px',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                position: 'relative',
                transition: 'border-color 0.2s ease',
            },
        });

        // Hover border effect
        panel.addEventListener('mouseenter', function () {
            panel.style.borderColor = THEME.borderAccent;
        });
        panel.addEventListener('mouseleave', function () {
            if (!panel._fullscreen) panel.style.borderColor = THEME.border;
        });

        // Header bar
        var header = el('div', {
            style: {
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                borderBottom: '1px solid ' + THEME.border,
                minHeight: '36px',
            },
        });

        var title = el('span', {
            style: {
                fontSize: '13px',
                fontWeight: '500',
                color: THEME.text,
                fontFamily: THEME.font,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
            },
        }, (panelSpec.spec && panelSpec.spec.title) || panelSpec.id);
        header.appendChild(title);

        // Toolbar (visible on hover)
        var toolbar = el('div', {
            style: {
                display: 'flex',
                gap: '4px',
                opacity: '0',
                transition: 'opacity 0.15s ease',
            },
        });
        panel.addEventListener('mouseenter', function () { toolbar.style.opacity = '1'; });
        panel.addEventListener('mouseleave', function () { toolbar.style.opacity = '0'; });

        function toolBtn(iconPath, titleText, onClick) {
            var btn = el('button', {
                title: titleText,
                style: {
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    padding: '2px',
                    borderRadius: '3px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                },
                onClick: onClick,
            }, [svgIcon(iconPath, 14)]);
            btn.addEventListener('mouseenter', function () {
                btn.style.background = THEME.bg;
            });
            btn.addEventListener('mouseleave', function () {
                btn.style.background = 'transparent';
            });
            return btn;
        }

        // Fullscreen toggle
        toolbar.appendChild(toolBtn(ICONS.maximize, 'Fullscreen', function (e) {
            e.stopPropagation();
            toggleFullscreen(panel, opts);
        }));

        // Export SVG
        toolbar.appendChild(toolBtn(ICONS.download, 'Export SVG', function (e) {
            e.stopPropagation();
            exportPanelSVG(panel, panelSpec);
        }));

        // Reset filter for this panel
        if (panelSpec.filter_field) {
            toolbar.appendChild(toolBtn(ICONS.x, 'Clear filter', function (e) {
                e.stopPropagation();
                delete filterState[panelSpec.filter_field];
                if (opts.onFilterChange) opts.onFilterChange();
            }));
        }

        header.appendChild(toolbar);
        panel.appendChild(header);

        // Chart body
        var body = el('div', {
            style: {
                flex: '1',
                padding: '4px',
                position: 'relative',
                overflow: 'hidden',
            },
        });
        panel.appendChild(body);
        panel._body = body;
        panel._spec = panelSpec;

        // Render chart
        renderChart(body, panelSpec.spec);

        // Double-click fullscreen
        body.addEventListener('dblclick', function () {
            toggleFullscreen(panel, opts);
        });

        // Click cross-filter
        if (panelSpec.filter_field) {
            body.style.cursor = 'crosshair';
            body.addEventListener('click', function (e) {
                // Try to extract the data value from click position
                var rect = body.getBoundingClientRect();
                var spec = panelSpec.spec;
                if (!spec || !spec.traces || !spec.traces.length) return;
                var trace = spec.traces[0];
                if (!trace.x || !trace.x.length) return;

                // Approximate which data point was clicked
                var xRatio = (e.clientX - rect.left) / rect.width;
                var idx = Math.round(xRatio * (trace.x.length - 1));
                idx = Math.max(0, Math.min(trace.x.length - 1, idx));
                var value = trace.x[idx];

                filterState[panelSpec.filter_field] = value;
                if (opts.onFilterChange) opts.onFilterChange();
            });
        }

        return panel;
    }

    /* ================================================================
     * Chart Rendering
     * ================================================================ */

    function renderChart(container, chartSpec) {
        container.innerHTML = '';
        if (!chartSpec) return;
        try {
            if (FV.render) {
                FV.render(container, chartSpec);
            } else {
                // Fallback: show spec title
                container.appendChild(el('div', {
                    style: {
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                        color: THEME.textDim,
                        fontSize: '13px',
                        fontFamily: THEME.font,
                    },
                }, chartSpec.title || 'No renderer available'));
            }
        } catch (err) {
            container.appendChild(el('div', {
                style: {
                    color: '#d06060',
                    padding: '12px',
                    fontSize: '12px',
                    fontFamily: THEME.font,
                },
            }, 'Render error: ' + err.message));
        }
    }

    /* ================================================================
     * Fullscreen
     * ================================================================ */

    function toggleFullscreen(panel, opts) {
        if (panel._fullscreen) {
            // Restore
            panel.style.position = '';
            panel.style.top = '';
            panel.style.left = '';
            panel.style.width = '';
            panel.style.height = '';
            panel.style.zIndex = '';
            panel.style.gridRow = (panel._spec.row + 1) + ' / span ' + panel._spec.row_span;
            panel.style.gridColumn = (panel._spec.col + 1) + ' / span ' + panel._spec.col_span;
            panel.style.borderColor = THEME.border;
            panel._fullscreen = false;

            // Remove overlay
            if (panel._overlay && panel._overlay.parentNode) {
                panel._overlay.parentNode.removeChild(panel._overlay);
            }

            renderChart(panel._body, panel._spec.spec);
        } else {
            // Expand to fill dashboard container
            var container = opts.container;
            var rect = container.getBoundingClientRect();

            // Add overlay
            var overlay = el('div', {
                style: {
                    position: 'fixed',
                    top: '0',
                    left: '0',
                    width: '100vw',
                    height: '100vh',
                    background: 'rgba(0,0,0,0.6)',
                    zIndex: '9998',
                },
                onClick: function () {
                    toggleFullscreen(panel, opts);
                },
            });
            document.body.appendChild(overlay);
            panel._overlay = overlay;

            panel.style.position = 'fixed';
            panel.style.top = '40px';
            panel.style.left = '40px';
            panel.style.width = 'calc(100vw - 80px)';
            panel.style.height = 'calc(100vh - 80px)';
            panel.style.zIndex = '9999';
            panel.style.gridRow = '';
            panel.style.gridColumn = '';
            panel.style.borderColor = THEME.accent;
            panel._fullscreen = true;

            // Re-render at full size
            var fsSpec = Object.assign({}, panel._spec.spec, {
                width: window.innerWidth - 120,
                height: window.innerHeight - 160,
            });
            renderChart(panel._body, fsSpec);
        }
    }

    /* ================================================================
     * Export
     * ================================================================ */

    function exportPanelSVG(panel, panelSpec) {
        var svg = panel._body.querySelector('svg');
        if (!svg) return;

        var serializer = new XMLSerializer();
        var source = serializer.serializeToString(svg);
        var blob = new Blob([source], { type: 'image/svg+xml;charset=utf-8' });
        var url = URL.createObjectURL(blob);

        var a = document.createElement('a');
        a.href = url;
        a.download = (panelSpec.id || 'chart') + '.svg';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    /* ================================================================
     * Cross-filter logic
     * ================================================================ */

    function shouldRerender(panelSpec, filterState) {
        // A panel should re-render if any of its listen_fields are in the filter state
        if (!panelSpec.listen_fields || !panelSpec.listen_fields.length) return false;
        for (var i = 0; i < panelSpec.listen_fields.length; i++) {
            if (filterState.hasOwnProperty(panelSpec.listen_fields[i])) {
                return true;
            }
        }
        return false;
    }

    function applyFilters(spec, filterState, listenFields) {
        // Create a filtered copy of the spec
        // For now: filter trace data by matching x values
        if (!spec || !spec.traces || !spec.traces.length) return spec;
        if (!listenFields || !listenFields.length) return spec;

        var filtered = JSON.parse(JSON.stringify(spec));

        listenFields.forEach(function (field) {
            if (!filterState.hasOwnProperty(field)) return;
            var filterValue = filterState[field];

            filtered.traces = filtered.traces.map(function (trace) {
                if (!trace.x || !trace.y) return trace;
                var newX = [], newY = [];
                for (var i = 0; i < trace.x.length; i++) {
                    if (String(trace.x[i]) === String(filterValue)) {
                        newX.push(trace.x[i]);
                        newY.push(trace.y[i]);
                    }
                }
                return Object.assign({}, trace, { x: newX, y: newY });
            });
        });

        return filtered;
    }

    /* ================================================================
     * Drag Reorder (optional)
     * ================================================================ */

    function enableDragReorder(grid, panelEls, panelSpecs) {
        var dragSrc = null;

        panelEls.forEach(function (panel, idx) {
            // Add drag handle
            var handle = el('div', {
                draggable: 'true',
                title: 'Drag to reorder',
                style: {
                    position: 'absolute',
                    top: '8px',
                    left: '4px',
                    width: '8px',
                    height: '20px',
                    cursor: 'grab',
                    opacity: '0',
                    transition: 'opacity 0.15s',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '2px',
                    justifyContent: 'center',
                    alignItems: 'center',
                },
            });
            // Dots pattern for drag handle
            for (var i = 0; i < 3; i++) {
                var dot = el('div', {
                    style: {
                        width: '3px',
                        height: '3px',
                        borderRadius: '50%',
                        background: THEME.textDim,
                    },
                });
                handle.appendChild(dot);
            }
            panel.appendChild(handle);
            panel.addEventListener('mouseenter', function () { handle.style.opacity = '1'; });
            panel.addEventListener('mouseleave', function () { handle.style.opacity = '0'; });

            handle.addEventListener('dragstart', function (e) {
                dragSrc = idx;
                panel.style.opacity = '0.5';
                e.dataTransfer.effectAllowed = 'move';
            });

            panel.addEventListener('dragover', function (e) {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                panel.style.borderColor = THEME.accent;
            });

            panel.addEventListener('dragleave', function () {
                panel.style.borderColor = THEME.border;
            });

            panel.addEventListener('drop', function (e) {
                e.preventDefault();
                panel.style.borderColor = THEME.border;
                if (dragSrc === null || dragSrc === idx) return;

                // Swap grid positions
                var srcSpec = panelSpecs[dragSrc];
                var dstSpec = panelSpecs[idx];
                var tmpRow = srcSpec.row, tmpCol = srcSpec.col;
                srcSpec.row = dstSpec.row;
                srcSpec.col = dstSpec.col;
                dstSpec.row = tmpRow;
                dstSpec.col = tmpCol;

                // Update grid placement
                panelEls[dragSrc].style.gridRow = (srcSpec.row + 1) + ' / span ' + srcSpec.row_span;
                panelEls[dragSrc].style.gridColumn = (srcSpec.col + 1) + ' / span ' + srcSpec.col_span;
                panelEls[idx].style.gridRow = (dstSpec.row + 1) + ' / span ' + dstSpec.row_span;
                panelEls[idx].style.gridColumn = (dstSpec.col + 1) + ' / span ' + dstSpec.col_span;
            });

            handle.addEventListener('dragend', function () {
                panel.style.opacity = '1';
                dragSrc = null;
            });
        });
    }

    /* ================================================================
     * Responsive breakpoint
     * ================================================================ */

    function applyResponsive(grid, spec) {
        function check() {
            if (window.innerWidth < 768) {
                grid.style.gridTemplateColumns = '1fr';
            } else {
                grid.style.gridTemplateColumns = 'repeat(' + spec.columns + ', 1fr)';
            }
        }
        check();
        window.addEventListener('resize', check);
        return function cleanup() {
            window.removeEventListener('resize', check);
        };
    }

    /* ================================================================
     * Main Entry Point
     * ================================================================ */

    FV.dashboard = function (container, spec, options) {
        options = options || {};
        var filterState = {};
        var panels = [];
        var panelEls = [];
        var cleanups = [];

        // Ensure container is styled
        if (typeof container === 'string') {
            container = document.querySelector(container);
        }
        if (!container) throw new Error('ForgeViz.dashboard: container not found');
        container.innerHTML = '';
        container.style.fontFamily = THEME.font;

        // Dashboard wrapper
        var wrapper = el('div', {
            style: {
                background: THEME.bg,
                borderRadius: '8px',
                overflow: 'hidden',
                border: '1px solid ' + THEME.border,
            },
        });

        // Title bar
        if (spec.title) {
            var titleBar = el('div', {
                style: {
                    padding: '16px 20px 12px',
                    borderBottom: '1px solid ' + THEME.border,
                },
            });
            titleBar.appendChild(el('h2', {
                style: {
                    margin: '0',
                    fontSize: '18px',
                    fontWeight: '600',
                    color: THEME.text,
                    fontFamily: THEME.font,
                },
            }, spec.title));
            wrapper.appendChild(titleBar);
        }

        // Global filters bar
        if (spec.filters && spec.filters.length) {
            var filterBar = buildFilterBar(spec.filters, filterState, rerenderAll);
            wrapper.appendChild(filterBar);
        }

        // Grid
        var rowHeight = spec.row_height || 350;
        var grid = el('div', {
            style: {
                display: 'grid',
                gridTemplateColumns: 'repeat(' + (spec.columns || 2) + ', 1fr)',
                gridAutoRows: rowHeight + 'px',
                gap: '12px',
                padding: '12px',
            },
        });

        // Build panels
        var panelSpecs = spec.panels || [];
        panelSpecs.forEach(function (panelDef) {
            var panelEl = buildPanel(panelDef, filterState, {
                container: wrapper,
                onFilterChange: rerenderAll,
            });
            grid.appendChild(panelEl);
            panelEls.push(panelEl);
            panels.push({ el: panelEl, spec: panelDef });
        });

        wrapper.appendChild(grid);
        container.appendChild(wrapper);

        // Responsive
        cleanups.push(applyResponsive(grid, spec));

        // Drag reorder
        if (options.draggable !== false) {
            enableDragReorder(grid, panelEls, panelSpecs);
        }

        // ----------------------------------------------------------
        // Re-render logic
        // ----------------------------------------------------------

        function rerenderAll() {
            panels.forEach(function (p) {
                var panelDef = p.spec;
                if (panelDef.listen_fields && panelDef.listen_fields.length) {
                    // Check if any active filter matches
                    var hasActiveFilter = panelDef.listen_fields.some(function (f) {
                        return filterState.hasOwnProperty(f);
                    });
                    if (hasActiveFilter) {
                        var filteredSpec = applyFilters(panelDef.spec, filterState, panelDef.listen_fields);
                        renderChart(p.el._body, filteredSpec);
                    } else {
                        // No filter active — render original
                        renderChart(p.el._body, panelDef.spec);
                    }
                }
            });

            // Highlight active filter sources
            panels.forEach(function (p) {
                if (p.spec.filter_field && filterState.hasOwnProperty(p.spec.filter_field)) {
                    p.el.style.borderColor = THEME.accent;
                } else {
                    p.el.style.borderColor = THEME.border;
                }
            });
        }

        // ----------------------------------------------------------
        // Public API
        // ----------------------------------------------------------

        return {
            /** Set a cross-filter value. */
            setFilter: function (field, value) {
                filterState[field] = value;
                rerenderAll();
            },

            /** Remove a single filter. */
            removeFilter: function (field) {
                delete filterState[field];
                rerenderAll();
            },

            /** Clear all filters. */
            clearFilters: function () {
                Object.keys(filterState).forEach(function (k) { delete filterState[k]; });
                rerenderAll();
            },

            /** Get current filter state (copy). */
            getFilterState: function () {
                return JSON.parse(JSON.stringify(filterState));
            },

            /** Export all panels as SVG blobs. */
            exportAll: function (format) {
                format = format || 'svg';
                panels.forEach(function (p) {
                    exportPanelSVG(p.el, p.spec);
                });
            },

            /** Get a panel element by ID. */
            getPanel: function (panelId) {
                for (var i = 0; i < panels.length; i++) {
                    if (panels[i].spec.id === panelId) return panels[i];
                }
                return null;
            },

            /** Re-render a specific panel with a new ChartSpec. */
            updatePanel: function (panelId, newSpec) {
                var panel = this.getPanel(panelId);
                if (!panel) return;
                panel.spec.spec = newSpec;
                renderChart(panel.el._body, newSpec);
            },

            /** Tear down the dashboard. */
            destroy: function () {
                cleanups.forEach(function (fn) { fn(); });
                container.innerHTML = '';
            },
        };
    };

})(window.ForgeViz || (window.ForgeViz = {}));
