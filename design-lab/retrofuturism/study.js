/* Private design study. Real site controls and content keep their own behavior. */
(function () {
    "use strict";

    const root = document.documentElement;
    const storageKey = "jm.design-study.v1";
    // The build inserts presets.json here, sharing metadata with the visual picker.
    const presets = /* @presets */ {};
    const versions = Object.keys(presets);
    const limits = { grain: [0, 35, 1], grid: [24, 80, 4], glow: [0, 160, 5] };
    let bar;
    let field;
    let gridDrawn;
    let state;
    let persistTimer;

    function bounded(key, value, fallback) {
        const [min, max, step] = limits[key];
        const number = Number(value);
        if (value === null || value === "" || !Number.isFinite(number)) return fallback;
        return Math.min(max, Math.max(min, Math.round(number / step) * step));
    }

    function readState() {
        const query = new URLSearchParams(location.search);
        let saved = {};
        try {
            saved = JSON.parse(localStorage.getItem(storageKey)) || {};
        } catch (_) {}
        const requested = query.get("v");
        const version = Object.hasOwn(presets, requested)
            ? requested
            : Object.hasOwn(presets, saved.version)
              ? saved.version
              : "ion";
        const result = { version };
        for (const key of Object.keys(limits)) {
            const fallback = requested
                ? presets[version][key]
                : bounded(key, saved[key], presets[version][key]);
            result[key] = bounded(key, query.get(key), fallback);
        }
        const theme = query.get("theme");
        if (theme === "dark" || theme === "light") root.dataset.theme = theme;
        return result;
    }

    function applyTokens() {
        root.dataset.study = state.version;
        root.dataset.pattern = presets[state.version].pattern;
        root.dataset.studyRound = presets[state.version].family === "New" ? "2" : "1";
        root.style.setProperty("--study-grain", state.grain / 100);
        root.style.setProperty("--grid-size", state.grid + "px");
        root.style.setProperty("--study-energy", state.glow / 100);
    }

    function versionURL(path = location.href) {
        const url = new URL(path, location.href);
        url.searchParams.set("v", state.version);
        url.searchParams.set("theme", root.dataset.theme === "light" ? "light" : "dark");
        for (const key of Object.keys(limits)) url.searchParams.set(key, state[key]);
        return url;
    }

    function persist() {
        clearTimeout(persistTimer);
        try {
            localStorage.setItem(storageKey, JSON.stringify(state));
        } catch (_) {}
        history.replaceState(null, "", versionURL());
        for (const link of document.querySelectorAll('a[href^="/opt/"]')) {
            const url = versionURL(link.getAttribute("href"));
            link.setAttribute("href", url.pathname + url.search + url.hash);
        }
    }

    // Static vector geometry: no animation loop, canvas or per-scroll drawing.
    // The same paths drive the real backdrop and its small gallery preview.
    function patternPath(pattern, spacing) {
        const lines = [];
        const point = (x, y) => `${Math.round(x)} ${Math.round(y)}`;
        const segment = (x1, y1, x2, y2) => lines.push(`M${point(x1, y1)}L${point(x2, y2)}`);
        if (pattern === "perspective" || pattern === "horizon") {
            const horizon = pattern === "horizon" ? 260 : 64;
            for (let x = -1440; x <= 2880; x += spacing * 4) {
                segment(720, horizon, x, 960);
            }
            for (let distance = spacing * 0.4; distance < 960 - horizon; distance *= 1.36) {
                segment(0, horizon + distance, 1440, horizon + distance);
            }
            if (pattern === "horizon") segment(0, horizon, 1440, horizon);
        } else if (pattern === "corridor") {
            const center = [880, 340];
            const corners = [
                [-480, -360],
                [1840, -360],
                [1840, 1320],
                [-480, 1320],
            ];
            for (let scale = 0.07; scale < 1.8; scale *= 1 + spacing / 150) {
                const ring = corners.map(([x, y]) =>
                    point(center[0] + (x - center[0]) * scale, center[1] + (y - center[1]) * scale),
                );
                lines.push(`M${ring.join("L")}Z`);
            }
            for (const [x, y] of corners) segment(...center, x, y);
            segment(...center, -480, 480);
            segment(...center, 1840, 480);
        } else if (pattern === "contours") {
            for (let level = -5; level < 960 / spacing + 6; level++) {
                let path = "";
                for (let x = -20; x <= 1460; x += 20) {
                    const y =
                        level * spacing +
                        Math.sin(x / 230 + level * 0.13) * 130 +
                        Math.sin(x / 490 - level * 0.1) * 90;
                    path += (x === -20 ? "M" : "L") + point(x, y);
                }
                lines.push(path);
            }
        } else if (pattern === "orbits") {
            const cx = 960,
                cy = 280;
            for (let radius = spacing; radius < 1600; radius += spacing * 1.7) {
                const ry = radius * 0.76;
                lines.push(
                    `M${point(cx - radius, cy)}a${radius} ${ry} 0 1 0 ${radius * 2} 0a${radius} ${ry} 0 1 0 ${-radius * 2} 0`,
                );
            }
            for (let angle = 0; angle < Math.PI * 2; angle += Math.PI / 6) {
                segment(cx, cy, cx + Math.cos(angle) * 1800, cy + Math.sin(angle) * 1400);
            }
        } else if (pattern === "facets") {
            const stepX = spacing * 3,
                stepY = spacing * 2.2;
            const meshPoint = (column, row) => [
                column * stepX +
                    ((row % 2) * stepX) / 2 +
                    Math.sin(row * 1.7 + column) * spacing * 0.4,
                row * stepY + Math.cos(row + column * 0.7) * spacing * 0.5,
            ];
            for (let row = -2; row < 960 / stepY + 2; row++) {
                for (let column = -2; column < 1440 / stepX + 2; column++) {
                    const a = meshPoint(column, row),
                        b = meshPoint(column + 1, row);
                    const c = meshPoint(column + (row % 2 ? 1 : 0), row + 1);
                    lines.push(`M${point(...a)}L${point(...b)}L${point(...c)}Z`);
                }
            }
        } else if (pattern === "diagonal") {
            for (let x = -1440; x < 2880; x += spacing * 3) {
                segment(x, 0, x + 1440, 960);
                segment(x, 0, x - 1440, 960);
            }
        } else {
            const raster = pattern === "raster";
            for (let y = 0; y < 960; y += raster ? spacing / 2 : spacing * 2)
                segment(0, y, 1440, y);
            for (let x = 0; x < 1440; x += raster ? spacing * 4 : spacing * 2) {
                segment(x, 0, x, 960);
                if (raster) for (let y = 0; y < 960; y += spacing * 2) segment(x - 7, y, x + 7, y);
            }
        }
        return lines.join("");
    }

    function drawGrid() {
        const pattern = presets[state.version].pattern;
        const key = `${pattern}:${state.grid}`;
        if (gridDrawn === key) return;
        gridDrawn = key;
        const pathData = patternPath(pattern, state.grid);
        for (const path of field.querySelectorAll("path")) path.setAttribute("d", pathData);
    }

    function syncTheme() {
        const label =
            root.dataset.theme === "light" ? "Switch to dark mode" : "Switch to light mode";
        const button = bar.querySelector("[data-study-theme]");
        button.setAttribute("aria-label", label);
        button.title = label;
    }

    function render(saveImmediately = true) {
        applyTokens();
        if (!bar) return;
        for (const button of bar.querySelectorAll("[data-preset]")) {
            button.setAttribute("aria-pressed", String(button.dataset.preset === state.version));
        }
        bar.querySelector("[data-study-preset]").value = state.version;
        const preset = presets[state.version];
        const caption = `${preset.letter} · ${preset.name} — ${preset.description}`;
        const description = bar.querySelector(".study-caption");
        if (description.textContent !== caption) description.textContent = caption;
        bar.querySelector("[data-study-count]").textContent =
            `${versions.indexOf(state.version) + 1} / ${versions.length}`;
        for (const key of Object.keys(limits)) {
            bar.querySelector(`[data-knob="${key}"]`).value = state[key];
            bar.querySelector(`[data-value="${key}"]`).textContent =
                state[key] + (key === "grid" ? " px" : "%");
        }
        drawGrid();
        syncTheme();
        if (saveImmediately) persist();
        else {
            // Keep dragging immediate without flooding browser history or storage.
            clearTimeout(persistTimer);
            persistTimer = setTimeout(persist, 180);
        }
    }

    function choose(version) {
        if (!Object.hasOwn(presets, version)) return;
        const { grain, grid, glow } = presets[version];
        state = { version, grain, grid, glow };
        bar.querySelector(".study-browse").open = false;
        bar.querySelector(".study-message").textContent = "";
        render();
    }

    async function copyLink() {
        const message = bar.querySelector(".study-message");
        const url = versionURL().href;
        let copied = false;
        if (navigator.clipboard) {
            try {
                await navigator.clipboard.writeText(url);
                copied = true;
            } catch (_) {}
        }
        // LAN previews use HTTP, where the modern clipboard API may be unavailable.
        if (!copied) {
            const focused = document.activeElement;
            const input = document.createElement("textarea");
            input.className = "study-copy-buffer";
            input.value = url;
            input.setAttribute("aria-label", "Version link");
            bar.append(input);
            input.select();
            try {
                copied = document.execCommand("copy");
            } catch (_) {}
            input.remove();
            focused?.focus({ preventScroll: true });
        }
        message.textContent = copied
            ? "Link copied. It includes this version, theme and all three settings."
            : "Copy the address from your browser. It includes this version and all your settings.";
    }

    // Run before the first paint so a shared link opens directly in its chosen style.
    state = readState();
    applyTokens();
    document.addEventListener("DOMContentLoaded", function () {
        bar = document.querySelector(".study-bar");
        if (!bar) return;
        field = document.createElement("div");
        field.className = "study-field";
        field.setAttribute("aria-hidden", "true");
        for (const position of ["upper", "lower"]) {
            const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
            svg.setAttribute("viewBox", "0 0 1440 960");
            svg.setAttribute("preserveAspectRatio", "none");
            svg.setAttribute("class", "study-perspective study-perspective--" + position);
            const path = document.createElementNS(svg.namespaceURI, "path");
            path.setAttribute("vector-effect", "non-scaling-stroke");
            svg.append(path);
            field.append(svg);
        }
        document.querySelector(".page-surface").prepend(field);
        for (const preview of bar.querySelectorAll("[data-swatch-path]")) {
            const preset = presets[preview.dataset.swatchPath];
            preview.setAttribute("d", patternPath(preset.pattern, preset.grid));
        }
        for (const button of bar.querySelectorAll("[data-preset]")) {
            button.addEventListener("click", () => {
                choose(button.dataset.preset);
                const gallery = bar.querySelector(".study-browse");
                gallery.querySelector("summary").focus({ preventScroll: true });
            });
        }
        for (const button of bar.querySelectorAll("[data-study-step]")) {
            button.addEventListener("click", () => {
                const next =
                    (versions.indexOf(state.version) +
                        Number(button.dataset.studyStep) +
                        versions.length) %
                    versions.length;
                choose(versions[next]);
            });
        }
        bar.querySelector("[data-study-preset]").addEventListener("change", (event) =>
            choose(event.target.value),
        );
        for (const input of bar.querySelectorAll("[data-knob]")) {
            input.addEventListener("input", () => {
                const key = input.dataset.knob;
                state[key] = bounded(key, input.value, presets[state.version][key]);
                render(false);
            });
        }
        bar.querySelector("[data-study-reset]").addEventListener("click", () =>
            choose(state.version),
        );
        bar.querySelector("[data-study-copy]").addEventListener("click", copyLink);
        bar.querySelector("[data-study-theme]").addEventListener("click", () => {
            document.querySelector("[data-theme-toggle]").click();
        });
        new MutationObserver(() => {
            syncTheme();
            persist();
        }).observe(root, {
            attributes: true,
            attributeFilter: ["data-theme"],
        });
        const pagePicker = bar.querySelector("#study-page");
        if (![...pagePicker.options].some((option) => option.value === location.pathname)) {
            pagePicker.add(new Option("Current page", location.pathname));
        }
        pagePicker.value = location.pathname;
        pagePicker.addEventListener("change", () => {
            location.href = versionURL(pagePicker.value);
        });
        const drawers = [...bar.querySelectorAll("details")];
        for (const drawer of drawers) {
            drawer.querySelector("summary").addEventListener("click", () => {
                for (const other of drawers) if (other !== drawer) other.open = false;
            });
        }
        document.addEventListener("keydown", (event) => {
            const opened = drawers.find((drawer) => drawer.open);
            if (event.key === "Escape" && opened) {
                opened.open = false;
                opened.querySelector("summary").focus();
            }
        });
        document.addEventListener("click", (event) => {
            if (!bar.contains(event.target)) for (const drawer of drawers) drawer.open = false;
            const link = event.target.closest('a[href^="/opt/"]');
            if (link) link.href = versionURL(link.href);
        });
        document.addEventListener("focusin", (event) => {
            // Tabbing back into the page must never leave its focused link covered.
            if (!bar.contains(event.target)) for (const drawer of drawers) drawer.open = false;
        });
        window.addEventListener("popstate", () => {
            state = readState();
            render();
        });
        new ResizeObserver(() => {
            root.style.setProperty("--study-bar-height", `${bar.getBoundingClientRect().height}px`);
        }).observe(bar);
        render();
    });
})();
