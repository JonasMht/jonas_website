/* Private design study. Real site controls and content keep their own behavior. */
(function () {
    "use strict";

    const root = document.documentElement;
    const storageKey = "jm.design-study.v1";
    // The build inserts presets.json here, sharing metadata with the visual picker.
    const presets = /* @presets */ {};
    const details = /* @details */ {};
    const media = window.StudyMedia;
    const voteKey = "jm.design-votes.v1";
    const versions = Object.keys(presets);
    const limits = { grain: [0, 35, 1], grid: [24, 80, 4], glow: [0, 160, 5] };
    let bar;
    let field;
    let gridDrawn;
    let state;
    let persistTimer;
    let votes;
    let delegatingTheme = false;

    function bounded(key, value, fallback) {
        const [min, max, step] = limits[key];
        const number = Number(value);
        if (value === null || value === "" || !Number.isFinite(number)) return fallback;
        return Math.min(max, Math.max(min, Math.round(number / step) * step));
    }

    function readState() {
        const query = new URLSearchParams(location.search);
        const mix = Object.hasOwn(details.mixes, query.get("mix"))
            ? details.mixes[query.get("mix")]
            : null;
        let saved = {};
        try {
            saved = JSON.parse(localStorage.getItem(storageKey)) || {};
        } catch (_) {}
        const requested = query.get("v") || mix?.version;
        const version = Object.hasOwn(presets, requested)
            ? requested
            : Object.hasOwn(presets, saved.version)
              ? saved.version
              : "ion";
        const result = { version };
        for (const key of Object.keys(limits)) {
            const fallback = requested
                ? (mix?.[key] ?? presets[version][key])
                : bounded(key, saved[key], presets[version][key]);
            result[key] = bounded(key, query.get(key), fallback);
        }
        for (const [key, choices, baseline] of [
            ["frame", details.frames, "corners"],
            ["reveal", details.reveals, "still"],
        ]) {
            const value = query.get(key) || mix?.[key] || (!requested && saved[key]);
            result[key] = Object.hasOwn(choices, value) ? value : baseline;
        }
        const theme = query.get("theme");
        if (theme === "dark" || theme === "light") root.dataset.theme = theme;
        return result;
    }

    function applyTokens() {
        root.dataset.study = state.version;
        root.dataset.pattern = presets[state.version].pattern;
        root.dataset.studyRound = String(presets[state.version].round);
        root.style.setProperty("--study-grain", state.grain / 100);
        root.style.setProperty("--grid-size", state.grid + "px");
        root.style.setProperty("--study-energy", state.glow / 100);
        root.dataset.studyFrame = state.frame;
        root.dataset.studyReveal = state.reveal;
        media.apply(state.frame, state.reveal);
    }

    function versionURL(path = location.href) {
        const url = new URL(path, location.href);
        url.searchParams.set("v", state.version);
        url.searchParams.set("theme", root.dataset.theme === "light" ? "light" : "dark");
        for (const key of Object.keys(limits)) url.searchParams.set(key, state[key]);
        url.searchParams.delete("mix");
        url.searchParams.set("frame", state.frame);
        url.searchParams.set("reveal", state.reveal);
        return url;
    }

    function persist() {
        clearTimeout(persistTimer);
        try {
            localStorage.setItem(storageKey, JSON.stringify(state));
        } catch (_) {}
        history.replaceState(null, "", versionURL());
        for (const link of document.querySelectorAll('a[href^="/opt/"]')) {
            if (link.hasAttribute("data-saved-mix")) continue;
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
        const caption = `${preset.letter} · ${preset.name} / ${details.frames[state.frame].name} / ${details.reveals[state.reveal].name}`;
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
        for (const key of ["frame", "reveal", "mix"]) {
            for (const button of bar.querySelectorAll(`[data-${key}]`)) {
                const selected =
                    key === "mix"
                        ? isMix(details.mixes[button.dataset.mix])
                        : button.dataset[key] === state[key];
                button.setAttribute("aria-pressed", String(selected));
            }
        }
        renderVotes();
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
        state = { ...state, version, grain, grid, glow };
        bar.querySelector(".study-browse").open = false;
        bar.querySelector(".study-message").textContent = "";
        render();
    }

    async function copyText(value) {
        let copied = false;
        if (navigator.clipboard) {
            try {
                await navigator.clipboard.writeText(value);
                copied = true;
            } catch (_) {}
        }
        // LAN previews use HTTP, where the modern clipboard API may be unavailable.
        if (!copied) {
            const focused = document.activeElement;
            const input = document.createElement("textarea");
            input.className = "study-copy-buffer";
            input.value = value;
            input.setAttribute("aria-label", "Design choices to copy");
            bar.append(input);
            input.select();
            try {
                copied = document.execCommand("copy");
            } catch (_) {}
            input.remove();
            focused?.focus({ preventScroll: true });
        }
        return copied;
    }

    async function copyLink() {
        const copied = await copyText(versionURL().href);
        bar.querySelector(".study-message").textContent = copied
            ? "Link copied. It includes the backdrop, frame, reveal, theme and settings."
            : "Copy the address from your browser. It includes this version and all your settings.";
    }

    function isMix(mix) {
        return ["version", "frame", "reveal", ...Object.keys(limits)].every(
            (key) => mix[key] === state[key],
        );
    }

    function mixName() {
        const named = Object.values(details.mixes).find(isMix);
        return named
            ? `${named.letter} · ${named.name}`
            : `${presets[state.version].name} / ${details.frames[state.frame].name} / ${details.reveals[state.reveal].name}`;
    }

    function panel(name) {
        media.stopPreviews();
        for (const section of bar.querySelectorAll("[data-study-panel]"))
            section.hidden = section.dataset.studyPanel !== name;
        for (const button of bar.querySelectorAll("[data-study-pane]"))
            button.setAttribute("aria-pressed", String(button.dataset.studyPane === name));
        bar.querySelector(".study-gallery").scrollTop = 0;
        media.refresh();
    }

    function closeGallery() {
        const gallery = bar.querySelector(".study-browse");
        if (!gallery.open) return;
        media.stopPreviews();
        gallery.open = false;
        gallery.querySelector("summary").focus({ preventScroll: true });
    }

    function replay() {
        closeGallery();
        bar.querySelector(".study-adjust").open = false;
        const target = document.querySelector(
            "main .hub-hero__photo, main .post-hero, main .media-frame[data-image-frame]",
        );
        if (target) {
            const box = target.getBoundingClientRect();
            const top = bar.getBoundingClientRect().bottom + 18;
            if (box.top < top || box.top >= innerHeight)
                window.scrollTo({ top: scrollY + box.top - top, behavior: "instant" });
        }
        const count = media.replay();
        const message = !media.motionAllowed()
            ? "Motion effects are off to respect your display preferences."
            : state.reveal === "still"
              ? "Immediate: images appear without an entrance effect."
              : count
                ? "Image entrance replayed."
                : "The entrance will play when the image has loaded.";
        bar.querySelector(".study-replay-status").textContent = message;
        bar.querySelector("[data-study-replay]").title = message;
    }

    function readVotes() {
        const result = { backgrounds: {}, frames: {}, reveals: {}, mixes: [], note: "" };
        try {
            const saved = JSON.parse(localStorage.getItem(voteKey));
            if (!saved || typeof saved !== "object") return result;
            for (const [group, catalog] of [
                ["backgrounds", presets],
                ["frames", details.frames],
                ["reveals", details.reveals],
            ]) {
                for (const key of Object.keys(catalog)) {
                    const rating = saved[group]?.[key];
                    if (["love", "maybe", "pass"].includes(rating)) result[group][key] = rating;
                }
            }
            if (typeof saved.note === "string") result.note = saved.note.slice(0, 2000);
            if (Array.isArray(saved.mixes)) {
                for (const item of saved.mixes.slice(0, 24)) {
                    if (typeof item?.name !== "string" || typeof item?.url !== "string") continue;
                    const url = new URL(item.url, location.origin);
                    if (url.origin === location.origin && url.pathname.startsWith("/opt/"))
                        result.mixes.push({ name: item.name.slice(0, 200), url: url.href });
                }
            }
        } catch (_) {}
        return result;
    }

    function voteSummary() {
        const lines = ["Website design votes"];
        for (const [group, title, catalog] of [
            ["backgrounds", "Backdrops", presets],
            ["frames", "Image frames", details.frames],
            ["reveals", "Image reveals", details.reveals],
        ]) {
            const choices = Object.entries(votes[group]).map(
                ([key, rating]) => `${catalog[key].name}: ${rating}`,
            );
            if (choices.length) lines.push(`${title} — ${choices.join("; ")}`);
        }
        if (votes.mixes.length) {
            lines.push("", "Saved mixes:");
            for (const item of votes.mixes) lines.push(`${item.name}\n${item.url}`);
        }
        if (votes.note.trim()) lines.push("", `Notes: ${votes.note.trim()}`);
        lines.push("", `Current preview: ${versionURL().href}`);
        return lines.join("\n");
    }

    function saveVotes() {
        try {
            localStorage.setItem(voteKey, JSON.stringify(votes));
        } catch (_) {
            bar.querySelector(".study-vote-status").textContent =
                "Browser storage is unavailable. Copy your votes before leaving this page.";
        }
        renderVotes();
    }

    function renderVotes() {
        if (!votes) return;
        const selected = { backgrounds: state.version, frames: state.frame, reveals: state.reveal };
        const catalogs = { backgrounds: presets, frames: details.frames, reveals: details.reveals };
        for (const [group, key] of Object.entries(selected)) {
            bar.querySelector(`[data-vote-name="${group}"]`).textContent =
                catalogs[group][key].name;
            for (const button of bar.querySelectorAll(`[data-vote-group="${group}"] [data-rating]`))
                button.setAttribute(
                    "aria-pressed",
                    String(votes[group][key] === button.dataset.rating),
                );
        }
        const count = ["backgrounds", "frames", "reveals"].reduce(
            (total, group) => total + Object.keys(votes[group]).length,
            0,
        );
        bar.querySelector("[data-vote-count]").textContent = count + votes.mixes.length;
        bar.querySelector("#study-vote-export").value = voteSummary();
        const list = bar.querySelector(".study-saved-mixes");
        // Preserve keyboard focus while changing a rating or typing a note.
        const signature = JSON.stringify(votes.mixes);
        if (list.dataset.signature === signature) return;
        list.dataset.signature = signature;
        list.replaceChildren();
        for (const [index, item] of votes.mixes.entries()) {
            const row = document.createElement("li");
            const link = document.createElement("a");
            link.href = item.url;
            link.dataset.savedMix = "";
            link.textContent = item.name;
            const remove = document.createElement("button");
            remove.type = "button";
            remove.textContent = "Remove";
            remove.setAttribute("aria-label", `Remove saved mix ${item.name}`);
            remove.addEventListener("click", () => {
                votes.mixes.splice(index, 1);
                saveVotes();
                bar.querySelector("[data-save-mix]").focus();
            });
            row.append(link, remove);
            list.append(row);
        }
    }

    function initDetails() {
        votes = readVotes();
        bar.querySelector("#study-vote-note").value = votes.note;
        for (const button of bar.querySelectorAll("[data-study-pane]"))
            button.addEventListener("click", () => panel(button.dataset.studyPane));
        for (const key of ["frame", "reveal", "mix"]) {
            for (const button of bar.querySelectorAll(`[data-${key}]`)) {
                button.addEventListener("click", () => {
                    if (key === "mix") {
                        const mix = details.mixes[button.dataset.mix];
                        state = Object.fromEntries(
                            ["version", "frame", "reveal", ...Object.keys(limits)].map((name) => [
                                name,
                                mix[name],
                            ]),
                        );
                    } else state[key] = button.dataset[key];
                    render();
                    closeGallery();
                    if (key !== "frame") replay();
                });
                if (key === "reveal") {
                    const preview = () =>
                        media.preview(
                            button.querySelector(".study-media-preview"),
                            button.dataset.reveal,
                        );
                    button.addEventListener("pointerenter", preview);
                    button.addEventListener("focus", preview);
                }
            }
        }
        bar.querySelector("[data-study-replay]").addEventListener("click", replay);
        bar.querySelector("[data-study-open-votes]").addEventListener("click", () => {
            bar.querySelector(".study-adjust").open = false;
            bar.querySelector(".study-browse").open = true;
            panel("votes");
            bar.querySelector('[data-study-pane="votes"]').focus({ preventScroll: true });
        });
        for (const group of bar.querySelectorAll("[data-vote-group]")) {
            for (const button of group.querySelectorAll("[data-rating]"))
                button.addEventListener("click", () => {
                    const category = group.dataset.voteGroup;
                    const key = {
                        backgrounds: state.version,
                        frames: state.frame,
                        reveals: state.reveal,
                    }[category];
                    if (votes[category][key] === button.dataset.rating) delete votes[category][key];
                    else votes[category][key] = button.dataset.rating;
                    saveVotes();
                });
        }
        bar.querySelector("[data-save-mix]").addEventListener("click", () => {
            const url = versionURL().href;
            const message = bar.querySelector(".study-vote-status");
            if (votes.mixes.some((item) => item.url === url))
                message.textContent = "This exact mix is already saved.";
            else if (votes.mixes.length >= 24)
                message.textContent = "You have 24 saved mixes. Remove one to make room.";
            else {
                votes.mixes.push({
                    name: `${mixName()} · ${root.dataset.theme === "light" ? "Day" : "Night"}`,
                    url,
                });
                message.textContent = "Mix saved. Copy your votes to share it in our conversation.";
                saveVotes();
            }
        });
        bar.querySelector("#study-vote-note").addEventListener("input", (event) => {
            votes.note = event.target.value;
            saveVotes();
        });
        bar.querySelector("[data-copy-votes]").addEventListener("click", async () => {
            const copied = await copyText(voteSummary());
            bar.querySelector(".study-vote-status").textContent = copied
                ? "Votes and links copied. Paste them into our conversation."
                : "Select and copy the text in the box below, then paste it into our conversation.";
            if (!copied) {
                const text = bar.querySelector("#study-vote-export");
                text.focus();
                text.select();
            }
        });
        bar.querySelector(".study-browse").addEventListener("toggle", () => {
            if (bar.querySelector(".study-browse").open) media.refresh();
            else media.stopPreviews();
        });
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
        media.init();
        initDetails();
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
            delegatingTheme = true;
            try {
                document.querySelector("[data-theme-toggle]").click();
            } finally {
                delegatingTheme = false;
            }
        });
        new MutationObserver(() => {
            syncTheme();
            renderVotes();
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
            if (!delegatingTheme && !bar.contains(event.target))
                for (const drawer of drawers) drawer.open = false;
            const link = event.target.closest('a[href^="/opt/"]');
            if (link && !link.hasAttribute("data-saved-mix")) link.href = versionURL(link.href);
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
