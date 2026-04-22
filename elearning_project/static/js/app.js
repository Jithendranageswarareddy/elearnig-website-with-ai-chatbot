(() => {
    "use strict";

    const App = {};
    const state = {
        reducedMotion: window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
        desktopQuery: window.matchMedia ? window.matchMedia("(min-width: 992px)") : { matches: false }
    };

    const qs = (selector, root = document) => root.querySelector(selector);
    const qsa = (selector, root = document) => Array.from(root.querySelectorAll(selector));
    const toList = (value) => (value || "").split(",").map((part) => part.trim()).filter(Boolean);
    const toNumbers = (value) => toList(value).map((part) => Number.parseFloat(part)).filter((num) => Number.isFinite(num));

    const getToken = (name) =>
        getComputedStyle(document.documentElement).getPropertyValue(name).trim();

    const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);

    App.theme = {
        init() {
            const html = document.documentElement;
            const toggle = qs("#theme-toggle");
            if (!toggle) {
                return;
            }
            const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
            const saved = localStorage.getItem("theme");
            const initial = saved || (prefersDark ? "dark" : "light");

            const setTheme = (theme) => {
                html.setAttribute("data-theme", theme);
                toggle.textContent = theme === "dark" ? "Light" : "Dark";
            };

            setTheme(initial);
            toggle.addEventListener("click", () => {
                const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
                setTheme(next);
                localStorage.setItem("theme", next);
                App.charts.refresh();
                App.graphs.refresh();
            });
        }
    };

    App.transitions = {
        init() {
            const body = document.body;
            requestAnimationFrame(() => body.classList.add("page-ready"));

            if (state.reducedMotion) {
                return;
            }

            qsa("a[href]").forEach((link) => {
                link.addEventListener("click", (event) => {
                    if (
                        event.defaultPrevented ||
                        event.button !== 0 ||
                        event.metaKey ||
                        event.ctrlKey ||
                        event.shiftKey ||
                        event.altKey ||
                        link.target === "_blank" ||
                        link.hasAttribute("download")
                    ) {
                        return;
                    }

                    const href = link.getAttribute("href");
                    if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:") || href.startsWith("javascript:")) {
                        return;
                    }

                    let url;
                    try {
                        url = new URL(link.href, window.location.href);
                    } catch (error) {
                        return;
                    }

                    if (url.origin !== window.location.origin || url.href === window.location.href) {
                        return;
                    }

                    event.preventDefault();
                    body.classList.add("page-leaving");
                    setTimeout(() => {
                        window.location.href = url.href;
                    }, 180);
                });
            });
        }
    };

    App.sidebar = {
        init() {
            const body = document.body;
            const sidebar = qs("#sidebar");
            const sidebarNav = qs("#sidebarNav");
            const indicator = qs("#sidebarActiveIndicator");
            const sidebarToggle = qs("#sidebarToggle");
            const miniToggle = qs("#sidebarMiniToggle");
            const backdrop = qs("#sidebarBackdrop");
            if (!sidebar || !sidebarNav) {
                return;
            }

            const getMiniState = () => localStorage.getItem("sidebar-mini") === "1";
            const storeMiniState = (mini) => localStorage.setItem("sidebar-mini", mini ? "1" : "0");

            const closeSidebar = () => {
                sidebar.classList.remove("open");
                if (backdrop) {
                    backdrop.classList.remove("show");
                }
            };

            const openSidebar = () => {
                if (state.desktopQuery.matches) {
                    return;
                }
                sidebar.classList.add("open");
                if (backdrop) {
                    backdrop.classList.add("show");
                }
            };

            const updateIndicator = (targetLink) => {
                if (!indicator) {
                    return;
                }
                const target = targetLink || qs(".nav-link.active", sidebarNav);
                if (!target) {
                    indicator.style.opacity = "0";
                    return;
                }
                const markerHeight = Math.max(20, target.offsetHeight - 12);
                const markerTop = target.offsetTop + (target.offsetHeight - markerHeight) / 2;
                indicator.style.height = markerHeight + "px";
                indicator.style.transform = "translateY(" + markerTop + "px)";
                indicator.style.opacity = "1";
            };

            const setMini = (mini, persist = true) => {
                if (!state.desktopQuery.matches) {
                    body.classList.remove("sidebar-mini");
                    if (miniToggle) {
                        miniToggle.setAttribute("aria-pressed", "false");
                    }
                    return;
                }
                body.classList.toggle("sidebar-mini", mini);
                if (miniToggle) {
                    miniToggle.setAttribute("aria-pressed", mini ? "true" : "false");
                    const icon = qs("i", miniToggle);
                    if (icon) {
                        icon.className = mini ? "bi bi-chevron-double-right" : "bi bi-chevron-double-left";
                    }
                }
                if (persist) {
                    storeMiniState(mini);
                }
                requestAnimationFrame(updateIndicator);
            };

            const syncViewport = () => {
                if (state.desktopQuery.matches) {
                    closeSidebar();
                    setMini(getMiniState(), false);
                } else {
                    body.classList.remove("sidebar-mini");
                }
                updateIndicator();
            };

            if (sidebarToggle) {
                sidebarToggle.addEventListener("click", () => {
                    if (state.desktopQuery.matches) {
                        setMini(!body.classList.contains("sidebar-mini"));
                    } else if (sidebar.classList.contains("open")) {
                        closeSidebar();
                    } else {
                        openSidebar();
                    }
                });
            }

            if (miniToggle) {
                miniToggle.addEventListener("click", () => {
                    if (!state.desktopQuery.matches) {
                        closeSidebar();
                        return;
                    }
                    setMini(!body.classList.contains("sidebar-mini"));
                });
            }

            if (backdrop) {
                backdrop.addEventListener("click", closeSidebar);
            }

            qsa(".nav-link", sidebarNav).forEach((link) => {
                link.addEventListener("mouseenter", () => updateIndicator(link));
                link.addEventListener("focus", () => updateIndicator(link));
                link.addEventListener("mouseleave", () => updateIndicator());
            });

            window.addEventListener("resize", syncViewport);
            syncViewport();
        }
    };

    App.buttons = {
        init() {
            return;
        }
    };

    App.forms = {
        init() {
            qsa("form").forEach((form) => {
                form.addEventListener("submit", () => {
                    const submitButton = qs("button[type='submit'].js-btn-loading", form);
                    if (!submitButton || submitButton.disabled) {
                        return;
                    }
                    const loadingText = submitButton.dataset.loadingText || "Loading...";
                    submitButton.dataset.originalText = submitButton.innerHTML;
                    submitButton.disabled = true;
                    submitButton.classList.add("is-loading");
                    submitButton.innerHTML = "<span class=\"spinner-border spinner-border-sm me-2\" role=\"status\" aria-hidden=\"true\"></span>" + loadingText;
                });
            });
        }
    };

    App.metrics = {
        animateCounter(el) {
            if (!el || el.dataset.counterDone === "1") {
                return;
            }
            const target = Number.parseFloat(el.dataset.counterTarget || "0");
            if (!Number.isFinite(target)) {
                el.textContent = "0";
                return;
            }
            const decimals = target % 1 === 0 ? 0 : 1;
            const suffix = el.dataset.counterSuffix || "";
            const duration = 880;
            const start = performance.now();

            const frame = (now) => {
                const progress = Math.min(1, (now - start) / duration);
                const value = target * easeOutCubic(progress);
                el.textContent = value.toFixed(decimals) + suffix;
                if (progress < 1) {
                    requestAnimationFrame(frame);
                } else {
                    el.dataset.counterDone = "1";
                }
            };

            requestAnimationFrame(frame);
        },
        applyProgress(el) {
            if (!el || el.dataset.progressDone === "1") {
                return;
            }
            const progress = Number.parseFloat(el.dataset.progress || "0");
            if (!Number.isFinite(progress)) {
                return;
            }
            const value = Math.max(0, Math.min(100, progress));
            el.style.setProperty("--progress", value + "%");
            el.dataset.progressDone = "1";
        }
    };

    App.reveal = {
        init() {
            qsa("[data-reveal], .hero-panel, .section-header, .chat-panel, .card.card-glass").forEach((el) => {
                el.classList.add("reveal", "is-visible");
            });
            qsa(".stagger-grid > .stagger-item").forEach((item) => {
                item.classList.add("is-visible");
            });
            qsa("[data-counter-target]").forEach((counter) => App.metrics.animateCounter(counter));
            qsa("[data-progress]").forEach((progress) => App.metrics.applyProgress(progress));
            qsa("canvas[data-chart]").forEach((canvas) => App.charts.create(canvas));
        }
    };

    App.skeletons = {
        init() {
            const hosts = qsa("[data-skeleton-host]");
            hosts.forEach((host, index) => {
                const delay = Number.parseInt(host.dataset.skeletonDelay || "", 10);
                const resolvedDelay = Number.isFinite(delay) ? delay : 440 + index * 80;
                setTimeout(() => {
                    host.classList.add("is-loaded");
                }, resolvedDelay);
            });
        }
    };

    App.toasts = {
        region: null,
        init() {
            this.region = qs("#toastRegion");
            if (!this.region) {
                return;
            }
            window.showToast = this.show.bind(this);

            const serverMessages = qs("#serverMessages");
            if (serverMessages) {
                qsa("[data-toast-level]", serverMessages).forEach((msg) => {
                    this.show(msg.dataset.toastLevel || "info", msg.textContent.trim());
                });
            }

            if (!sessionStorage.getItem("command-palette-tip-shown")) {
                setTimeout(() => {
                    this.show("info", "Tip: Press Ctrl + K to open quick navigation.");
                    sessionStorage.setItem("command-palette-tip-shown", "1");
                }, 900);
            }
        },
        icon(type) {
            if (type === "success") {
                return "bi-check-circle-fill";
            }
            if (type === "error" || type === "danger") {
                return "bi-exclamation-octagon-fill";
            }
            return "bi-info-circle-fill";
        },
        normalize(type) {
            const token = String(type || "").toLowerCase().split(" ")[0];
            if (token === "danger") {
                return "error";
            }
            if (token.includes("success")) {
                return "success";
            }
            if (token.includes("error")) {
                return "error";
            }
            if (token.includes("info")) {
                return "info";
            }
            if (!token) {
                return "info";
            }
            return "info";
        },
        show(type, message, options = {}) {
            if (!this.region || !message) {
                return;
            }
            const level = this.normalize(type);
            const toast = document.createElement("article");
            toast.className = "app-toast app-toast-" + level;
            toast.setAttribute("role", "status");

            const duration = Number.isFinite(options.duration) ? options.duration : 3600;
            toast.innerHTML =
                "<div class=\"toast-icon\"><i class=\"bi " + this.icon(level) + "\"></i></div>" +
                "<div class=\"toast-content\">" +
                    "<p class=\"toast-title\">" + level.charAt(0).toUpperCase() + level.slice(1) + "</p>" +
                    "<p class=\"toast-message\"></p>" +
                "</div>" +
                "<button class=\"toast-close\" type=\"button\" aria-label=\"Dismiss notification\"><i class=\"bi bi-x-lg\"></i></button>";

            const messageEl = qs(".toast-message", toast);
            messageEl.textContent = message;

            const close = () => {
                toast.classList.add("is-leaving");
                setTimeout(() => toast.remove(), 220);
            };

            qs(".toast-close", toast).addEventListener("click", close);
            this.region.appendChild(toast);
            requestAnimationFrame(() => toast.classList.add("is-visible"));
            setTimeout(close, duration);
        }
    };

    App.commandPalette = {
        init() {
            this.palette = qs("#commandPalette");
            this.input = qs("#commandPaletteInput");
            this.list = qs("#commandPaletteList");
            this.subjectList = qs("#commandPaletteSubjects");
            if (!this.palette || !this.input || !this.list || !this.subjectList) {
                return;
            }

            this.populateSubjects();
            this.bindEvents();
        },
        populateSubjects() {
            const subjects = qsa(".subject-command-source");
            const fragment = document.createDocumentFragment();
            subjects.slice(0, 24).forEach((subject) => {
                const href = subject.getAttribute("href");
                const label = subject.dataset.subjectName || subject.textContent.trim();
                if (!href || !label) {
                    return;
                }
                const item = document.createElement("a");
                item.href = href;
                item.className = "command-item";
                item.setAttribute("data-command-item", "");
                item.setAttribute("data-command-label", "Subject " + label);
                item.innerHTML = "<i class=\"bi bi-book\"></i><span>" + label + "</span>";
                fragment.appendChild(item);
            });

            if (fragment.childNodes.length === 0) {
                const empty = document.createElement("p");
                empty.className = "command-empty";
                empty.textContent = "No subjects available on this page.";
                this.subjectList.appendChild(empty);
            } else {
                this.subjectList.appendChild(fragment);
            }
        },
        open() {
            this.palette.classList.add("is-open");
            this.palette.setAttribute("aria-hidden", "false");
            document.body.classList.add("command-open");
            this.input.value = "";
            this.filter("");
            setTimeout(() => this.input.focus(), 40);
        },
        close() {
            this.palette.classList.remove("is-open");
            this.palette.setAttribute("aria-hidden", "true");
            document.body.classList.remove("command-open");
        },
        filter(query) {
            const normalized = (query || "").trim().toLowerCase();
            qsa("[data-command-item]", this.palette).forEach((item) => {
                const label = (item.dataset.commandLabel || item.textContent || "").toLowerCase();
                const visible = !normalized || label.includes(normalized);
                item.classList.toggle("d-none", !visible);
            });
        },
        bindEvents() {
            document.addEventListener("keydown", (event) => {
                const active = document.activeElement;
                const isTypingContext =
                    active &&
                    (active.tagName === "INPUT" ||
                        active.tagName === "TEXTAREA" ||
                        active.tagName === "SELECT" ||
                        active.isContentEditable);

                const isK = event.key && event.key.toLowerCase() === "k";
                if ((event.ctrlKey || event.metaKey) && isK) {
                    if (isTypingContext && !this.palette.classList.contains("is-open")) {
                        return;
                    }
                    event.preventDefault();
                    if (this.palette.classList.contains("is-open")) {
                        this.close();
                    } else {
                        this.open();
                    }
                }
                if (event.key === "Escape" && this.palette.classList.contains("is-open")) {
                    this.close();
                }
            });

            qsa("[data-command-close]", this.palette).forEach((closeTrigger) => {
                closeTrigger.addEventListener("click", () => this.close());
            });

            qsa("[data-command-open]").forEach((trigger) => {
                trigger.addEventListener("click", () => this.open());
            });

            this.input.addEventListener("input", (event) => this.filter(event.target.value));

            this.input.addEventListener("keydown", (event) => {
                if (event.key !== "Enter") {
                    return;
                }
                const first = qsa("[data-command-item]", this.palette).find((item) => !item.classList.contains("d-none"));
                if (first) {
                    window.location.href = first.getAttribute("href");
                }
            });
        }
    };

    App.charts = {
        instances: [],
        init() {
            if (!window.Chart) {
                return;
            }
            const fontFamily = getToken("--font-body").replace(/"/g, "") || "Manrope";
            window.Chart.defaults.font.family = fontFamily;
            window.Chart.defaults.animation.duration = 860;
            qsa("canvas[data-chart]").forEach((canvas) => this.create(canvas));
        },
        refresh() {
            if (!window.Chart) {
                return;
            }
            this.instances.forEach((chart) => chart.destroy());
            this.instances = [];
            qsa("canvas[data-chart]").forEach((canvas) => {
                delete canvas.dataset.chartReady;
                this.create(canvas);
            });
        },
        create(canvas) {
            if (!window.Chart || !canvas || canvas.dataset.chartReady === "1") {
                return;
            }

            const chartType = (canvas.dataset.chart || "").toLowerCase();
            const labels = toList(canvas.dataset.labels);
            const values = toNumbers(canvas.dataset.values);
            if (!chartType || values.length === 0) {
                return;
            }

            const accent = getToken("--accent-primary") || "#2260ee";
            const accent2 = getToken("--accent-secondary") || "#12b8b5";
            const text = getToken("--text-secondary") || "#51617d";
            const border = getToken("--border-color") || "rgba(0,0,0,0.12)";
            const gradient = [accent, accent2, getToken("--accent-strong") || "#1848be", "#89a7ff", "#65dcd3"];
            const colors = toList(canvas.dataset.colors);
            const palette = colors.length ? colors : gradient;

            let config;
            if (chartType === "donut" || chartType === "doughnut") {
                config = {
                    type: "doughnut",
                    data: {
                        labels: labels.length ? labels : ["Complete", "In Progress", "Pending"],
                        datasets: [{
                            data: values,
                            backgroundColor: palette.slice(0, values.length),
                            borderColor: "transparent",
                            hoverOffset: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        cutout: "72%",
                        plugins: {
                            legend: {
                                position: "bottom",
                                labels: { color: text, usePointStyle: true, boxWidth: 9 }
                            },
                            tooltip: { mode: "index", intersect: false }
                        }
                    }
                };
            } else if (chartType === "line") {
                config = {
                    type: "line",
                    data: {
                        labels: labels.length ? labels : values.map((_, index) => "Day " + (index + 1)),
                        datasets: [{
                            data: values,
                            tension: 0.35,
                            borderWidth: 2.4,
                            borderColor: accent,
                            pointRadius: 3.2,
                            pointHoverRadius: 4.4,
                            pointBackgroundColor: accent2,
                            fill: true,
                            backgroundColor: "rgba(34, 96, 238, 0.12)"
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            x: {
                                grid: { color: "transparent" },
                                ticks: { color: text }
                            },
                            y: {
                                beginAtZero: true,
                                grid: { color: border },
                                ticks: { color: text, precision: 0 }
                            }
                        }
                    }
                };
            } else if (chartType === "bar") {
                config = {
                    type: "bar",
                    data: {
                        labels: labels.length ? labels : values.map((_, index) => "Item " + (index + 1)),
                        datasets: [{
                            data: values,
                            borderRadius: 8,
                            backgroundColor: values.map((_, index) => palette[index % palette.length]),
                            maxBarThickness: 28
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            x: {
                                grid: { color: "transparent" },
                                ticks: { color: text }
                            },
                            y: {
                                beginAtZero: true,
                                grid: { color: border },
                                ticks: { color: text, precision: 0 }
                            }
                        }
                    }
                };
            }

            if (!config) {
                return;
            }

            const instance = new window.Chart(canvas, config);
            this.instances.push(instance);
            canvas.dataset.chartReady = "1";
        }
    };

    App.graphs = {
        init() {
            if (!window.d3) {
                return;
            }
            qsa("[data-concept-graph]").forEach((canvas) => this.create(canvas));
        },
        refresh() {
            if (!window.d3) {
                return;
            }
            qsa("[data-concept-graph]").forEach((canvas) => {
                canvas.innerHTML = "";
                delete canvas.dataset.graphReady;
                this.create(canvas);
            });
        },
        create(canvas) {
            if (!window.d3 || !canvas || canvas.dataset.graphReady === "1") {
                return;
            }
            const sourceId = canvas.dataset.sourceId;
            const source = sourceId ? qs("#" + sourceId) : null;
            if (!source) {
                return;
            }

            let graph;
            try {
                graph = JSON.parse(source.textContent || "{}");
            } catch (error) {
                return;
            }

            if (!Array.isArray(graph.nodes) || graph.nodes.length === 0) {
                return;
            }

            const width = Math.max(canvas.clientWidth || 640, 320);
            const height = Math.max(canvas.clientHeight || 520, 320);
            const primary = getToken("--accent-primary") || "#2260ee";
            const secondary = getToken("--accent-secondary") || "#12b8b5";
            const text = getToken("--text-primary") || "#122038";
            const muted = getToken("--text-muted") || "#6f7f9c";
            const border = getToken("--border-color") || "rgba(20, 36, 64, 0.13)";

            const svg = window.d3
                .select(canvas)
                .append("svg")
                .attr("viewBox", [0, 0, width, height])
                .attr("role", "img")
                .attr("aria-label", "Interactive concept graph");

            const tooltip = document.createElement("div");
            tooltip.className = "concept-graph-tooltip";
            canvas.appendChild(tooltip);

            const nodes = graph.nodes.map((node) => ({ ...node }));
            const links = (graph.links || []).map((link) => ({ ...link }));
            const nodeIndex = new Map(nodes.map((node) => [String(node.id), node]));

            const link = svg
                .append("g")
                .attr("stroke", border)
                .attr("stroke-opacity", 0.7)
                .selectAll("line")
                .data(links)
                .join("line")
                .attr("stroke-width", (d) => Math.max(1.2, Math.min(4.5, d.weight * 0.7)));

            const node = svg
                .append("g")
                .selectAll("g")
                .data(nodes)
                .join("g")
                .attr("tabindex", 0)
                .style("cursor", "pointer")
                .call(this._dragBehavior());

            node
                .append("circle")
                .attr("r", (d) => Math.max(10, Math.min(28, d.size / 2)))
                .attr("fill", (d, index) => (index % 2 === 0 ? primary : secondary))
                .attr("fill-opacity", 0.88)
                .attr("stroke", "#ffffff")
                .attr("stroke-width", 1.5);

            node
                .append("text")
                .attr("x", 0)
                .attr("y", (d) => Math.max(18, Math.min(34, d.size / 2 + 16)))
                .attr("text-anchor", "middle")
                .attr("fill", text)
                .attr("font-size", 11)
                .attr("font-weight", 700)
                .text((d) => d.label.length > 18 ? d.label.slice(0, 18) + "..." : d.label);

            const simulation = window.d3
                .forceSimulation(nodes)
                .force("link", window.d3.forceLink(links).id((d) => d.id).distance(110).strength(0.4))
                .force("charge", window.d3.forceManyBody().strength(-220))
                .force("center", window.d3.forceCenter(width / 2, height / 2))
                .force("collision", window.d3.forceCollide().radius((d) => Math.max(16, d.size / 2 + 12)));

            simulation.on("tick", () => {
                link
                    .attr("x1", (d) => nodeIndex.get(String(d.source.id || d.source)).x)
                    .attr("y1", (d) => nodeIndex.get(String(d.source.id || d.source)).y)
                    .attr("x2", (d) => nodeIndex.get(String(d.target.id || d.target)).x)
                    .attr("y2", (d) => nodeIndex.get(String(d.target.id || d.target)).y);

                node.attr("transform", (d) => "translate(" + d.x + "," + d.y + ")");
            });

            const showTooltip = (event, d) => {
                tooltip.innerHTML =
                    "<strong>" + d.label + "</strong>" +
                    "<div>" + d.chunk_hits + " supporting chunks</div>" +
                    (d.description ? "<div class=\"mt-1\">" + d.description + "</div>" : "");
                tooltip.classList.add("is-visible");
                const rect = canvas.getBoundingClientRect();
                const left = Number.isFinite(event.clientX) ? event.clientX - rect.left + 12 : Math.max(16, (d.x || 0) + 18);
                const top = Number.isFinite(event.clientY) ? event.clientY - rect.top + 12 : Math.max(16, (d.y || 0) + 18);
                tooltip.style.left = left + "px";
                tooltip.style.top = top + "px";
            };

            const hideTooltip = () => tooltip.classList.remove("is-visible");

            node
                .on("mouseenter", showTooltip)
                .on("mousemove", showTooltip)
                .on("mouseleave", hideTooltip)
                .on("focus", (event, d) => showTooltip(event, d))
                .on("blur", hideTooltip)
                .on("click", (_event, d) => {
                    window.location.href = "/concepts/" + d.slug + "/";
                })
                .on("keydown", (event, d) => {
                    if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        window.location.href = "/concepts/" + d.slug + "/";
                    }
                });

            canvas.dataset.graphReady = "1";
        },
        _dragBehavior() {
            return window.d3.drag()
                .on("start", (event, d) => {
                    if (!event.active) {
                        d.fx = d.x;
                        d.fy = d.y;
                    }
                })
                .on("drag", (event, d) => {
                    d.fx = event.x;
                    d.fy = event.y;
                })
                .on("end", (event, d) => {
                    if (!event.active) {
                        d.fx = null;
                        d.fy = null;
                    }
                });
        }
    };

    App.chat = {
        init() {
            qsa("[data-chat-root]").forEach((root) => this.setupRoot(root));
        },
        setupRoot(root) {
            const messages = qs("[data-chat-messages]", root);
            if (!messages) {
                return;
            }
            const form = qs("[data-chat-form]", root);
            const typing = qs("[data-typing-indicator]", root);
            const scrollButton = qs("[data-chat-scroll]", root);
            const panel = messages.closest(".chat-panel");
            const questionInput = form ? qs("input[name='question']", form) : null;
            const demoButtons = qsa("[data-demo-question]", root);
            const zoomButtons = qsa("[data-diagram-zoom]", root);
            const modalEl = qs("#diagramZoomModal", root);
            const modalImage = modalEl ? qs("[data-diagram-modal-image]", modalEl) : null;
            const modalTitle = qs("#diagramZoomTitle", root);
            const modalInstance = modalEl && window.bootstrap ? new window.bootstrap.Modal(modalEl) : null;

            const syncMarkers = () => {
                if (!panel) {
                    return;
                }
                const distanceTop = messages.scrollTop;
                const distanceBottom = messages.scrollHeight - messages.scrollTop - messages.clientHeight;
                panel.classList.toggle("has-top-shadow", distanceTop > 8);
                panel.classList.toggle("has-bottom-shadow", distanceBottom > 8);
                if (scrollButton) {
                    scrollButton.classList.toggle("is-visible", distanceBottom > 100);
                }
            };

            const scrollToBottom = () => {
                messages.scrollTop = messages.scrollHeight;
                syncMarkers();
            };

            qsa(".message", messages).forEach((message, index) => {
                message.style.setProperty("--message-index", String(index));
            });

            qsa("[data-copy-message]", messages).forEach((copyButton) => {
                copyButton.addEventListener("click", async () => {
                    const bubble = qs(".message-bubble", copyButton.closest(".message"));
                    if (!bubble) {
                        return;
                    }
                    const text = bubble.innerText.trim();
                    if (!text) {
                        return;
                    }
                    try {
                        if (navigator.clipboard && navigator.clipboard.writeText) {
                            await navigator.clipboard.writeText(text);
                        } else {
                            const temp = document.createElement("textarea");
                            temp.value = text;
                            temp.setAttribute("readonly", "");
                            temp.style.position = "absolute";
                            temp.style.left = "-9999px";
                            document.body.appendChild(temp);
                            temp.select();
                            document.execCommand("copy");
                            temp.remove();
                        }
                        copyButton.classList.add("is-copied");
                        const icon = qs("i", copyButton);
                        if (icon) {
                            icon.className = "bi bi-check2";
                        }
                        if (typeof window.showToast === "function") {
                            window.showToast("success", "Response copied to clipboard.");
                        }
                        setTimeout(() => {
                            copyButton.classList.remove("is-copied");
                            if (icon) {
                                icon.className = "bi bi-clipboard";
                            }
                        }, 1300);
                    } catch (error) {
                        if (typeof window.showToast === "function") {
                            window.showToast("error", "Clipboard copy failed on this browser.");
                        }
                    }
                });
            });

            if (scrollButton) {
                scrollButton.addEventListener("click", scrollToBottom);
            }

            if (form && typing) {
                form.addEventListener("submit", () => {
                    typing.classList.add("is-visible");
                    requestAnimationFrame(scrollToBottom);
                });
            }

            demoButtons.forEach((button) => {
                button.addEventListener("click", () => {
                    if (!questionInput) {
                        return;
                    }
                    questionInput.value = button.dataset.demoQuestion || "";
                    questionInput.focus();
                    questionInput.scrollIntoView({ behavior: state.reducedMotion ? "auto" : "smooth", block: "center" });
                    if (typeof window.showToast === "function") {
                        window.showToast("info", "Demo question loaded into the chat form.");
                    }
                });
            });

            zoomButtons.forEach((button) => {
                button.addEventListener("click", () => {
                    if (!modalInstance || !modalImage) {
                        return;
                    }
                    const src = button.dataset.diagramSrc || "";
                    const title = button.dataset.diagramTitle || "Diagram Preview";
                    modalImage.src = src;
                    modalImage.alt = title;
                    if (modalTitle) {
                        modalTitle.textContent = title;
                    }
                    modalInstance.show();
                });
            });

            messages.addEventListener("scroll", syncMarkers, { passive: true });
            requestAnimationFrame(scrollToBottom);
        }
    };

    App.init = () => {
        document.body.classList.add("js-ready");
        App.theme.init();
        App.transitions.init();
        App.sidebar.init();
        App.buttons.init();
        App.forms.init();
        App.toasts.init();
        App.commandPalette.init();
        App.skeletons.init();
        App.reveal.init();
        App.charts.init();
        App.graphs.init();
        App.chat.init();
    };

    document.addEventListener("DOMContentLoaded", App.init);
})();
