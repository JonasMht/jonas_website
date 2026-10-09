/* Image experiments for the private study. Each entrance settles to the chosen colour. */
window.StudyMedia = (function () {
    "use strict";

    const ns = "http://www.w3.org/2000/svg";
    const reduced = matchMedia("(prefers-reduced-motion: reduce)");
    const contrast = matchMedia("(forced-colors: active), (prefers-contrast: more)");
    const records = [];
    const effects = window.StudyEffects;
    let frame = "corners";
    let reveal = "still";
    let tone = "natural";
    let observer;
    let resize;

    function svgElement(name, attributes) {
        const element = document.createElementNS(ns, name);
        for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
        return element;
    }

    function ornament(record) {
        const kind = record.element.dataset.framePreview || frame;
        record.element.dataset.imageFrame = kind;
        // Original brackets remain the CSS fallback if script or SVG is unavailable.
        record.svg.toggleAttribute("hidden", kind === "corners");
        if (kind === "corners") return;
        const w = record.element.clientWidth + 12;
        const h = record.element.clientHeight + 12;
        if (w <= 12 || h <= 12) return;
        record.svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
        const r = w - 1,
            b = h - 1;
        let base = "",
            line = "",
            tip = "";
        if (kind === "rails") {
            base = `M1 20V${b - 20}M${r} 20V${b - 20}M45 1H${r - 45}M45 ${b}H${r - 45}`;
            line = `M1 22V1H${Math.min(w * 0.36, 90)}M${r - Math.min(w * 0.36, 90)} ${b}H${r}V${b - 22}`;
            for (let x = 0; x < 3; x++) {
                line += `M${r - 12 - x * 7} 1v4M${13 + x * 7} ${b}v-4`;
            }
            tip = `M1 1H12M${r - 11} ${b}H${r}`;
        } else if (kind === "rails-ii") {
            const joint = Math.min(14, w * 0.1, h * 0.16);
            const run = Math.min(w * 0.46, 180);
            const stem = Math.min(44, h * 0.35);
            base = `M1 ${stem}V${joint}L${joint} 1H${r - joint}L${r} ${joint}V${b - stem}M${r} ${b - joint}L${r - joint} ${b}H${joint}L1 ${b - joint}V${stem}`;
            base += `M${joint + 5} 4H${r - joint - 5}M${joint + 5} ${b - 3}H${r - joint - 5}`;
            line = `M1 ${stem}V${joint}L${joint} 1H${run}M${r - run} ${b}H${r - joint}L${r} ${b - joint}V${b - stem}`;
            line += `M${r - 26} 1H${r - joint}L${r} ${joint}V${joint + 10}M1 ${b - joint - 10}V${b - joint}L${joint} ${b}H26`;
            tip = `M${joint + 2} 1H${joint + 13}M${r - joint - 13} ${b}H${r - joint - 2}`;
            tip += `M${run + 8} 1h4M${r - run - 12} ${b}h4`;
        } else if (kind === "bevel") {
            const c = 18;
            base = `M${c} 1H${r - c}L${r} ${c}V${b - c}L${r - c} ${b}H${c}L1 ${b - c}V${c}Z`;
            line = `M${r - 48} 1H${r - c}L${r} ${c}V48M48 ${b}H${c}L1 ${b - c}V${b - 48}`;
            tip = `M${r - c} 1L${r} ${c}M${c} ${b}L1 ${b - c}`;
        } else if (kind === "echo") {
            base = `M5 32V5H40M${r - 40} 5H${r - 5}V32M5 ${b - 32}V${b - 5}H40M${r - 40} ${b - 5}H${r - 5}V${b - 32}`;
            line = `M1 22V1H29M${r - 29} 1H${r}V22M1 ${b - 22}V${b}H29M${r - 29} ${b}H${r}V${b - 22}`;
            tip = `M1 1H9M${r - 8} ${b}H${r}`;
        } else if (kind === "arc") {
            const c = 24;
            base = `M${w / 2 - 7} 1h14M${w / 2 - 7} ${b}h14M1 ${h / 2 - 7}v14M${r} ${h / 2 - 7}v14`;
            line = `M1 ${c}Q1 1 ${c} 1M${r - c} 1Q${r} 1 ${r} ${c}M${r} ${b - c}Q${r} ${b} ${r - c} ${b}M${c} ${b}Q1 ${b} 1 ${b - c}`;
            tip = `M${w / 2} 1v4M${w / 2} ${b}v-4`;
        }
        [base, line, tip].forEach((path, index) =>
            record.svg.children[index].setAttribute("d", path),
        );
    }

    function stop(record) {
        for (const animation of record.animations) animation.cancel();
        record.animations = [];
        record.sweep?.remove();
        record.sweep = null;
        effects.cancel(record);
        record.element.removeAttribute("data-image-playing");
    }

    function play(record, chosen = reveal) {
        stop(record);
        if (!record.ready || reduced.matches || contrast.matches || chosen === "still")
            return false;
        const image = record.image;
        if (!image.clientWidth || !image.clientHeight || !image.animate) return false;
        const filter = getComputedStyle(image).filter;
        const baseFilter = filter === "none" ? "" : filter + " ";
        const full = "inset(0% 0% 0% 0%)";
        const entrances = {
            sweep: [{ clipPath: "inset(0% 0% 100% 0%)" }, { clipPath: full }],
            aperture: [
                { clipPath: "polygon(68% 0%, 68% 0%, 32% 100%, 32% 100%)" },
                { clipPath: "polygon(0% 0%, 100% 0%, 100% 100%, 0% 100%)" },
            ],
            develop: [
                { opacity: 0.25, filter: baseFilter + "blur(2px) brightness(1.18)" },
                { opacity: 1, filter },
            ],
            raster: [{ clipPath: "inset(0% 0% 100% 0%)" }, { clipPath: full }],
        };
        const duration = { sweep: 620, aperture: 540, develop: 480, raster: 600 }[chosen];
        if (!entrances[chosen]) {
            record.element.dataset.imagePlaying = chosen;
            const animation = effects.play(record, chosen);
            if (!animation) {
                stop(record);
                return false;
            }
            traceRails(record, animation.effect.getTiming().duration);
            finish(record, animation);
            return true;
        }
        const options = {
            duration,
            easing: chosen === "raster" ? "steps(12, end)" : "cubic-bezier(.22,.65,.3,1)",
        };
        record.element.dataset.imagePlaying = chosen;
        const animation = image.animate(entrances[chosen], options);
        record.animations.push(animation);
        if (chosen === "sweep") {
            const sweep = document.createElement("span");
            sweep.className = "study-load-sweep";
            sweep.setAttribute("aria-hidden", "true");
            // Follow the image bounds, including contained publication thumbnails.
            sweep.style.cssText = `left:${image.offsetLeft}px;top:${image.offsetTop}px;width:${image.clientWidth}px`;
            record.element.append(sweep);
            record.sweep = sweep;
            record.animations.push(
                sweep.animate(
                    [
                        { transform: "translateY(0)", opacity: 0 },
                        { opacity: 0.9, offset: 0.12 },
                        {
                            transform: `translateY(${Math.max(0, image.clientHeight - 2)}px)`,
                            opacity: 0,
                        },
                    ],
                    options,
                ),
            );
        }
        traceRails(record, duration);
        finish(record, animation);
        return true;
    }

    function traceRails(record, duration) {
        if (record.element.dataset.imageFrame !== "rails-ii") return;
        const line = record.svg.querySelector(".study-ornament-line");
        const length = line.getTotalLength();
        record.animations.push(
            line.animate(
                [
                    { strokeDasharray: `${length} ${length}`, strokeDashoffset: length },
                    { strokeDasharray: `${length} ${length}`, strokeDashoffset: 0 },
                ],
                { duration: Math.min(duration, 720), easing: "cubic-bezier(.22,.65,.3,1)" },
            ),
        );
    }

    function finish(record, animation) {
        // No fill mode on the controlling animation; cancellation restores the source.
        animation.finished
            .then(() => {
                if (record.animations[0] === animation) stop(record);
            })
            .catch(() => {});
    }

    function visible(record) {
        const box = record.element.getBoundingClientRect();
        const bar = document.querySelector(".study-bar").getBoundingClientRect().bottom;
        return box.width > 0 && box.bottom > bar && box.top < innerHeight;
    }

    function arrive(record) {
        record.ready = record.image.complete && record.image.naturalWidth > 0;
        record.element.dataset.imageLoad = record.ready ? "ready" : "error";
        if (record.ready && !record.preview && !record.played && visible(record)) {
            record.played = true;
            observer?.unobserve(record.element);
            play(record);
        }
        // A failed source remains the browser's accessible image/alt-text fallback.
    }

    function add(element, preview = false) {
        const image = element.querySelector("img");
        if (!image) return;
        const svg = svgElement("svg", {
            class: "study-ornament",
            "aria-hidden": "true",
            focusable: "false",
            preserveAspectRatio: "none",
        });
        for (const kind of ["base", "line", "tip"])
            svg.append(
                svgElement("path", {
                    class: `study-ornament-${kind}`,
                    "vector-effect": "non-scaling-stroke",
                }),
            );
        element.append(svg);
        const record = {
            element,
            image,
            svg,
            preview,
            ready: false,
            played: false,
            animations: [],
            layers: [],
            raf: null,
        };
        records.push(record);
        effects.applyTone(record, tone, contrast.matches);
        resize?.observe(element);
        ornament(record);
        image.addEventListener("load", () => arrive(record));
        image.addEventListener("error", () => {
            stop(record);
            arrive(record);
        });
        if (image.complete) arrive(record);
        else element.dataset.imageLoad = "waiting";
        if (!preview && !record.played) observer?.observe(element);
    }

    function init(tones) {
        effects.install(tones);
        if ("IntersectionObserver" in window)
            observer = new IntersectionObserver(
                (entries) => {
                    for (const entry of entries) {
                        if (!entry.isIntersecting) continue;
                        const record = records.find((item) => item.element === entry.target);
                        if (record?.ready && !record.played) {
                            record.played = true;
                            observer.unobserve(record.element);
                            play(record);
                        }
                    }
                },
                { threshold: 0.12 },
            );
        if ("ResizeObserver" in window)
            resize = new ResizeObserver((entries) => {
                for (const entry of entries) {
                    const record = records.find((item) => item.element === entry.target);
                    if (!record) continue;
                    const layer = record.layers[0];
                    if (
                        layer &&
                        (Math.abs(layer.clientWidth - record.image.clientWidth) > 1 ||
                            Math.abs(layer.clientHeight - record.image.clientHeight) > 1)
                    )
                        stop(record);
                    ornament(record);
                }
            });
        // Keep video controls, before/after comparisons and navigation avatars untouched.
        for (const element of document.querySelectorAll("main .media-frame")) {
            if (
                element.matches(".avatar-frame, .slider, .yt-facade") ||
                element.closest(".slider, .yt-facade")
            )
                continue;
            add(element);
        }
        for (const element of document.querySelectorAll(".study-media-preview")) {
            add(element, true);
        }
        for (const preference of [reduced, contrast])
            preference.addEventListener("change", () => {
                for (const record of records) {
                    stop(record);
                    effects.applyTone(record, tone, contrast.matches);
                }
            });
        window.addEventListener("pagehide", () => {
            for (const record of records) stop(record);
        });
        window.addEventListener("beforeprint", () => {
            for (const record of records) stop(record);
        });
        document.addEventListener("visibilitychange", () => {
            if (document.hidden) for (const record of records) stop(record);
        });
    }

    return {
        init,
        apply(nextFrame, nextReveal, nextTone) {
            const changed = frame !== nextFrame;
            const motionChanged = reveal !== nextReveal;
            const toneChanged = tone !== nextTone;
            frame = nextFrame;
            reveal = nextReveal;
            tone = nextTone;
            for (const record of records) {
                if (changed) ornament(record);
                if (motionChanged || toneChanged) stop(record);
                if (toneChanged) effects.applyTone(record, tone, contrast.matches);
            }
        },
        replay() {
            let count = 0;
            for (const record of records)
                if (!record.preview && visible(record) && play(record)) count++;
            return count;
        },
        preview(element, chosen) {
            const record = records.find((item) => item.element === element);
            if (record) play(record, chosen);
        },
        refresh() {
            for (const record of records) ornament(record);
        },
        stopPreviews() {
            for (const record of records) if (record.preview) stop(record);
        },
        motionAllowed() {
            return !reduced.matches && !contrast.matches;
        },
    };
})();
