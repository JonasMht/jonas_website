/* Procedural image entrances. Sources stay intact; every temporary layer is disposable.
 * Canvas pixel scaling: https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/imageSmoothingEnabled
 * Colour tables: https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/feComponentTransfer
 */
window.StudyEffects = (function () {
    "use strict";

    const ns = "http://www.w3.org/2000/svg";
    const durations = { pixel: 1000, print: 1200, spectral: 960, blueprint: 1050, broadcast: 1100 };

    function svg(tag, attributes = {}) {
        const element = document.createElementNS(ns, tag);
        for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
        return element;
    }

    function install(tones) {
        const root = svg("svg", {
            class: "study-colour-defs",
            "aria-hidden": "true",
            focusable: "false",
            width: 0,
            height: 0,
        });
        const defs = svg("defs");
        for (const [key, tone] of Object.entries(tones)) {
            if (!tone.colors) continue;
            const filter = svg("filter", {
                id: `study-tone-${key}`,
                "color-interpolation-filters": "sRGB",
                x: "0%",
                y: "0%",
                width: "100%",
                height: "100%",
            });
            filter.append(svg("feColorMatrix", { type: "saturate", values: "0" }));
            const transfer = svg("feComponentTransfer");
            ["R", "G", "B"].forEach((channel, index) => {
                const values = tone.colors.map((color) =>
                    (parseInt(color.slice(index * 2 + 1, index * 2 + 3), 16) / 255).toFixed(5),
                );
                transfer.append(
                    svg(`feFunc${channel}`, {
                        type: tone.discrete ? "discrete" : "table",
                        tableValues: values.join(" "),
                    }),
                );
            });
            filter.append(transfer);
            defs.append(filter);
        }
        root.append(defs);
        document.body.append(root);
    }

    function toneFilter(tone) {
        return tone === "natural" ? "none" : `url("#study-tone-${tone}")`;
    }

    function applyTone(record, tone, highContrast = false) {
        // Only editorial header portraits receive lasting colour grades.
        const chosen = record.preview
            ? record.element.dataset.tonePreview || tone
            : record.element.matches(".hub-hero__photo")
              ? tone
              : "natural";
        record.element.dataset.imageTone = chosen;
        record.image.classList.add("study-filtered-image");
        record.image.style.setProperty(
            "--study-photo-filter",
            highContrast ? "none" : toneFilter(chosen),
        );
    }

    function animate(record, target, frames, timing) {
        const animation = target.animate(frames, timing);
        record.animations.push(animation);
        return animation;
    }

    function overlay(record) {
        const layer = document.createElement("span");
        const image = record.image;
        const box = image.getBoundingClientRect();
        const parent = record.element.getBoundingClientRect();
        layer.className = "study-image-effect";
        layer.setAttribute("aria-hidden", "true");
        layer.style.cssText = `left:${box.left - parent.left - record.element.clientLeft}px;top:${box.top - parent.top - record.element.clientTop}px;width:${box.width}px;height:${box.height}px;border-radius:${getComputedStyle(image).borderRadius}`;
        record.element.append(layer);
        record.layers.push(layer);
        return layer;
    }

    function cloneImage(record, parent, tone) {
        const image = document.createElement("img");
        const style = getComputedStyle(record.image);
        image.src = record.image.currentSrc || record.image.src;
        image.alt = "";
        image.setAttribute("aria-hidden", "true");
        image.style.objectFit = style.objectFit;
        image.style.objectPosition = style.objectPosition;
        image.style.filter = toneFilter(tone);
        parent.append(image);
        return image;
    }

    function drawFitted(context, image, width, height) {
        const style = getComputedStyle(image);
        const fit = style.objectFit;
        const iw = image.naturalWidth,
            ih = image.naturalHeight;
        if (fit !== "cover" && fit !== "contain") {
            context.drawImage(image, 0, 0, width, height);
            return;
        }
        const scale = (fit === "cover" ? Math.max : Math.min)(width / iw, height / ih);
        const position = style.objectPosition.split(" ").map((value) => {
            const numeric = Number.parseFloat(value);
            return value.endsWith("%") && Number.isFinite(numeric) ? numeric / 100 : 0.5;
        });
        context.drawImage(
            image,
            (width - iw * scale) * position[0],
            (height - ih * scale) * (position[1] ?? 0.5),
            iw * scale,
            ih * scale,
        );
    }

    function pixels(record, layer, clock) {
        const canvas = document.createElement("canvas");
        const scale = Math.min(
            devicePixelRatio,
            1200 / Math.max(layer.clientWidth, layer.clientHeight),
        );
        canvas.width = Math.max(1, Math.round(layer.clientWidth * scale));
        canvas.height = Math.max(1, Math.round(layer.clientHeight * scale));
        canvas.style.filter = toneFilter(record.element.dataset.imageTone);
        layer.append(canvas);
        const context = canvas.getContext("2d");
        const small = document.createElement("canvas");
        const source = small.getContext("2d");
        if (!context || !source) return false;
        context.imageSmoothingEnabled = false;
        const steps = [10, 14, 20, 30, 46, 70, 110, 180, 300, canvas.width];
        let previous = -1;
        function draw() {
            const progress = Math.min(1, Math.max(0, (clock.currentTime || 0) / durations.pixel));
            const index = Math.min(steps.length - 1, Math.floor(progress * steps.length));
            if (index !== previous) {
                previous = index;
                small.width = Math.min(canvas.width, steps[index]);
                small.height = Math.max(
                    1,
                    Math.round((small.width * canvas.height) / canvas.width),
                );
                drawFitted(source, record.image, small.width, small.height);
                context.clearRect(0, 0, canvas.width, canvas.height);
                context.drawImage(small, 0, 0, canvas.width, canvas.height);
                canvas.dataset.pixelColumns = small.width;
            }
            if (clock.playState === "running" || clock.pending)
                record.raf = requestAnimationFrame(draw);
        }
        draw();
        return true;
    }

    function print(record, layer, duration) {
        layer.classList.add("study-effect-print");
        const photo = cloneImage(record, layer, "press");
        animate(
            record,
            photo,
            [
                { clipPath: "polygon(0 0, 0 0, 0 100%, 0 100%)" },
                { clipPath: "polygon(0 0, 100% 0, 100% 100%, 0 100%)" },
            ],
            { duration: duration * 0.65, fill: "both", easing: "cubic-bezier(.16,.6,.3,1)" },
        );
        const dots = document.createElement("span");
        dots.className = "study-print-dots";
        layer.append(dots);
        for (const [index, colour] of ["#4db3ea", "#26327f"].entries()) {
            const ink = document.createElement("span");
            ink.className = "study-ink-pass";
            ink.style.background = colour;
            layer.append(ink);
            animate(
                record,
                ink,
                [
                    { transform: "translateX(-250%) skewX(-18deg)" },
                    { transform: "translateX(500%) skewX(-18deg)" },
                ],
                {
                    duration: duration * 0.8,
                    delay: index * 90,
                    fill: "both",
                    easing: "cubic-bezier(.2,.55,.3,1)",
                },
            );
        }
    }

    function spectral(record, layer, duration) {
        layer.classList.add("study-effect-spectral");
        for (const [index, tone] of ["prism", "cobalt"].entries()) {
            const photo = cloneImage(record, layer, tone);
            photo.style.mixBlendMode = index ? "screen" : "normal";
            animate(
                record,
                photo,
                [
                    {
                        transform: `translateX(${index ? -7 : 7}%)`,
                        opacity: 0.2,
                        clipPath: "polygon(65% 0, 65% 0, 35% 100%, 35% 100%)",
                    },
                    { opacity: index ? 0.65 : 1, offset: 0.25 },
                    {
                        transform: "translateX(0)",
                        opacity: index ? 0.35 : 1,
                        clipPath: "polygon(0 0, 100% 0, 100% 100%, 0 100%)",
                    },
                ],
                { duration: duration * 0.8, fill: "both", easing: "cubic-bezier(.16,.7,.25,1)" },
            );
        }
    }

    function blueprint(record, layer, duration) {
        cloneImage(record, layer, "cobalt");
        const grid = document.createElement("span");
        grid.className = "study-exposure-grid";
        layer.append(grid);
        animate(
            record,
            layer,
            [{ clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0 0 0)" }],
            { duration: duration * 0.72, fill: "both", easing: "cubic-bezier(.25,.55,.3,1)" },
        );
        const line = document.createElement("span");
        line.className = "study-exposure-line";
        layer.append(line);
        animate(
            record,
            line,
            [{ transform: "translateX(0)" }, { transform: `translateX(${layer.clientWidth}px)` }],
            { duration: duration * 0.72, fill: "both", easing: "cubic-bezier(.25,.55,.3,1)" },
        );
    }

    function broadcast(record, layer, duration) {
        layer.classList.add("study-effect-print");
        const strips = 6;
        for (let index = 0; index < strips; index++) {
            const tone = record.element.dataset.imageTone;
            const image = cloneImage(record, layer, tone === "natural" ? "press" : tone);
            image.style.clipPath = `inset(${(index * 100) / strips}% 0 ${((strips - index - 1) * 100) / strips}% 0)`;
            animate(
                record,
                image,
                [
                    { transform: `translateX(${index % 2 ? 45 : -45}%)`, opacity: 0 },
                    { transform: "translateX(0)", opacity: 1 },
                ],
                {
                    duration: duration * 0.52,
                    delay: index * 38,
                    fill: "both",
                    easing: "cubic-bezier(.12,.7,.2,1)",
                },
            );
        }
    }

    function play(record, chosen) {
        if (!Object.hasOwn(durations, chosen)) return null;
        const duration = durations[chosen];
        const layer = overlay(record);
        const clock = animate(
            record,
            layer,
            [
                { opacity: 1, offset: 0 },
                { opacity: 1, offset: 0.75 },
                { opacity: 0, offset: 1 },
            ],
            { duration, easing: "linear" },
        );
        animate(
            record,
            record.image,
            [
                { opacity: 0, offset: 0 },
                { opacity: 0, offset: 0.65 },
                { opacity: 1, offset: 0.9 },
                { opacity: 1, offset: 1 },
            ],
            { duration, easing: "linear" },
        );
        if (chosen === "pixel") {
            if (!pixels(record, layer, clock)) return null;
        } else if (chosen === "print") print(record, layer, duration);
        else if (chosen === "spectral") spectral(record, layer, duration);
        else if (chosen === "blueprint") blueprint(record, layer, duration);
        else broadcast(record, layer, duration);
        return clock;
    }

    function cancel(record) {
        cancelAnimationFrame(record.raf);
        record.raf = null;
        for (const layer of record.layers) layer.remove();
        record.layers = [];
    }

    return { install, applyTone, play, cancel };
})();
