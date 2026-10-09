(function () {
    "use strict";

    var dialog = document.getElementById("console");
    var toggle = document.getElementById("console-toggle");
    if (!dialog || !toggle || typeof dialog.showModal !== "function") return;

    var output = document.getElementById("console-body");
    var form = document.getElementById("console-form");
    var input = document.getElementById("console-input");
    var suggestions = document.getElementById("console-suggestions");
    var runButton = form.querySelector("button");
    var history = [];
    var historyIndex = 0;
    var draft = "";
    var commandCount = 0;
    var previousFocus = null;
    var indexPromise = null;
    var searchIndex = null;
    var completions = [];
    var telemetryState = null;
    var initialized = false;
    var commands = ["help", "find", "goto", "session", "telemetry", "clear", "close"];
    var aliases = {
        overview: "/",
        home: "/",
        pro: "/pro/",
        research: "/pro/",
        personal: "/personal/",
        projects: "/personal/",
        lab: "/lab/",
        publications: "/pro/publications/",
        about: "/pro/about/",
        privacy: "/privacy/",
        cv: "/pro/about/jonas-mehtali-resume.pdf",
    };
    var shortcuts = [
        { t: "Overview", u: "/", d: "Jonas Mehtali — research and projects", g: [] },
        { t: "Professional", u: "/pro/", d: "Research, publications and experience", g: [] },
        { t: "Personal", u: "/personal/", d: "Games, 3D art and tools", g: [] },
        { t: "The Lab", u: "/lab/", d: "Interactive experiments", g: [] },
        { t: "Publications", u: "/pro/publications/", d: "Papers and research", g: [] },
        { t: "About", u: "/pro/about/", d: "Background and CV", g: [] },
        { t: "Privacy", u: "/privacy/", d: "Site telemetry and your controls", g: [] },
        { t: "CV (PDF)", u: aliases.cv, d: "Download the CV", g: [] },
    ];

    function element(tag, text, className) {
        var node = document.createElement(tag);
        if (text !== undefined) node.textContent = text;
        if (className) node.className = className;
        return node;
    }

    function scrollToLatest() {
        output.scrollTop = output.scrollHeight;
    }

    function entry(command, className) {
        var group = element(
            "div",
            undefined,
            "console__entry" + (className ? " " + className : ""),
        );
        if (command) {
            var heading = element("p", undefined, "console__command");
            heading.appendChild(element("code", command));
            group.appendChild(heading);
        }
        var response = element("div", undefined, "console__response");
        group.appendChild(response);
        output.appendChild(group);
        while (output.children.length > 60) output.firstElementChild.remove();
        return response;
    }

    function say(target, text, emphasis) {
        if (!target.isConnected) return;
        target.appendChild(element("p", text, emphasis ? "console__emphasis" : ""));
        scrollToLatest();
    }

    function action(target, label, command) {
        var button = element("button", label, "console__action");
        button.type = "button";
        button.dataset.command = command;
        target.appendChild(button);
    }

    function normalize(text) {
        return text
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")
            .toLowerCase();
    }

    function internalURL(path) {
        if (!path || /^[a-z][a-z0-9+.-]*:/i.test(path) || /^\/\//.test(path) || /\\/.test(path))
            return null;
        try {
            var url = new URL(path.charAt(0) === "/" ? path : "/" + path, location.origin);
            return url.origin === location.origin ? url : null;
        } catch (error) {
            return null;
        }
    }

    function loadIndex() {
        if (indexPromise) return indexPromise;
        var controller = new AbortController();
        var timeout = setTimeout(function () {
            controller.abort();
        }, 8000);
        indexPromise = fetch("/searchindex.json", { signal: controller.signal })
            .then(function (response) {
                if (!response.ok) throw new Error("Search index unavailable");
                return response.json();
            })
            .then(function (items) {
                if (!Array.isArray(items)) throw new Error("Invalid search index");
                var pages = new Map();
                shortcuts.concat(items).forEach(function (page) {
                    if (!page || typeof page.t !== "string" || typeof page.u !== "string") return;
                    var url = internalURL(page.u);
                    if (!url) return;
                    pages.set(url.pathname, {
                        t: page.t,
                        u: url.pathname,
                        d: typeof page.d === "string" ? page.d : "",
                        g: Array.isArray(page.g)
                            ? page.g.filter(function (tag) {
                                  return typeof tag === "string";
                              })
                            : [],
                    });
                });
                searchIndex = Array.from(pages.values());
                return searchIndex;
            })
            .catch(function (error) {
                indexPromise = null;
                throw error;
            })
            .finally(function () {
                clearTimeout(timeout);
            });
        return indexPromise;
    }

    function resultList(target, pages) {
        var list = element("ul", undefined, "console__results");
        pages.forEach(function (page) {
            var item = element("li");
            var link = element("a", undefined, "console__result");
            link.href = page.u;
            link.appendChild(element("strong", page.t));
            if (page.d) link.appendChild(element("span", page.d));
            link.appendChild(element("small", page.u));
            item.appendChild(link);
            list.appendChild(item);
        });
        target.appendChild(list);
    }

    function help(target) {
        var rows = [
            ["find <words>", "Search titles, descriptions and tags. Try find games."],
            ["goto <page>", "Open a page. Try goto pro, goto lab or goto /personal/."],
            ["session", "Show this page, theme and console session."],
            ["telemetry", "Check site telemetry and change your browser preference."],
            ["clear", "Clear console output and command history."],
            ["close", "Close the console. Escape works too."],
            ["help", "Show these commands."],
        ];
        var list = element("dl", undefined, "console__help");
        rows.forEach(function (row) {
            var term = element("dt");
            term.appendChild(element("code", row[0]));
            list.appendChild(term);
            list.appendChild(element("dd", row[1]));
        });
        target.appendChild(list);
    }

    function telemetry(target) {
        document.dispatchEvent(new CustomEvent("jm:telemetry-request"));
        if (!telemetryState) {
            say(target, "Telemetry status is unavailable. See the privacy page for details.");
        } else {
            if (!telemetryState.configured) {
                say(
                    target,
                    "Site telemetry is not configured for this build. No telemetry events are sent.",
                    true,
                );
            } else if (telemetryState.dnt) {
                say(target, "Site telemetry is off because your browser sends Do Not Track.", true);
            } else {
                say(
                    target,
                    telemetryState.active
                        ? "Site telemetry is on for this browser."
                        : "Site telemetry is off for this browser.",
                    true,
                );
            }
            say(
                target,
                "Your " +
                    (telemetryState.persistent ? "saved" : "current") +
                    " preference: " +
                    (telemetryState.optedOut ? "off." : "allow telemetry when configured."),
            );
            if (!telemetryState.persistent)
                say(target, "Browser storage is unavailable. Changes apply only to this page.");
            if (!telemetryState.optedOut) action(target, "Turn telemetry off", "telemetry off");
            else if (!telemetryState.dnt) action(target, "Allow telemetry", "telemetry on");
        }
        var paragraph = element("p");
        var link = element("a", "Read the privacy details");
        link.href = "/privacy/";
        paragraph.appendChild(link);
        target.appendChild(paragraph);
    }

    function find(query, target) {
        if (!query) {
            say(target, "Add a search term. For example: find games");
            return;
        }
        say(target, "Searching the site…");
        loadIndex()
            .then(function (pages) {
                if (!target.isConnected) return;
                target.replaceChildren();
                var terms = normalize(query).split(/\s+/);
                var matches = pages
                    .map(function (page) {
                        var title = normalize(page.t);
                        var tags = normalize(page.g.join(" "));
                        var text = title + " " + tags + " " + normalize(page.d);
                        if (
                            !terms.every(function (term) {
                                return text.includes(term);
                            })
                        )
                            return null;
                        var score = terms.reduce(function (sum, term) {
                            return sum + (title.includes(term) ? 10 : tags.includes(term) ? 4 : 1);
                        }, 0);
                        return { page: page, score: score };
                    })
                    .filter(Boolean)
                    .sort(function (a, b) {
                        return b.score - a.score || a.page.t.localeCompare(b.page.t);
                    });
                if (!matches.length) {
                    say(
                        target,
                        "No pages found for “" + query + "”. Try fewer words or a different topic.",
                    );
                    return;
                }
                say(
                    target,
                    matches.length +
                        " matching " +
                        (matches.length === 1 ? "page" : "pages") +
                        (matches.length > 8
                            ? "; showing the first 8. Refine your search for more."
                            : "."),
                );
                resultList(
                    target,
                    matches.slice(0, 8).map(function (match) {
                        return match.page;
                    }),
                );
                /* Start at the first result; long result lists remain keyboard- and touch-scrollable. */
                output.scrollTop = target.parentElement.offsetTop - output.offsetTop;
            })
            .catch(function () {
                if (!target.isConnected) return;
                target.replaceChildren();
                say(
                    target,
                    "Search is unavailable right now. Check your connection and try again.",
                );
                action(target, "Try again", "find " + query);
            });
    }

    function navigate(path, target) {
        if (!path) {
            say(target, "Choose a page. For example: goto pro or goto /personal/");
            return;
        }
        var url = internalURL(aliases[path.toLowerCase()] || path);
        if (!url) {
            say(
                target,
                "Use a page on this site, such as /pro/. External URLs are not console commands.",
            );
            return;
        }
        function match(pages) {
            return pages.find(function (page) {
                return page.u.replace(/\/$/, "") === url.pathname.replace(/\/$/, "");
            });
        }
        function open(page) {
            if (!target.isConnected) return;
            say(target, "Opening " + page.t + "…");
            location.assign(page.u + url.search + url.hash);
        }
        var known = match(shortcuts);
        if (known) {
            open(known);
            return;
        }
        say(target, "Checking that page…");
        loadIndex()
            .then(function (pages) {
                if (!target.isConnected) return;
                target.replaceChildren();
                var page = match(pages);
                if (page) open(page);
                else {
                    say(
                        target,
                        "No page at “" + url.pathname + "”. Use find to search by title or topic.",
                    );
                    action(target, "Show commands", "help");
                }
            })
            .catch(function () {
                if (!target.isConnected) return;
                target.replaceChildren();
                say(
                    target,
                    "Could not check that page. Try again, or use goto pro, goto personal or goto lab.",
                );
            });
    }

    function execute(raw) {
        raw = raw.trim();
        if (!raw) return;
        input.value = "";
        draft = "";
        commandCount += 1;
        if (history[history.length - 1] !== raw) history.push(raw);
        if (history.length > 100) history.shift();
        historyIndex = history.length;
        updateSuggestions();
        var space = raw.search(/\s/);
        var command = (space === -1 ? raw : raw.slice(0, space)).toLowerCase();
        var argument = space === -1 ? "" : raw.slice(space).trim();
        var target = entry(raw);

        if (["help", "session", "clear", "close"].includes(command) && argument) {
            say(target, command + " does not need an argument.");
        } else if (command === "help") {
            help(target);
        } else if (command === "find") {
            find(argument, target);
        } else if (command === "goto") {
            navigate(argument, target);
        } else if (command === "session") {
            say(target, document.title, true);
            say(target, "Page: " + location.pathname);
            say(
                target,
                "Theme: " + (document.documentElement.dataset.theme === "light" ? "light" : "dark"),
            );
            say(
                target,
                "Commands run on this page: " +
                    commandCount +
                    ". History ends when you leave this page.",
            );
        } else if (command === "telemetry") {
            var mode = argument.toLowerCase();
            if (mode && !["on", "off", "status"].includes(mode)) {
                say(
                    target,
                    "Use telemetry to check the status, telemetry off to opt out, or telemetry on to allow it.",
                );
            } else {
                if (mode === "off" || mode === "on") {
                    document.dispatchEvent(
                        new CustomEvent("jm:telemetry-request", {
                            detail: { enabled: mode === "on" },
                        }),
                    );
                    if (mode === "off" && telemetryState) {
                        say(
                            target,
                            telemetryState.identifiersCleared
                                ? "Unsent events and this browser’s telemetry IDs have been cleared. Previously sent events are not deleted."
                                : "Unsent events have been cleared. Browser storage prevented removal of saved IDs. Previously sent events are not deleted.",
                        );
                    }
                }
                telemetry(target);
            }
        } else if (command === "clear") {
            output.replaceChildren();
            history = [];
            historyIndex = 0;
            commandCount = 0;
            try {
                localStorage.removeItem("jm.console.v1");
            } catch (error) {
                /* Remove legacy console memory when available. */
            }
            say(
                entry("", "console__cleared"),
                "Console output and history cleared. Theme and telemetry preferences are unchanged.",
            );
        } else if (command === "close") {
            dialog.close();
        } else {
            say(
                target,
                "Unknown command “" +
                    command +
                    "”. Use help for the command list, or find to search the site.",
            );
            action(target, "Search for “" + raw + "”", "find " + raw);
        }
        scrollToLatest();
        if (dialog.open) input.focus({ preventScroll: true });
    }

    function updateSuggestions() {
        var value = input.value.trimStart();
        runButton.disabled = !value.trim();
        completions = [];
        if (value && !/\s/.test(value)) {
            completions = commands.filter(function (command) {
                return command.startsWith(value.toLowerCase()) && command !== value.toLowerCase();
            });
        } else if (/^goto\s/i.test(value)) {
            var fragment = value.replace(/^goto\s+/i, "").toLowerCase();
            var pages = searchIndex || shortcuts;
            completions = pages
                .filter(function (page) {
                    return page.u.toLowerCase().startsWith(fragment) && page.u !== fragment;
                })
                .map(function (page) {
                    return "goto " + page.u;
                })
                .slice(0, 5);
        } else if (/^telemetry\s/i.test(value)) {
            completions = ["telemetry on", "telemetry off", "telemetry status"].filter(
                function (command) {
                    return (
                        command.startsWith(value.toLowerCase()) && command !== value.toLowerCase()
                    );
                },
            );
        }
        suggestions.replaceChildren();
        completions.forEach(function (completion) {
            var button = element("button", completion);
            button.type = "button";
            button.dataset.complete = completion;
            button.setAttribute("aria-label", "Complete: " + completion);
            suggestions.appendChild(button);
        });
        suggestions.hidden = !completions.length;
    }

    function complete(value) {
        input.value = value + (["find", "goto", "telemetry"].includes(value) ? " " : "");
        draft = input.value;
        historyIndex = history.length;
        input.focus({ preventScroll: true });
        updateSuggestions();
    }

    function fitViewport() {
        if (!dialog.open || !window.visualViewport) return;
        var viewport = window.visualViewport;
        var margin = window.innerWidth <= 540 ? 12 : 20;
        dialog.classList.toggle("console--compact", viewport.height < 500);
        dialog.classList.toggle("console--tiny", viewport.height < 320);
        dialog.style.setProperty("--console-viewport-height", viewport.height + "px");
        dialog.style.setProperty(
            "--console-bottom",
            Math.max(margin, window.innerHeight - viewport.height - viewport.offsetTop + margin) +
                "px",
        );
    }

    function openConsole() {
        if (dialog.open) return;
        previousFocus = document.activeElement;
        if (!initialized) {
            var welcome = entry("", "console__welcome");
            say(welcome, "Explore the site from here.", true);
            say(
                welcome,
                "Search with find, open a page with goto, or choose Help for all commands.",
            );
            initialized = true;
        }
        dialog.showModal();
        dialog.classList.add("is-open");
        document.body.classList.add("console-open");
        toggle.setAttribute("aria-expanded", "true");
        fitViewport();
        input.focus({ preventScroll: true });
    }

    document.addEventListener("jm:telemetry-status", function (event) {
        telemetryState = event.detail;
    });
    toggle.hidden = false;
    updateSuggestions();
    toggle.addEventListener("click", openConsole);
    dialog.querySelector("[data-console-close]").addEventListener("click", function () {
        dialog.close();
    });
    dialog.addEventListener("close", function () {
        dialog.classList.remove("is-open");
        document.body.classList.remove("console-open");
        toggle.setAttribute("aria-expanded", "false");
        if (previousFocus && previousFocus.isConnected)
            previousFocus.focus({ preventScroll: true });
    });

    var backdropPressed = false;
    dialog.addEventListener("pointerdown", function (event) {
        backdropPressed = event.target === dialog;
    });
    dialog.addEventListener("click", function (event) {
        if (backdropPressed && event.target === dialog) dialog.close();
        backdropPressed = false;
        var commandButton = event.target.closest("[data-command]");
        var completeButton = event.target.closest("[data-complete]");
        if (commandButton) execute(commandButton.dataset.command);
        else if (completeButton) complete(completeButton.dataset.complete);
    });

    document.addEventListener("keydown", function (event) {
        if (
            event.defaultPrevented ||
            event.isComposing ||
            event.repeat ||
            event.ctrlKey ||
            event.metaKey ||
            event.altKey
        )
            return;
        var target = event.target;
        var typing = target.matches("input, textarea, select") || target.isContentEditable;
        if ((event.key === "~" || event.key === "`") && !typing && !dialog.open) {
            event.preventDefault();
            openConsole();
        }
    });
    form.addEventListener("submit", function (event) {
        event.preventDefault();
        execute(input.value);
    });
    input.addEventListener("input", function () {
        draft = input.value;
        historyIndex = history.length;
        updateSuggestions();
        if (/^goto\s/i.test(input.value) && !searchIndex)
            loadIndex()
                .then(updateSuggestions)
                .catch(function () {
                    /* Core shortcuts still work offline. */
                });
    });
    input.addEventListener("keydown", function (event) {
        if (event.isComposing || event.ctrlKey || event.metaKey || event.altKey) return;
        if ((event.key === "ArrowUp" || event.key === "ArrowDown") && history.length) {
            event.preventDefault();
            historyIndex = Math.max(
                0,
                Math.min(history.length, historyIndex + (event.key === "ArrowUp" ? -1 : 1)),
            );
            input.value = historyIndex === history.length ? draft : history[historyIndex];
            input.setSelectionRange(input.value.length, input.value.length);
            updateSuggestions();
        } else if (
            event.key === "ArrowRight" &&
            completions.length === 1 &&
            input.selectionStart === input.value.length &&
            input.selectionEnd === input.value.length
        ) {
            event.preventDefault();
            complete(completions[0]);
        }
    });
    if (window.visualViewport) {
        window.visualViewport.addEventListener("resize", fitViewport);
        window.visualViewport.addEventListener("scroll", fitViewport);
    }
})();
