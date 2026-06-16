/**
 * Topology Editor - Multi-Zone Spatial Configuration
 */

// ============================================================================
// SCENE STATE
// ============================================================================

let availableDevices = [];   // device meta for the legend panel

// ============================================================================
// CANVAS TOPOLOGY RENDERER
// ============================================================================

class TopologyCanvas {
    constructor(canvasElement) {
        this.canvas = canvasElement;
        this.ctx = canvasElement.getContext('2d');
        this.zones = []; // Populated dynamically after device selection

        // Global effect center (topology-level, not per-zone)
        this.effectCenter = { x: 50, y: 50 }; // Percentuale 0-100

        // Rendering config
        this.ledSize = 20; // Pixel size per LED unit
        this.gridSize = 1; // LED units
        this.snapEnabled = true;
        this.showGrid = true;
        this.padding = 50; // Canvas padding

        // Interaction state
        this.selectedZone = null;
        this.hoveredZone = null;
        this.dragState = null;
        this.dragCenterState = null; // Stato per dragging del crosshair
        this.mousePos = { x: 0, y: 0 };

        // Camera for pan/zoom
        this.camera = { x: 0, y: 0, zoom: 1 };
        this.panState = null;

        // Calibration overlay
        this.showCalibration = false;
        this.calibrationSpacing = 10;

        this.setupEventListeners();
        this.render();
    }

    // ------------------------------------------------------------------------
    // Event Handlers
    // ------------------------------------------------------------------------

    setupEventListeners() {
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('mouseleave', (e) => this.onMouseLeave(e));
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e), { passive: false });
        this.canvas.addEventListener('contextmenu', (e) => e.preventDefault());
        document.addEventListener('keydown', (e) => this.onKeyDown(e));
    }

    onMouseDown(e) {
        // Middle mouse: pan
        if (e.button === 1) {
            const pos = this.getMousePos(e);
            this.panState = { startPos: pos, startCamX: this.camera.x, startCamY: this.camera.y };
            this.canvas.style.cursor = 'grabbing';
            e.preventDefault();
            return;
        }

        const screenPos = this.getMousePos(e);
        const worldPos = this.screenToWorld(screenPos);

        // Priority 1: Check if clicking on effect center crosshair
        if (this.isPointOnEffectCenter(screenPos)) {
            this.dragCenterState = {
                startCenter: { ...this.effectCenter }
            };
            this.render();
            return;
        }

        // Priority 2: Check if clicking on a zone
        const clickedZone = this.findZoneAt(worldPos);

        if (clickedZone) {
            this.selectZone(clickedZone);
            this.dragState = {
                zone: clickedZone,
                startPos: { ...clickedZone.position },
                offset: {
                    x: worldPos.x - clickedZone.position.x,
                    y: worldPos.y - clickedZone.position.y
                }
            };
        } else {
            this.selectZone(null);
        }

        this.render();
    }

    onMouseMove(e) {
        // Pan with middle mouse
        if (this.panState) {
            const pos = this.getMousePos(e);
            this.camera.x = this.panState.startCamX + (pos.x - this.panState.startPos.x);
            this.camera.y = this.panState.startCamY + (pos.y - this.panState.startPos.y);
            this.render();
            return;
        }

        const screenPos = this.getMousePos(e);
        const worldPos = this.screenToWorld(screenPos);
        this.mousePos = worldPos;

        // Update mouse position display
        document.getElementById('mouse-pos').textContent =
            `X: ${worldPos.x.toFixed(1)}, Y: ${worldPos.y.toFixed(1)}`;

        // Priority 1: Dragging effect center
        if (this.dragCenterState) {
            const bbox = this.calculateBoundingBox();
            if (bbox) {
                // Snap world position to grid (same as zones)
                let snappedX = worldPos.x;
                let snappedY = worldPos.y;

                if (this.snapEnabled) {
                    snappedX = Math.round(worldPos.x / this.gridSize) * this.gridSize;
                    snappedY = Math.round(worldPos.y / this.gridSize) * this.gridSize;
                }

                // Convert snapped world coords to percentage within bbox
                const width = bbox.max_x - bbox.min_x;
                const height = bbox.max_y - bbox.min_y;

                let newCenterX = ((snappedX - bbox.min_x) / width) * 100;
                let newCenterY = ((snappedY - bbox.min_y) / height) * 100;

                // Clamp to 0-100%
                newCenterX = Math.max(0, Math.min(100, newCenterX));
                newCenterY = Math.max(0, Math.min(100, newCenterY));

                this.effectCenter.x = newCenterX;
                this.effectCenter.y = newCenterY;

                this.updateEffectCenterInputs();
                this.render();
                if (this.showCalibration) triggerHardwareCalibration();
            }
            return;
        }

        // Priority 2: Dragging zone
        if (this.dragState) {
            let newX = worldPos.x - this.dragState.offset.x;
            let newY = worldPos.y - this.dragState.offset.y;

            // Snap to grid
            if (this.snapEnabled) {
                newX = Math.round(newX / this.gridSize) * this.gridSize;
                newY = Math.round(newY / this.gridSize) * this.gridSize;
            }

            this.dragState.zone.position.x = newX;
            this.dragState.zone.position.y = newY;

            this.updateInspector();
            this.checkOverlaps();
            this.updateBoundingBox();  // Update in real-time during drag
            this.render();
        } else {
            // Hover detection (cursor style)
            if (this.isPointOnEffectCenter(screenPos)) {
                this.canvas.style.cursor = 'grab';
            } else {
                const hoveredZone = this.findZoneAt(worldPos);
                if (hoveredZone !== this.hoveredZone) {
                    this.hoveredZone = hoveredZone;
                    this.canvas.style.cursor = hoveredZone ? 'move' : 'crosshair';
                    this.render();
                }
            }
        }
    }

    onMouseUp(e) {
        if (e.button === 1 && this.panState) {
            this.panState = null;
            this.canvas.style.cursor = 'crosshair';
            return;
        }
        if (this.dragCenterState) {
            this.dragCenterState = null;
            this.canvas.style.cursor = 'crosshair';
            this.updateBoundingBox();
            this.render();
        }
        if (this.dragState) {
            this.dragState = null;
            this.updateBoundingBox();
        }
    }

    onMouseLeave(e) {
        this.panState = null;
        this.dragCenterState = null;
        this.dragState = null;
        this.hoveredZone = null;
        this.canvas.style.cursor = 'crosshair';
        this.render();
    }

    onWheel(e) {
        e.preventDefault();
        const mousePos = this.getMousePos(e);
        const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
        const newZoom = Math.max(0.1, Math.min(8, this.camera.zoom * zoomFactor));

        // Keep world point under mouse fixed: camera.x_new = mousePos.x - baseX * newZoom
        const baseX = (mousePos.x - this.camera.x) / this.camera.zoom;
        const baseY = (mousePos.y - this.camera.y) / this.camera.zoom;
        this.camera.x = mousePos.x - baseX * newZoom;
        this.camera.y = mousePos.y - baseY * newZoom;
        this.camera.zoom = newZoom;

        this.updateZoomDisplay();
        this.render();
    }

    resetCamera() {
        const bbox = this.calculateBoundingBox();

        if (!bbox || this.zones.length === 0) {
            this.camera = { x: 0, y: 0, zoom: 1 };
            this.updateZoomDisplay();
            this.render();
            return;
        }

        // Bbox center and size in base pixels (zoom=1, cam=0)
        const fitPad = 80;
        const cx_base = this.padding + ((bbox.min_x + bbox.max_x) / 2) * this.ledSize;
        const cy_base = this.canvas.height - this.padding - ((bbox.min_y + bbox.max_y) / 2) * this.ledSize;
        const bboxW_px = (bbox.max_x - bbox.min_x) * this.ledSize;
        const bboxH_px = (bbox.max_y - bbox.min_y) * this.ledSize;

        // Scale to fit bbox in available canvas area (at least 1 LED wide to avoid div/0)
        const availW = this.canvas.width - fitPad * 2;
        const availH = this.canvas.height - fitPad * 2;
        const zoom = Math.max(0.1, Math.min(8,
            Math.min(availW / Math.max(bboxW_px, this.ledSize),
                     availH / Math.max(bboxH_px, this.ledSize))
        ));

        // Center bbox in canvas
        this.camera = {
            x: this.canvas.width / 2 - cx_base * zoom,
            y: this.canvas.height / 2 - cy_base * zoom,
            zoom
        };

        this.updateZoomDisplay();
        this.render();
    }

    updateZoomDisplay() {
        const el = document.getElementById('zoom-level');
        if (el) el.textContent = `${Math.round(this.camera.zoom * 100)}%`;
    }

    onKeyDown(e) {
        if (!this.selectedZone) return;

        // R / Shift+R: Rotate (90° snapping)
        if (e.key === 'r' || e.key === 'R') {
            const increment = e.shiftKey ? -90 : 90;
            this.selectedZone.rotation = (this.selectedZone.rotation + increment + 360) % 360;
            this.checkOverlaps();
            this.updateBoundingBox();
            this.updateInspector();
            this.render();
        }

        // F: Flip direction
        if (e.key === 'f' || e.key === 'F') {
            this.selectedZone.direction = this.selectedZone.direction === 'forward' ? 'reverse' : 'forward';
            this.updateInspector();
            this.render();
        }

        // Arrow keys: Nudge
        const nudgeAmount = e.shiftKey ? 0.1 : 1;
        switch(e.key) {
            case 'ArrowLeft':
                this.selectedZone.position.x -= nudgeAmount;
                this.updateInspector();
                this.render();
                e.preventDefault();
                break;
            case 'ArrowRight':
                this.selectedZone.position.x += nudgeAmount;
                this.updateInspector();
                this.render();
                e.preventDefault();
                break;
            case 'ArrowUp':
                this.selectedZone.position.y += nudgeAmount;
                this.updateInspector();
                this.render();
                e.preventDefault();
                break;
            case 'ArrowDown':
                this.selectedZone.position.y -= nudgeAmount;
                this.updateInspector();
                this.render();
                e.preventDefault();
                break;
        }
    }

    // ------------------------------------------------------------------------
    // Rendering
    // ------------------------------------------------------------------------

    render() {
        this.clear();

        if (this.showGrid) {
            this.drawGrid();
        }

        // Draw zones (unselected first, selected last for z-order)
        const unselected = this.zones.filter(z => z !== this.selectedZone);
        const selected = this.zones.filter(z => z === this.selectedZone);

        unselected.forEach(zone => this.drawZone(zone, false, zone === this.hoveredZone));
        selected.forEach(zone => this.drawZone(zone, true, false));

        // Calibration overlay (above zones, below bboxes and crosshair)
        this.drawCalibrationOverlay();

        // Draw Virtual BBox first (background layer)
        this.drawVirtualBBox();

        // Draw standard BBox (foreground layer)
        this.drawBoundingBox();

        // Draw effect center (always visible on global bbox)
        this.drawEffectCenter();
    }

    clear() {
        this.ctx.fillStyle = '#0a0a0c';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }

    drawGrid() {
        const gridSpacing = this.gridSize * this.ledSize;
        const width = this.canvas.width;
        const height = this.canvas.height;

        // Compute visible range in base coords (before camera)
        const baseX0 = (0 - this.camera.x) / this.camera.zoom;
        const baseX1 = (width - this.camera.x) / this.camera.zoom;
        const baseY0 = (0 - this.camera.y) / this.camera.zoom;
        const baseY1 = (height - this.camera.y) / this.camera.zoom;

        const startX = Math.floor(baseX0 / gridSpacing) * gridSpacing;
        const startY = Math.floor(baseY0 / gridSpacing) * gridSpacing;

        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.05)';
        this.ctx.lineWidth = 1;

        for (let bx = startX; bx <= baseX1; bx += gridSpacing) {
            const sx = bx * this.camera.zoom + this.camera.x;
            this.ctx.beginPath();
            this.ctx.moveTo(sx, 0);
            this.ctx.lineTo(sx, height);
            this.ctx.stroke();
        }

        for (let by = startY; by <= baseY1; by += gridSpacing) {
            const sy = by * this.camera.zoom + this.camera.y;
            this.ctx.beginPath();
            this.ctx.moveTo(0, sy);
            this.ctx.lineTo(width, sy);
            this.ctx.stroke();
        }
    }

    _calibrationColor(zone, ledIndex) {
        // Returns CSS color string for a LED based on its distance from the effect center.
        const RING_COLORS = ['#FFFFFF', '#FF3C3C', '#507FFF', '#3CD250'];
        const bbox = this.calculateBoundingBox();
        if (!bbox) return zone.color;

        const cx_w = bbox.min_x + (bbox.max_x - bbox.min_x) * (this.effectCenter.x / 100);
        const cy_w = bbox.min_y + (bbox.max_y - bbox.min_y) * (this.effectCenter.y / 100);

        // LED center in zone local space
        const ledSpacing = zone.led_spacing ?? 1.0;
        const lx_local = (ledIndex + 0.5) * ledSpacing;
        const ly_local = 0.5;

        // Rotate to world space
        const rad = zone.rotation * Math.PI / 180;
        const wx = zone.position.x + lx_local * Math.cos(rad) - ly_local * Math.sin(rad);
        const wy = zone.position.y + lx_local * Math.sin(rad) + ly_local * Math.cos(rad);

        const dist = Math.hypot(wx - cx_w, wy - cy_w);
        const ringIdx = Math.floor(dist / (this.calibrationSpacing || 10));
        return RING_COLORS[ringIdx % 4];
    }

    drawZone(zone, isSelected, isHovered) {
        if (!zone.position || zone.led_count <= 0) return;
        const { x, y } = this.worldToScreen(zone.position);
        const ledSpacing = zone.led_spacing ?? 1.0;
        const eff = this.ledSize * this.camera.zoom; // effective LED size in screen pixels
        const ledWidth = eff - 3;

        this.ctx.save();
        this.ctx.translate(x, y);
        this.ctx.rotate(-zone.rotation * Math.PI / 180);

        for (let i = 0; i < zone.led_count; i++) {
            const ledX = i * eff * ledSpacing;

            this.ctx.fillStyle = this.showCalibration ? this._calibrationColor(zone, i) : zone.color;
            this.ctx.globalAlpha = this.showCalibration ? 0.9 : (isSelected ? 0.8 : (isHovered ? 0.6 : 0.5));
            this.ctx.fillRect(ledX, 0, ledWidth, ledWidth);

            this.ctx.globalAlpha = 1;
            this.ctx.strokeStyle = isSelected ? '#14F5FF' : '#666666';
            this.ctx.lineWidth = 1;
            this.ctx.strokeRect(ledX, 0, ledWidth, ledWidth);

            if (i === 0 || i === zone.led_count - 1) {
                this.ctx.fillStyle = '#FFFFFF';
                this.ctx.font = `${Math.max(7, 9 * this.camera.zoom)}px Rajdhani`;
                this.ctx.textAlign = 'center';
                this.ctx.textBaseline = 'middle';
                this.ctx.globalAlpha = 0.6;
                this.ctx.fillText(i.toString(), ledX + ledWidth / 2, ledWidth / 2);
            }
        }

        this.drawDirectionArrow(zone, eff);

        // Zone label (fixed screen size, always readable)
        this.ctx.globalAlpha = 1;
        this.ctx.fillStyle = '#FFFFFF';
        this.ctx.font = 'bold 11px Rajdhani';
        this.ctx.textAlign = 'left';
        this.ctx.textBaseline = 'top';
        this.ctx.fillText(zone.name, 0, -16);

        if (isSelected || isHovered) {
            const outlineWidth = zone.led_count * eff * ledSpacing;
            this.ctx.strokeStyle = isSelected ? '#14F5FF' : '#FFFFFF';
            this.ctx.lineWidth = 1;
            this.ctx.globalAlpha = isSelected ? 1 : 0.5;
            this.ctx.strokeRect(-5, -5, outlineWidth + 10, ledWidth + 10);
        }

        if (zone.hasOverlap) {
            const outlineWidth = zone.led_count * eff * ledSpacing;
            this.ctx.strokeStyle = '#FF0000';
            this.ctx.lineWidth = 3;
            this.ctx.globalAlpha = 0.8;
            this.ctx.setLineDash([5, 5]);
            this.ctx.strokeRect(-7, -7, outlineWidth + 14, ledWidth + 14);
            this.ctx.setLineDash([]);
        }

        this.ctx.restore();
    }

    drawDirectionArrow(zone, eff = this.ledSize) {
        const ledSpacing = zone.led_spacing ?? 1.0;
        const arrowLedIndex = zone.direction === 'forward' ? zone.led_count - 1 : 0;
        const arrowX = arrowLedIndex * eff * ledSpacing + (eff - 3) / 2;
        const arrowY = (eff - 3) / 2;

        this.ctx.fillStyle = '#FFFF00';
        this.ctx.globalAlpha = 1;

        // Triangle arrow pointing in direction of flow
        const arrowSize = Math.max(4, 6 * this.camera.zoom);
        this.ctx.beginPath();
        if (zone.direction === 'forward') {
            // Arrow pointing right
            this.ctx.moveTo(arrowX + arrowSize, arrowY);
            this.ctx.lineTo(arrowX - arrowSize, arrowY - arrowSize);
            this.ctx.lineTo(arrowX - arrowSize, arrowY + arrowSize);
        } else {
            // Arrow pointing left
            this.ctx.moveTo(arrowX - arrowSize, arrowY);
            this.ctx.lineTo(arrowX + arrowSize, arrowY - arrowSize);
            this.ctx.lineTo(arrowX + arrowSize, arrowY + arrowSize);
        }
        this.ctx.closePath();
        this.ctx.fill();

        // Arrow outline
        this.ctx.strokeStyle = '#000000';
        this.ctx.lineWidth = 1;
        this.ctx.stroke();
    }

    drawVirtualBBox() {
        const vbbox = this.calculateVirtualBBox();
        if (!vbbox) return;

        const topLeft = this.worldToScreen({ x: vbbox.min_x, y: vbbox.max_y });
        const bottomRight = this.worldToScreen({ x: vbbox.max_x, y: vbbox.min_y });

        const width = bottomRight.x - topLeft.x;
        const height = bottomRight.y - topLeft.y;

        // Fill with semi-transparent gray
        this.ctx.fillStyle = 'rgba(128, 128, 128, 0.15)';
        this.ctx.fillRect(topLeft.x, topLeft.y, width, height);

        // Dashed gray border
        this.ctx.strokeStyle = 'rgba(128, 128, 128, 0.4)';
        this.ctx.lineWidth = 1;
        this.ctx.setLineDash([8, 4]);
        this.ctx.strokeRect(topLeft.x, topLeft.y, width, height);
        this.ctx.setLineDash([]);

        // VBBox label
        this.ctx.fillStyle = 'rgba(128, 128, 128, 0.7)';
        this.ctx.font = '10px Rajdhani';
        this.ctx.fillText(
            `VBBox: ${(vbbox.max_x - vbbox.min_x).toFixed(1)} × ${(vbbox.max_y - vbbox.min_y).toFixed(1)}`,
            topLeft.x,
            topLeft.y - 5
        );
    }

    drawBoundingBox() {
        const bbox = this.calculateBoundingBox();
        if (!bbox) return;

        const topLeft = this.worldToScreen({ x: bbox.min_x, y: bbox.max_y });
        const bottomRight = this.worldToScreen({ x: bbox.max_x, y: bbox.min_y });

        const width = bottomRight.x - topLeft.x;
        const height = bottomRight.y - topLeft.y;

        this.ctx.strokeStyle = 'rgba(20, 245, 255, 0.3)';
        this.ctx.lineWidth = 2;
        this.ctx.setLineDash([10, 5]);
        this.ctx.strokeRect(topLeft.x, topLeft.y, width, height);
        this.ctx.setLineDash([]);

        // BBox label
        this.ctx.fillStyle = 'rgba(20, 245, 255, 0.6)';
        this.ctx.font = '10px Rajdhani';
        this.ctx.fillText(
            `BBox: ${(bbox.max_x - bbox.min_x).toFixed(1)} × ${(bbox.max_y - bbox.min_y).toFixed(1)}`,
            topLeft.x,
            topLeft.y - 5
        );
    }

    drawEffectCenter() {
        // Always visible - renders on global bbox
        const bbox = this.calculateBoundingBox();
        if (!bbox) return;

        // Calcola world position del centro dalla bbox globale
        const cx_world = bbox.min_x + (bbox.max_x - bbox.min_x) * (this.effectCenter.x / 100);
        const cy_world = bbox.min_y + (bbox.max_y - bbox.min_y) * (this.effectCenter.y / 100);
        const screenPos = this.worldToScreen({ x: cx_world, y: cy_world });

        // Disegna crosshair cyan (più grande e visibile)
        this.ctx.strokeStyle = this.dragCenterState ? '#00FFFF' : 'rgba(0, 255, 255, 0.8)';
        this.ctx.lineWidth = this.dragCenterState ? 3 : 2;
        const size = 15;

        // Linee verticale e orizzontale
        this.ctx.beginPath();
        this.ctx.moveTo(screenPos.x - size, screenPos.y);
        this.ctx.lineTo(screenPos.x + size, screenPos.y);
        this.ctx.moveTo(screenPos.x, screenPos.y - size);
        this.ctx.lineTo(screenPos.x, screenPos.y + size);
        this.ctx.stroke();

        // Centro dot (draggable handle)
        this.ctx.fillStyle = this.dragCenterState ? '#00FFFF' : 'rgba(0, 255, 255, 0.7)';
        this.ctx.beginPath();
        this.ctx.arc(screenPos.x, screenPos.y, 6, 0, Math.PI * 2);
        this.ctx.fill();

        // Outer ring per highlight durante drag
        if (this.dragCenterState) {
            this.ctx.strokeStyle = 'rgba(0, 255, 255, 0.3)';
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();
            this.ctx.arc(screenPos.x, screenPos.y, 10, 0, Math.PI * 2);
            this.ctx.stroke();
        }
    }

    drawCalibrationOverlay() {
        if (!this.showCalibration) return;
        const bbox = this.calculateBoundingBox();
        if (!bbox) return;

        const RING_COLORS = [
            [255, 255, 255],  // white
            [255,  60,  60],  // red
            [ 80, 140, 255],  // blue
            [ 60, 210,  70],  // green
        ];

        // Effect center in screen space
        const cx_w = bbox.min_x + (bbox.max_x - bbox.min_x) * (this.effectCenter.x / 100);
        const cy_w = bbox.min_y + (bbox.max_y - bbox.min_y) * (this.effectCenter.y / 100);
        const cs = this.worldToScreen({ x: cx_w, y: cy_w });

        // Ring spacing in screen pixels
        const spacingPx = this.calibrationSpacing * this.ledSize * this.camera.zoom;
        if (spacingPx < 1) return;

        // How many rings needed to cover the whole canvas
        const corners = [[0,0],[this.canvas.width,0],[0,this.canvas.height],[this.canvas.width,this.canvas.height]];
        const maxR = Math.max(...corners.map(([cx, cy]) => Math.hypot(cx - cs.x, cy - cs.y)));
        const ringCount = Math.ceil(maxR / spacingPx);

        this.ctx.save();

        // Draw rings (innermost last so inner color wins at overlap)
        for (let i = ringCount; i >= 1; i--) {
            const r = i * spacingPx;
            const [R, G, B] = RING_COLORS[(i - 1) % 4];
            this.ctx.strokeStyle = `rgba(${R},${G},${B},0.5)`;
            this.ctx.lineWidth = Math.max(1, 1.5 * this.camera.zoom);
            this.ctx.beginPath();
            this.ctx.arc(cs.x, cs.y, r, 0, Math.PI * 2);
            this.ctx.stroke();
        }

        // Distance labels: shown if zoom is readable, thinned out if many rings
        if (this.camera.zoom >= 0.25 && ringCount > 0) {
            const labelStep = ringCount > 20 ? Math.ceil(ringCount / 15) : 1;
            const fontSize = Math.max(9, Math.min(13, 10 * this.camera.zoom));
            this.ctx.font = `${fontSize}px Rajdhani`;

            // Candidate angles for label placement (right, top, left, bottom)
            const ANGLES = [0, -Math.PI / 2, Math.PI, Math.PI / 2];

            for (let i = 1; i <= ringCount; i++) {
                if (i % labelStep !== 0) continue;
                const r = i * spacingPx;
                const [R, G, B] = RING_COLORS[(i - 1) % 4];
                const label = `${i * this.calibrationSpacing}u`;
                const textW = this.ctx.measureText(label).width;
                const margin = 6;

                for (const angle of ANGLES) {
                    const lx = cs.x + (r + margin) * Math.cos(angle);
                    const ly = cs.y + (r + margin) * Math.sin(angle);
                    const hw = textW / 2 + 2;
                    if (lx - hw > 0 && lx + hw < this.canvas.width && ly > 12 && ly < this.canvas.height - 5) {
                        this.ctx.fillStyle = `rgba(${R},${G},${B},0.85)`;
                        this.ctx.textAlign = 'center';
                        this.ctx.textBaseline = 'middle';
                        this.ctx.fillText(label, lx, ly);
                        break;
                    }
                }
            }
        }

        // Center dot — solid white with glow
        this.ctx.shadowColor = 'rgba(255,255,255,0.9)';
        this.ctx.shadowBlur = 8;
        this.ctx.fillStyle = '#FFFFFF';
        this.ctx.beginPath();
        this.ctx.arc(cs.x, cs.y, Math.max(4, 5 * Math.min(1, this.camera.zoom)), 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.shadowBlur = 0;

        this.ctx.restore();
    }

    isPointOnEffectCenter(screenPos) {
        // Controlla se il click è sul crosshair (handle draggable)
        const bbox = this.calculateBoundingBox();
        if (!bbox) return false;

        const cx_world = bbox.min_x + (bbox.max_x - bbox.min_x) * (this.effectCenter.x / 100);
        const cy_world = bbox.min_y + (bbox.max_y - bbox.min_y) * (this.effectCenter.y / 100);
        const centerScreen = this.worldToScreen({ x: cx_world, y: cy_world });

        const dx = screenPos.x - centerScreen.x;
        const dy = screenPos.y - centerScreen.y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        return distance <= 10; // 10px hit radius
    }

    // ------------------------------------------------------------------------
    // Coordinate Transforms
    // ------------------------------------------------------------------------

    worldToScreen(worldPos) {
        // World → base pixels → screen (apply camera)
        const baseX = this.padding + worldPos.x * this.ledSize;
        const baseY = this.canvas.height - this.padding - worldPos.y * this.ledSize;
        return {
            x: baseX * this.camera.zoom + this.camera.x,
            y: baseY * this.camera.zoom + this.camera.y
        };
    }

    screenToWorld(screenPos) {
        // Screen → base pixels (undo camera) → world
        const baseX = (screenPos.x - this.camera.x) / this.camera.zoom;
        const baseY = (screenPos.y - this.camera.y) / this.camera.zoom;
        return {
            x: (baseX - this.padding) / this.ledSize,
            y: (this.canvas.height - this.padding - baseY) / this.ledSize
        };
    }

    getMousePos(e) {
        const rect = this.canvas.getBoundingClientRect();
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }

    // ------------------------------------------------------------------------
    // Zone Hit Detection
    // ------------------------------------------------------------------------

    findZoneAt(worldPos) {
        // Check zones in reverse order (last drawn = top z-order)
        for (let i = this.zones.length - 1; i >= 0; i--) {
            const zone = this.zones[i];
            if (this.isPointInZone(worldPos, zone)) {
                return zone;
            }
        }
        return null;
    }

    isPointInZone(worldPos, zone) {
        // Transform point to zone local space
        const dx = worldPos.x - zone.position.x;
        const dy = worldPos.y - zone.position.y;

        // Rotate point by -zone.rotation
        const rad = -zone.rotation * Math.PI / 180;
        const localX = dx * Math.cos(rad) - dy * Math.sin(rad);
        const localY = dx * Math.sin(rad) + dy * Math.cos(rad);

        // Check if inside zone bounding box (local space)
        const zoneWidth = zone.led_count * (zone.led_spacing ?? 1.0);
        return localX >= 0 && localX <= zoneWidth &&
               localY >= -1 && localY <= 0;
    }

    // ------------------------------------------------------------------------
    // Utilities
    // ------------------------------------------------------------------------

    selectZone(zone) {
        this.selectedZone = zone;
        this.updateZonesList();
        this.updateInspector();
    }

    calculateBoundingBox() {
        if (this.zones.length === 0) return null;

        let min_x = Infinity, min_y = Infinity;
        let max_x = -Infinity, max_y = -Infinity;

        this.zones.forEach(zone => {
            const corners = this.getZoneCorners(zone);
            corners.forEach(corner => {
                min_x = Math.min(min_x, corner.x);
                min_y = Math.min(min_y, corner.y);
                max_x = Math.max(max_x, corner.x);
                max_y = Math.max(max_y, corner.y);
            });
        });

        return { min_x, min_y, max_x, max_y };
    }

    calculateVirtualBBox() {
        const standardBbox = this.calculateBoundingBox();
        if (!standardBbox) return null;

        // Convert effect center percentage to normalized [0,1]
        const cx_norm = Math.max(0.0, Math.min(1.0, this.effectCenter.x / 100.0));
        const cy_norm = Math.max(0.0, Math.min(1.0, this.effectCenter.y / 100.0));

        // Convert to world coords
        const width = standardBbox.max_x - standardBbox.min_x;
        const height = standardBbox.max_y - standardBbox.min_y;
        const cx_world = standardBbox.min_x + cx_norm * width;
        const cy_world = standardBbox.min_y + cy_norm * height;

        // Calculate symmetric expansion
        const dist_left = cx_world - standardBbox.min_x;
        const dist_right = standardBbox.max_x - cx_world;
        const dist_bottom = cy_world - standardBbox.min_y;
        const dist_top = standardBbox.max_y - cy_world;

        const half_width = Math.max(dist_left, dist_right);
        const half_height = Math.max(dist_bottom, dist_top);

        // Apply 10% padding (5% per side to total 10%)
        const padding_x = half_width * 0.05;
        const padding_y = half_height * 0.05;

        return {
            min_x: cx_world - half_width - padding_x,
            min_y: cy_world - half_height - padding_y,
            max_x: cx_world + half_width + padding_x,
            max_y: cy_world + half_height + padding_y,
            center_world: { x: cx_world, y: cy_world }
        };
    }

    getZoneCorners(zone) {
        const w = zone.led_count * (zone.led_spacing ?? 1.0);
        const corners = [
            { x: 0, y: -1 },  // bottom-left
            { x: w,  y: -1 }, // bottom-right
            { x: w,  y: 0  }, // top-right
            { x: 0,  y: 0  }  // top-left
        ];

        // Rotate corners
        const rad = zone.rotation * Math.PI / 180;
        return corners.map(c => ({
            x: zone.position.x + (c.x * Math.cos(rad) - c.y * Math.sin(rad)),
            y: zone.position.y + (c.x * Math.sin(rad) + c.y * Math.cos(rad))
        }));
    }

    checkOverlaps() {
        // Reset overlap flags
        this.zones.forEach(z => z.hasOverlap = false);

        // Check all pairs
        for (let i = 0; i < this.zones.length; i++) {
            for (let j = i + 1; j < this.zones.length; j++) {
                if (this.zonesOverlap(this.zones[i], this.zones[j])) {
                    this.zones[i].hasOverlap = true;
                    this.zones[j].hasOverlap = true;
                }
            }
        }

        // Show/hide warning
        const hasAnyOverlap = this.zones.some(z => z.hasOverlap);
        document.getElementById('overlap-warning').classList.toggle('hidden', !hasAnyOverlap);
    }

    zonesOverlap(zone1, zone2) {
        const corners1 = this.getZoneCorners(zone1);
        const corners2 = this.getZoneCorners(zone2);

        // Simple AABB overlap check on rotated corners
        const bbox1 = {
            min_x: Math.min(...corners1.map(c => c.x)),
            max_x: Math.max(...corners1.map(c => c.x)),
            min_y: Math.min(...corners1.map(c => c.y)),
            max_y: Math.max(...corners1.map(c => c.y))
        };

        const bbox2 = {
            min_x: Math.min(...corners2.map(c => c.x)),
            max_x: Math.max(...corners2.map(c => c.x)),
            min_y: Math.min(...corners2.map(c => c.y)),
            max_y: Math.max(...corners2.map(c => c.y))
        };

        // Allow edge-to-edge contact (<=) instead of requiring gap (<)
        // This prevents false positives when zones are adjacent but not overlapping
        return !(bbox1.max_x <= bbox2.min_x || bbox1.min_x >= bbox2.max_x ||
                 bbox1.max_y <= bbox2.min_y || bbox1.min_y >= bbox2.max_y);
    }

    updateBoundingBox() {
        const bbox = this.calculateBoundingBox();
        if (bbox) {
            const width = (bbox.max_x - bbox.min_x).toFixed(1);
            const height = (bbox.max_y - bbox.min_y).toFixed(1);
            document.getElementById('bbox-info').textContent = `BBox: ${width}×${height}`;
        }

        // Update Virtual BBox (expanded based on effect center)
        const vbbox = this.calculateVirtualBBox();
        if (vbbox) {
            const vwidth = (vbbox.max_x - vbbox.min_x).toFixed(1);
            const vheight = (vbbox.max_y - vbbox.min_y).toFixed(1);
            document.getElementById('vbbox-info').textContent = `VBBox: ${vwidth}×${vheight}`;
        }
    }

    updateZonesList() {
        const list = document.getElementById('zones-list');

        // Group zones by device_id for display
        const byDevice = {};
        this.zones.forEach(zone => {
            const did = zone.device_id || 'unknown';
            if (!byDevice[did]) byDevice[did] = [];
            byDevice[did].push(zone);
        });

        // Build device group display names from availableDevices lookup
        const deviceNames = {};
        availableDevices.forEach(d => { deviceNames[d.device_id] = d.name; });

        list.innerHTML = Object.entries(byDevice).map(([did, zones]) => {
            const label = deviceNames[did] || did.split('::')[0];
            return `
                <div class="mb-3">
                    <div class="text-[10px] text-white/40 uppercase tracking-widest mb-1 px-1">${label}</div>
                    ${zones.map(zone => {
                        const uid = `${zone.device_id}::${zone.zone_index}`;
                        return `
                        <div class="zone-card p-2 border rounded text-xs mb-1 ${zone === this.selectedZone ? 'selected' : ''}"
                             data-zone-uid="${uid}"
                             style="border-color: ${zone.color};">
                            <div class="font-bold" style="color: ${zone.color};">${zone.name}</div>
                            <div class="text-white/40 text-[10px]">${zone.led_count} LEDs · ${zone.rotation}° · ${zone.direction}</div>
                        </div>`;
                    }).join('')}
                </div>`;
        }).join('');

        // Click handlers — find zone by composite uid (device_id::zone_index)
        list.querySelectorAll('.zone-card').forEach(card => {
            card.addEventListener('click', () => {
                const uid = card.dataset.zoneUid;
                const parts = uid.split('::');
                const zoneIdx = parts[parts.length - 1];
                const did = parts.slice(0, -1).join('::');
                const zone = this.zones.find(z => z.device_id === did && String(z.zone_index) === zoneIdx);
                if (zone) { this.selectZone(zone); this.render(); }
            });
        });
    }

    updateInspector() {
        const noSelection = document.getElementById('no-selection');
        const inspectorFields = document.getElementById('inspector-fields');

        if (!this.selectedZone) {
            noSelection.classList.remove('hidden');
            inspectorFields.classList.add('hidden');
            return;
        }

        noSelection.classList.add('hidden');
        inspectorFields.classList.remove('hidden');

        const zone = this.selectedZone;
        document.getElementById('zone-name').value = zone.name;
        document.getElementById('zone-x').value = zone.position.x.toFixed(1);
        document.getElementById('zone-y').value = zone.position.y.toFixed(1);

        // Update rotation buttons
        document.querySelectorAll('.rotation-btn').forEach(btn => {
            const rotation = parseInt(btn.dataset.rotation);
            if (rotation === zone.rotation) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });

        document.getElementById('zone-direction').value = zone.direction;
        document.getElementById('zone-device').textContent = zone.device_id;
        document.getElementById('zone-index').textContent = zone.zone_index;
        document.getElementById('zone-led-count').textContent = zone.led_count;

        // Physical length
        const physInput = document.getElementById('zone-physical-length');
        if (physInput) {
            physInput.value = zone.physical_length_cm != null ? zone.physical_length_cm : '';
            const spacingEl = document.getElementById('zone-spacing-display');
            if (spacingEl) {
                const sp = zone.led_spacing ?? 1.0;
                spacingEl.textContent = sp !== 1.0 ? `${sp.toFixed(2)} units/LED` : '1.0 (default)';
            }
        }
    }

    updateEffectCenterInputs() {
        const centerX = document.getElementById('center-x');
        const centerY = document.getElementById('center-y');

        if (centerX && centerY) {
            centerX.value = Math.round(this.effectCenter.x);
            centerY.value = Math.round(this.effectCenter.y);
        }

        // Update active preset button if values match a preset
        const presets = {
            'center': { x: 50, y: 50 },
            'top': { x: 50, y: 90 },
            'bottom': { x: 50, y: 10 },
            'left': { x: 10, y: 50 },
            'right': { x: 90, y: 50 }
        };

        let matchedPreset = null;
        for (const [name, preset] of Object.entries(presets)) {
            if (Math.abs(this.effectCenter.x - preset.x) < 0.5 &&
                Math.abs(this.effectCenter.y - preset.y) < 0.5) {
                matchedPreset = name;
                break;
            }
        }

        // Update active state on preset buttons
        document.querySelectorAll('.preset-btn').forEach(btn => {
            if (btn.dataset.preset === matchedPreset) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    autoLayout() {
        // Group zones by device, stack devices vertically with inter-device gap
        const byDevice = {};
        this.zones.forEach(z => {
            const did = z.device_id || 'unknown';
            if (!byDevice[did]) byDevice[did] = [];
            byDevice[did].push(z);
        });

        let currentY = 5;
        const zoneGap = 2;       // gap between zones of same device
        const deviceGap = 5;     // extra gap between devices

        Object.values(byDevice).forEach((zones, devIdx) => {
            zones.forEach(zone => {
                zone.position.x = 5;
                zone.position.y = currentY;
                zone.rotation = 0;
                currentY += 1 + zoneGap;
            });
            currentY += deviceGap;  // extra space after each device group
        });

        this.updateInspector();
        this.checkOverlaps();
        this.updateBoundingBox();
        this.render();
    }

    reset() {
        this.zones = [];
        this.selectedZone = null;
        loadAndRenderScene();
    }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

let canvas;

// Calibration blink config — read from panel controls
let calibrationConfig = {
    center: { blink: true,  period_ms: 333  },
    white:  { blink: false, period_ms: 1000 },
    red:    { blink: false, period_ms: 1000 },
    blue:   { blink: false, period_ms: 1000 },
    green:  { blink: false, period_ms: 1000 },
};

function readCalibrationConfig() {
    document.querySelectorAll('#calibration-panel .calib-row').forEach(row => {
        const key = row.dataset.key;
        const blink = row.querySelector('.calib-blink').checked;
        const period = parseInt(row.querySelector('.calib-speed').value);
        calibrationConfig[key] = { blink, period_ms: period };
    });
    return calibrationConfig;
}

// Debounced hardware calibration — module-level so class methods can call it
let _calibrationTimer = null;
function triggerHardwareCalibration() {
    if (!canvas || !canvas.showCalibration) return;
    clearTimeout(_calibrationTimer);
    _calibrationTimer = setTimeout(() => {
        api('test_topology_calibration', canvas.effectCenter, canvas.calibrationSpacing, readCalibrationConfig());
    }, 80);
}

async function loadSceneTopology() {
    try {
        console.log('[Topology] Loading unified scene topology...');
        const result = await eel.get_scene_topology()();
        if (result.success) {
            console.log(`[Topology] Scene loaded: ${result.zones.length} zones, ${result.devices.length} devices`);
            return result;
        }
        console.warn('[Topology] Scene load failed:', result.error);
    } catch (e) {
        console.warn('[Topology] Failed to load scene:', e);
    }
    return { zones: [], devices: [], global_effect_center: { x: 50, y: 50 } };
}

async function loadAndRenderScene() {
    const scene = await loadSceneTopology();
    availableDevices = scene.devices || [];

    // Stamp each zone with a unique _uid for zone list lookups
    canvas.zones = JSON.parse(JSON.stringify(scene.zones)).map(z => ({
        ...z,
        id: z.zone_index,
    }));

    canvas.effectCenter = {
        x: scene.global_effect_center?.x ?? 50,
        y: scene.global_effect_center?.y ?? 50,
    };
    canvas.selectedZone = null;

    renderDeviceLegend(availableDevices);
    canvas.updateZonesList();
    canvas.updateInspector();
    canvas.updateEffectCenterInputs();
    canvas.updateBoundingBox();
    canvas.render();
}

function renderDeviceLegend(devices) {
    const noDevicesEl = document.getElementById('no-devices-state');
    const listEl = document.getElementById('topology-device-list');
    listEl.innerHTML = '';

    if (!devices || devices.length === 0) {
        noDevicesEl.classList.remove('hidden');
        return;
    }
    noDevicesEl.classList.add('hidden');

    devices.forEach(dev => {
        const card = document.createElement('div');
        card.className = 'device-selector-card';
        card.dataset.deviceId = dev.device_id;
        card.innerHTML = `
            <div class="flex items-center justify-between gap-2">
                <div class="flex items-center gap-2 min-w-0">
                    <div class="w-3 h-3 rounded-sm shrink-0" style="background:${dev.color};"></div>
                    <div class="min-w-0">
                        <div class="device-selector-name truncate">${dev.name}</div>
                        <div class="device-selector-meta">${dev.zone_count} zones · ${dev.led_count} LEDs</div>
                    </div>
                </div>
                <button class="flash-btn shrink-0 w-7 h-7 flex items-center justify-center rounded border border-white/20 text-white/50 hover:text-[var(--primary-accent)] hover:border-[var(--primary-accent)] transition-colors"
                        title="Flash to identify" data-device-id="${dev.device_id}">
                    <span class="material-symbols-outlined" style="font-size:16px;">bolt</span>
                </button>
            </div>`;
        card.querySelector('.flash-btn').addEventListener('click', async (e) => {
            e.stopPropagation();
            const btn = e.currentTarget;
            btn.style.color = 'var(--primary-accent)';
            btn.style.borderColor = 'var(--primary-accent)';
            await api('flash_topology_device', dev.device_id);
            setTimeout(() => { btn.style.color = ''; btn.style.borderColor = ''; }, 400);
        });
        listEl.appendChild(card);
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    console.log('[Topology Editor] Initializing...');

    // Initialize canvas (empty — scene loaded below)
    const canvasElement = document.getElementById('topology-canvas');
    canvas = new TopologyCanvas(canvasElement);
    canvas.updateZonesList();
    canvas.updateInspector();
    canvas.updateEffectCenterInputs();
    canvas.render();

    // Load all devices + zones as a unified scene
    await loadAndRenderScene();

    // Grid controls
    document.getElementById('grid-size').addEventListener('input', (e) => {
        canvas.gridSize = parseFloat(e.target.value);
        document.getElementById('grid-size-value').textContent = e.target.value;
        canvas.render();
    });

    document.getElementById('snap-enabled').addEventListener('change', (e) => {
        canvas.snapEnabled = e.target.checked;
    });

    document.getElementById('show-grid').addEventListener('change', (e) => {
        canvas.showGrid = e.target.checked;
        canvas.render();
    });

    // Inspector controls
    document.getElementById('zone-name').addEventListener('input', (e) => {
        if (canvas.selectedZone) {
            canvas.selectedZone.name = e.target.value;
            canvas.updateZonesList();
            canvas.render();
        }
    });

    document.getElementById('zone-x').addEventListener('input', (e) => {
        if (canvas.selectedZone) {
            canvas.selectedZone.position.x = parseFloat(e.target.value) || 0;
            canvas.checkOverlaps();
            canvas.updateBoundingBox();
            canvas.render();
        }
    });

    document.getElementById('zone-y').addEventListener('input', (e) => {
        if (canvas.selectedZone) {
            canvas.selectedZone.position.y = parseFloat(e.target.value) || 0;
            canvas.checkOverlaps();
            canvas.updateBoundingBox();
            canvas.render();
        }
    });

    // Rotation buttons (90° snapping)
    document.querySelectorAll('.rotation-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            if (canvas.selectedZone) {
                const rotation = parseInt(btn.dataset.rotation);
                canvas.selectedZone.rotation = rotation;

                // Update button states
                document.querySelectorAll('.rotation-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                canvas.checkOverlaps();
                canvas.updateBoundingBox();
                canvas.render();
            }
        });
    });

    document.getElementById('zone-direction').addEventListener('change', (e) => {
        if (canvas.selectedZone) {
            canvas.selectedZone.direction = e.target.value;
            canvas.render();
        }
    });

    document.getElementById('btn-flip-direction').addEventListener('click', () => {
        if (canvas.selectedZone) {
            canvas.selectedZone.direction = canvas.selectedZone.direction === 'forward' ? 'reverse' : 'forward';
            canvas.updateInspector();
            canvas.render();
        }
    });

    document.getElementById('zone-physical-length').addEventListener('input', (e) => {
        if (!canvas.selectedZone) return;
        const zone = canvas.selectedZone;
        const cm = parseFloat(e.target.value);
        if (!isNaN(cm) && cm > 0 && zone.led_count > 0) {
            zone.physical_length_cm = cm;
            zone.led_spacing = cm / zone.led_count;
        } else if (e.target.value === '') {
            zone.physical_length_cm = null;
            zone.led_spacing = 1.0;
        }
        canvas.updateInspector();
        canvas.checkOverlaps();
        canvas.updateBoundingBox();
        canvas.render();
    });

    // Global Effect Center Controls (topology-level)

    document.getElementById('center-x').addEventListener('input', (e) => {
        canvas.effectCenter.x = Math.max(0, Math.min(100, parseFloat(e.target.value) || 50));
        // Remove active state from all preset buttons (manual input)
        document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
        canvas.updateBoundingBox();
        canvas.render();
    });

    document.getElementById('center-y').addEventListener('input', (e) => {
        canvas.effectCenter.y = Math.max(0, Math.min(100, parseFloat(e.target.value) || 50));
        // Remove active state from all preset buttons (manual input)
        document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
        canvas.updateBoundingBox();
        canvas.render();
    });

    // Preset buttons
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const presets = {
                'center': { x: 50, y: 50 },
                'top': { x: 50, y: 90 },
                'bottom': { x: 50, y: 10 },
                'left': { x: 10, y: 50 },
                'right': { x: 90, y: 50 }
            };

            // Toggle active state (same pattern as rotation buttons)
            document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            canvas.effectCenter = { ...presets[btn.dataset.preset] };
            canvas.updateEffectCenterInputs();
            canvas.updateBoundingBox();
            canvas.render();
        });
    });

    // Zones list click handler (event delegation) — uses composite uid
    document.getElementById('zones-list').addEventListener('click', (e) => {
        const zoneCard = e.target.closest('.zone-card');
        if (zoneCard) {
            const uid = zoneCard.dataset.zoneUid;
            if (uid) {
                const parts = uid.split('::');
                const zoneIdx = parts[parts.length - 1];
                const did = parts.slice(0, -1).join('::');
                const zone = canvas.zones.find(z => z.device_id === did && String(z.zone_index) === zoneIdx);
                if (zone) { canvas.selectZone(zone); canvas.render(); }
            }
        }
    });

    // Canvas controls
    document.getElementById('btn-auto-layout').addEventListener('click', () => {
        canvas.autoLayout();
        showNotification('✓ Auto layout applied', 'success');
    });

    document.getElementById('btn-reset').addEventListener('click', () => {
        if (confirm('Reset all zones to default positions?')) {
            canvas.reset();
            showNotification('✓ Topology reset', 'success');
        }
    });

    document.getElementById('btn-reset-view').addEventListener('click', () => {
        canvas.resetCamera();
    });

    document.getElementById('btn-calibration-toggle').addEventListener('click', async (e) => {
        canvas.showCalibration = !canvas.showCalibration;
        e.currentTarget.classList.toggle('active', canvas.showCalibration);
        document.getElementById('calibration-panel').classList.toggle('hidden', !canvas.showCalibration);
        canvas.render();
        if (canvas.showCalibration) {
            api('test_topology_calibration', canvas.effectCenter, canvas.calibrationSpacing, readCalibrationConfig());
        } else {
            api('stop_topology_calibration');
        }
    });

    document.getElementById('calibration-spacing').addEventListener('input', (e) => {
        const val = parseFloat(e.target.value);
        if (val > 0) {
            canvas.calibrationSpacing = val;
            if (canvas.showCalibration) {
                canvas.render();
                triggerHardwareCalibration();
            }
        }
    });

    // Calibration panel: blink checkboxes and speed sliders
    document.querySelectorAll('#calibration-panel .calib-row').forEach(row => {
        const blinkCb = row.querySelector('.calib-blink');
        const speedRow = row.querySelector('.calib-speed-row');
        const speedInput = row.querySelector('.calib-speed');
        const speedLabel = row.querySelector('.calib-speed-label');

        blinkCb.addEventListener('change', () => {
            speedRow.classList.toggle('hidden', !blinkCb.checked);
            triggerHardwareCalibration();
        });

        speedInput.addEventListener('input', () => {
            speedLabel.textContent = `${speedInput.value}ms`;
            triggerHardwareCalibration();
        });
    });

    document.getElementById('btn-reload-openrgb').addEventListener('click', async () => {
        try {
            const result = await eel.reload_scene_from_openrgb()();
            if (result.success) {
                // Merge reloaded zones back (preserving positions from current canvas)
                const reloadedMap = {};
                result.zones.forEach(z => {
                    const uid = `${z.device_id}::${z.zone_index}`;
                    reloadedMap[uid] = z;
                });
                canvas.zones = canvas.zones.map(z => {
                    const uid = `${z.device_id}::${z.zone_index}`;
                    return reloadedMap[uid] ? { ...z, led_count: reloadedMap[uid].led_count } : z;
                });
                // Add newly detected zones that weren't on canvas
                result.zones.forEach(z => {
                    const uid = `${z.device_id}::${z.zone_index}`;
                    const exists = canvas.zones.find(cz => `${cz.device_id}::${cz.zone_index}` === uid);
                    if (!exists) canvas.zones.push({ ...z, id: z.zone_index });
                });

                const hasNew = Object.values(result.changes).some(c => c.new_zones?.length > 0);
                if (hasNew) canvas.autoLayout();
                else { canvas.render(); canvas.updateZonesList(); }
                showNotification(result.message || 'Scene reloaded from OpenRGB', 'success');
            } else {
                showNotification(result.error || 'Reload failed', 'error');
            }
        } catch (e) {
            showNotification('Failed to reload from OpenRGB', 'error');
        }
    });

    document.getElementById('btn-save').addEventListener('click', async () => {
        try {
            const result = await eel.save_scene_topology(canvas.zones, canvas.effectCenter)();
            if (result.success) {
                showNotification(result.message || 'Scene saved', 'success');
            } else {
                showNotification(result.error || 'Save failed', 'error');
            }
        } catch (e) {
            showNotification('Failed to save scene', 'error');
        }
    });

    console.log('[Topology Editor] Ready');
});

// Fade in page
window.addEventListener('load', () => {
    document.body.classList.add('loaded');
});
