/* Private design study. Real site controls and content keep their own behavior. */
(function () {
    "use strict";

    const root = document.documentElement;
    const storageKey = "jm.design-study.v1";
    const presets = {
        blueprint: {
            grain: 16,
            grid: 32,
            glow: 100,
            caption:
                "A · Blueprint — The current blue drafting field, with grain on the background.",
        },
        vector: {
            grain: 20,
            grid: 28,
            glow: 55,
            caption:
                "B · Vector — Mint light, a precise wire grid and sharper geometry. The most restrained.",
        },
        "light-grid": {
            grain: 18,
            grid: 48,
            glow: 105,
            caption:
                "C · Light Grid — Deep ink, ice-blue light and a receding grid. My recommended direction.",
        },
        afterglow: {
            grain: 24,
            grid: 40,
            glow: 115,
            caption: "D · Afterglow — Indigo, warm light and an angled grid. The most expressive.",
        },
    };
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
              : "light-grid";
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

    function drawGrid() {
        if (gridDrawn === state.grid) return;
        gridDrawn = state.grid;
        const lines = [];
        for (let x = -1440; x <= 2880; x += state.grid * 4) {
            lines.push(`M720 64L${x} 960`);
        }
        for (let distance = state.grid * 0.4; distance < 900; distance *= 1.36) {
            lines.push(`M0 ${64 + distance}H1440`);
        }
        for (const path of field.querySelectorAll("path")) path.setAttribute("d", lines.join(""));
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
        bar.querySelector(".study-caption").textContent = presets[state.version].caption;
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
        state = { version, ...presets[version] };
        delete state.caption;
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
            document.body.append(input);
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
        for (const button of bar.querySelectorAll("[data-preset]")) {
            button.addEventListener("click", () => choose(button.dataset.preset));
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
        const adjustments = bar.querySelector("details");
        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && adjustments.open) {
                adjustments.open = false;
                adjustments.querySelector("summary").focus();
            }
        });
        document.addEventListener("click", (event) => {
            if (!bar.contains(event.target)) adjustments.open = false;
            const link = event.target.closest('a[href^="/opt/"]');
            if (link) link.href = versionURL(link.href);
        });
        window.addEventListener("popstate", () => {
            state = readState();
            render();
        });
        render();
    });
})();
