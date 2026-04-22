(() => {
    "use strict";

    const root = document.querySelector("[data-chatgpt-root]");
    if (!root) {
        return;
    }

    const streamUrl = root.dataset.streamUrl || "/chat/stream/";
    const chatUrl = (streamUrl || "").replace(/\/stream\/?$/, "/") || "/chat/";
    const historyUrl = root.dataset.historyUrl || "/chat/history/";
    const userId = root.dataset.userId || "anonymous";
    const strictLocked = root.dataset.strictLocked === "1";
    const storageKey = `chatgptThreads:${userId}`;

    const threadListEl = document.querySelector("#chat-thread-list") || root.querySelector("[data-thread-list]");
    const messageScroller = document.querySelector("#chat-message-container") || root.querySelector("[data-message-scroller]");
    const emptyState = root.querySelector("[data-empty-state]");
    const composer = root.querySelector("[data-chat-form]") || document.querySelector(".chatgpt-composer");
    const textarea =
        root.querySelector("[data-input-message]") ||
        document.querySelector("#chat-input") ||
        document.querySelector("#message-input") ||
        document.querySelector("textarea[name='message']");
    const messageInput = document.getElementById("messageInput") || textarea;
    const sendBtn = root.querySelector("[data-send-button]") || document.querySelector("#send-btn") || document.querySelector("#sendButton");
    const scopeSelect = root.querySelector("[data-input-scope]");
    const regulationSelect = root.querySelector("[data-input-regulation]");
    const branchSelect = root.querySelector("[data-input-branch]");
    const semesterSelect = root.querySelector("[data-input-semester]");
    const subjectSelect = root.querySelector("[data-input-subject]");
    const lessonSelect = root.querySelector("[data-input-lesson]");
    const unitSelect = root.querySelector("[data-input-unit]");
    const pdfSelect = root.querySelector("[data-input-pdf]");
    const subjectScopeWrap = root.querySelector("[data-scope-subject]");
    const lessonScopeWrap = root.querySelector("[data-scope-lesson]");
    const unitScopeWrap = root.querySelector("[data-scope-unit]");
    const scopeHelperEl = root.querySelector("[data-scope-helper]");
    const scopeErrorEl = root.querySelector("[data-scope-error]");
    const strictInput = root.querySelector("[data-input-strict]");
    const newChatBtn = root.querySelector("[data-new-chat]");
    const loadHistoryBtn = root.querySelector("[data-load-history]");
    const sidebarToggle = root.querySelector("[data-sidebar-toggle]");
    const sidebar = root.querySelector(".chatgpt-sidebar");
    const detailsToggle = root.querySelector("[data-details-toggle]");
    const detailsPanel = root.querySelector(".chatgpt-source-panel");
    const demoModeToggleBtn = document.getElementById("demo-mode-toggle");
    const thinkingEl = root.querySelector("[data-thinking]");
    const sidebarStorageKey = `chatgptSidebarCollapsed:${userId}`;
    const detailsStorageKey = `chatgptDetailsCollapsed:${userId}`;
    const sidebarFeedbackEl = root.querySelector("[data-chat-feedback]");

    const panelReferences = root.querySelector("[data-panel-references-body]");
    const panelConfidence = root.querySelector("[data-panel-confidence-body]");

    const sourceModalEl = root.querySelector("#chatSourceModal");
    const sourceModalIframe = root.querySelector("[data-source-iframe]");
    const sourceModal = sourceModalEl && window.bootstrap ? new window.bootstrap.Modal(sourceModalEl) : null;
    const clearChatBtn = root.querySelector("[data-clear-chat]");

    const state = {
        threads: [],
        activeThreadId: null,
        historyPage: 1,
        hasHistoryNext: true,
        loadingHistory: false,
        sidebarCollapsed: false,
        detailsCollapsed: false,
        isStreaming: false,
        isSending: false
    };

    const lessonCatalogScript = document.getElementById("lesson-catalog-data");
    let lessonCatalog = [];
    if (lessonCatalogScript) {
        try {
            const parsedCatalog = JSON.parse(lessonCatalogScript.textContent || "[]");
            lessonCatalog = Array.isArray(parsedCatalog) ? parsedCatalog : [];
        } catch (error) {
            lessonCatalog = [];
        }
    }

    const normalizeScope = (scope) => {
        const value = String(scope || "global").toLowerCase();
        return ["global", "subject", "lesson", "unit", "pdf"].includes(value) ? value : "global";
    };

    const normalizeConversationScope = () => "global";

    const chatDeleteUrlForThread = (threadId) => {
        const match = String(threadId || "").match(/^query-(\d+)$/);
        if (!match) {
            return null;
        }
        return `${chatUrl}${match[1]}/`;
    };

    const stopWords = new Set([
        "what", "is", "are", "the", "a", "an", "in", "on", "of", "for", "to", "with", "about", "explain", "define"
    ]);

    let demoMode = false;
    const NO_RESULT_MESSAGE = "This topic is not available in the selected syllabus.";
    const STRICT_NO_RESULT_MESSAGE = "This topic is not available in the selected syllabus.";

    const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

    const scrollToLatestMessage = (smooth = false) => {
        if (!messageScroller) {
            return;
        }
        if (smooth) {
            messageScroller.scrollTo({ top: messageScroller.scrollHeight, behavior: "smooth" });
            return;
        }
        messageScroller.scrollTop = messageScroller.scrollHeight;
    };

    const applyDemoMode = () => {
        document.body.classList.toggle("demo-mode", demoMode);
        if (demoModeToggleBtn) {
            demoModeToggleBtn.classList.toggle("is-active", demoMode);
        }
    };

    if (demoModeToggleBtn) {
        demoModeToggleBtn.addEventListener("click", () => {
            demoMode = !demoMode;
            applyDemoMode();
        });
    }

    const escapeHtml = (value) =>
        String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#039;");

    const nowTime = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

    const normalizeSectionTitle = (title) => {
        const source = String(title || "Section").trim();
        const lower = source.toLowerCase();
        if (lower.includes("reference")) {
            return { label: "References", className: "is-references", isReference: true };
        }
        return { label: source, className: sectionClassFromLabel(source), isReference: false };
    };

    const resolveConfidence = (meta) => {
        const rawLabel = String(meta?.confidence_label || "").toLowerCase();
        if (rawLabel === "high" || rawLabel === "medium" || rawLabel === "low") {
            return rawLabel;
        }
        const score = Number(meta?.confidence_score);
        if (!Number.isFinite(score)) {
            return "low";
        }
        if (score >= 0.75) {
            return "high";
        }
        if (score >= 0.45) {
            return "medium";
        }
        return "low";
    };

    const deriveTitleFromQuestion = (question) => {
        const source = String(question || "").replace(/\s+/g, " ").trim();
        if (!source) {
            return "New Chat";
        }
        return source.slice(0, 30);
    };

    const showSidebarFeedback = (message, type = "success") => {
        if (!sidebarFeedbackEl) {
            return;
        }
        sidebarFeedbackEl.innerHTML = `<div class="chat-feedback-msg ${type === "error" ? "is-error" : "is-success"}">${escapeHtml(message)}</div>`;
        window.setTimeout(() => {
            sidebarFeedbackEl.innerHTML = "";
        }, 2200);
    };

    const clearScopeError = () => {
        if (!scopeErrorEl) {
            return;
        }
        scopeErrorEl.classList.add("d-none");
        scopeErrorEl.textContent = "";
    };

    const showScopeError = (message) => {
        if (!scopeErrorEl) {
            return;
        }
        scopeErrorEl.textContent = message;
        scopeErrorEl.classList.remove("d-none");
    };

    const saveThreads = () => {
        try {
            localStorage.setItem(storageKey, JSON.stringify(state.threads));
        } catch (error) {
            return;
        }
    };

    const loadThreads = () => {
        try {
            const raw = localStorage.getItem(storageKey);
            if (!raw) {
                return;
            }
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed)) {
                state.threads = parsed;
                if (state.threads.length > 0) {
                    state.activeThreadId = state.threads[0].id;
                }
            }
        } catch (error) {
            return;
        }
    };

    const createThread = (title = "New Chat") => {
        const existingEmpty = state.threads.find((thread) => {
            const messages = Array.isArray(thread.messages) ? thread.messages : [];
            return messages.length === 0 && (!thread.title || thread.title === "New Chat");
        });
        if (existingEmpty) {
            state.activeThreadId = existingEmpty.id;
            renderThreadList();
            renderMessages();
            return existingEmpty;
        }

        const id = `thread-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
        const thread = {
            id,
            title,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            scope: normalizeConversationScope(),
            regulation: "",
            branch: "",
            semester: "",
            subjectId: "",
            lessonId: "",
            unitId: "",
            pdfId: "",
            strictMode: !!strictInput?.checked,
            messages: []
        };
        state.threads.unshift(thread);
        state.activeThreadId = id;
        saveThreads();
        renderThreadList();
        renderMessages();
        return thread;
    };

    const getActiveThread = () => state.threads.find((thread) => thread.id === state.activeThreadId) || null;

    const renderLessonOptions = (subjectId = "") => {
        if (!lessonSelect) {
            return;
        }

        const selectedSubjectId = String(subjectId || "");
        const lessonEntries = selectedSubjectId
            ? lessonCatalog.filter((item) => String(item.subject_id) === selectedSubjectId)
            : lessonCatalog;

        const fragment = document.createDocumentFragment();
        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = "All lessons";
        fragment.appendChild(defaultOption);

        lessonEntries.forEach((item) => {
            const option = document.createElement("option");
            option.value = String(item.id || "");
            option.textContent = String(item.label || "");
            option.dataset.subjectId = String(item.subject_id || "");
            fragment.appendChild(option);
        });

        lessonSelect.innerHTML = "";
        lessonSelect.appendChild(fragment);
    };

    const setActiveThread = (threadId) => {
        state.activeThreadId = threadId;
        const thread = getActiveThread();
        if (thread) {
            if (subjectSelect) {
                subjectSelect.value = thread.subjectId || "";
            }
            if (lessonSelect) {
                renderLessonOptions(thread.subjectId || "");
                lessonSelect.value = thread.lessonId || "";
            }
            if (unitSelect) {
                unitSelect.value = thread.unitId || "";
            }
            if (pdfSelect) {
                pdfSelect.value = thread.pdfId || "";
            }
            if (strictInput && !strictInput.closest("label")?.classList.contains("d-none") && !strictLocked) {
                strictInput.checked = !!thread.strictMode;
            }
        }
        applyScopeVisibility();
        renderThreadList();
        renderMessages();
    };

    const upsertThreadMessage = (threadId, message) => {
        const thread = state.threads.find((item) => item.id === threadId);
        if (!thread) {
            return;
        }
        if (!message.id) {
            message.id = `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        }
        thread.messages.push(message);
        thread.updatedAt = new Date().toISOString();
        thread.scope = normalizeConversationScope();
        thread.regulation = "";
        thread.branch = "";
        thread.semester = "";
        thread.subjectId = subjectSelect ? subjectSelect.value : "";
        thread.lessonId = lessonSelect ? lessonSelect.value : "";
        thread.unitId = unitSelect ? unitSelect.value : "";
        thread.pdfId = pdfSelect ? pdfSelect.value : "";
        thread.strictMode = strictInput ? !!strictInput.checked : true;
        if (!thread.title || thread.title === "New Chat") {
            const firstUser = thread.messages.find((item) => item.role === "user");
            if (firstUser) {
                thread.title = deriveTitleFromQuestion(firstUser.content);
            }
        }
    };

    const renderThreadList = () => {
        threadListEl.innerHTML = "";
        if (!state.threads.length) {
            threadListEl.innerHTML = '<div class="chatgpt-empty-history">No chats yet. Start a new conversation.</div>';
            return;
        }

        state.threads.forEach((thread) => {
            const row = document.createElement("div");
            row.className = "chatgpt-thread-row";

            const button = document.createElement("button");
            button.type = "button";
            button.className = "chatgpt-thread-item chat-thread-item" + (thread.id === state.activeThreadId ? " is-active" : "");
            button.setAttribute("aria-label", `Open conversation ${thread.title}`);
            button.innerHTML = `<strong>${escapeHtml(thread.title || "Untitled chat")}</strong><span>${new Date(thread.updatedAt || thread.createdAt).toLocaleString()}</span>`;
            button.addEventListener("click", () => setActiveThread(thread.id));

            const deleteBtn = document.createElement("button");
            deleteBtn.type = "button";
            deleteBtn.className = "btn btn-sm btn-outline-danger chat-thread-delete";
            deleteBtn.setAttribute("aria-label", `Delete conversation ${thread.title || "chat"}`);
            deleteBtn.innerHTML = '<i class="bi bi-trash" aria-hidden="true"></i>';
            deleteBtn.addEventListener("click", async (event) => {
                event.stopPropagation();
                const confirmed = window.confirm("Delete this chat?");
                if (!confirmed) {
                    return;
                }
                try {
                    await deleteThread(thread.id);
                } catch (error) {
                    window.alert("Unable to delete chat right now.");
                    showSidebarFeedback("Unable to delete chat right now", "error");
                }
            });

            row.appendChild(button);
            row.appendChild(deleteBtn);
            threadListEl.appendChild(row);
        });
    };

    const removeThreadLocal = (threadId) => {
        const before = state.threads.length;
        state.threads = state.threads.filter((thread) => thread.id !== threadId);
        if (state.threads.length === before) {
            return;
        }
        if (state.activeThreadId === threadId) {
            state.activeThreadId = state.threads.length ? state.threads[0].id : null;
        }
        saveThreads();
        renderThreadList();
        renderMessages();
    };

    const deleteThread = async (threadId) => {
        const deleteUrl = chatDeleteUrlForThread(threadId);
        if (deleteUrl) {
            const response = await fetch(deleteUrl, {
                method: "DELETE",
                headers: {
                    "X-CSRFToken": getCsrfToken(),
                    "X-Requested-With": "XMLHttpRequest"
                }
            });
            if (!response.ok) {
                throw new Error("Unable to delete chat.");
            }
        }
        removeThreadLocal(threadId);
        showSidebarFeedback("Chat deleted successfully", "success");
    };

    const applyScopeVisibility = () => {
        const scope = normalizeScope(scopeSelect?.value || "global");
        clearScopeError();
        if (lessonScopeWrap) {
            lessonScopeWrap.classList.toggle("d-none", scope !== "lesson");
        }
        if (scope !== "lesson" && lessonSelect) {
            lessonSelect.value = "";
        }
        if (scopeHelperEl) {
            if (scope === "lesson") {
                scopeHelperEl.textContent = "Lesson scope searches only references linked to the selected lesson.";
            } else if (scope === "unit") {
                scopeHelperEl.textContent = "Unit scope prioritizes selected unit content and linked references.";
            } else if (scope === "subject") {
                scopeHelperEl.textContent = "Subject scope searches references for the selected subject only.";
            } else if (scope === "pdf") {
                scopeHelperEl.textContent = "PDF scope searches only inside the selected PDF and prioritizes exact context matches.";
            } else {
                scopeHelperEl.textContent = "Global searches all approved references.";
            }
        }
    };

    const buildScopedRequestUrl = (baseUrl, payload) => {
        const url = new URL(baseUrl, window.location.origin);
        url.searchParams.set("scope", normalizeScope(payload.scope || "global"));
        if (payload.subjectId) {
            url.searchParams.set("subject_id", payload.subjectId);
        }
        if (payload.lessonId) {
            url.searchParams.set("lesson_id", payload.lessonId);
        }
        if (payload.unitId) {
            url.searchParams.set("unit_id", payload.unitId);
        }
        if (payload.regulation) {
            url.searchParams.set("regulation", payload.regulation);
        }
        if (payload.branch) {
            url.searchParams.set("branch", payload.branch);
        }
        if (payload.semester) {
            url.searchParams.set("semester", payload.semester);
        }
        if (payload.pdfId) {
            url.searchParams.set("pdf_id", payload.pdfId);
        }
        return url.toString();
    };

    const isMobileViewport = () => window.matchMedia("(max-width: 991px)").matches;

    const setToggleContent = (button, hiddenText, shownText, isHidden, hiddenIconClass, shownIconClass) => {
        if (!button) {
            return;
        }
        const iconEl = button.querySelector("i");
        const labelEl = button.querySelector("span");
        if (iconEl && hiddenIconClass && shownIconClass) {
            iconEl.className = `bi ${isHidden ? hiddenIconClass : shownIconClass}`;
        }
        if (labelEl) {
            labelEl.textContent = isHidden ? hiddenText : shownText;
        } else {
            button.textContent = isHidden ? hiddenText : shownText;
        }
        button.setAttribute("aria-expanded", isHidden ? "false" : "true");
    };

    const updateSidebarToggleLabel = () => {
        if (!sidebarToggle) {
            return;
        }
        const mobile = isMobileViewport();
        const isHidden = mobile ? !sidebar?.classList.contains("is-open") : state.sidebarCollapsed;
        setToggleContent(sidebarToggle, "Show Chats", "Hide Chats", isHidden, "bi-chevron-right", "bi-chevron-left");
    };

    const updateDetailsToggleLabel = () => {
        if (!detailsToggle) {
            return;
        }
        setToggleContent(detailsToggle, "Show Details", "Hide Details", state.detailsCollapsed, "bi-arrows-angle-expand", "bi-arrows-angle-contract");
    };

    const persistSidebarState = () => {
        try {
            localStorage.setItem(sidebarStorageKey, state.sidebarCollapsed ? "1" : "0");
        } catch (error) {
            return;
        }
    };

    const applySidebarState = () => {
        const mobile = isMobileViewport();
        if (!sidebar) {
            return;
        }

        if (mobile) {
            root.classList.remove("is-sidebar-collapsed");
            sidebar.classList.remove("is-open");
        } else {
            sidebar.classList.remove("is-open");
            root.classList.toggle("is-sidebar-collapsed", state.sidebarCollapsed);
        }

        updateSidebarToggleLabel();
    };

    const applyDetailsState = () => {
        if (!detailsPanel || !detailsToggle) {
            return;
        }
        root.classList.toggle("is-details-collapsed", state.detailsCollapsed);
        updateDetailsToggleLabel();
    };

    const toggleSidebar = () => {
        if (!sidebar) {
            return;
        }
        const mobile = isMobileViewport();
        if (mobile) {
            sidebar.classList.toggle("is-open");
            updateSidebarToggleLabel();
            return;
        }

        state.sidebarCollapsed = !state.sidebarCollapsed;
        persistSidebarState();
        applySidebarState();
    };

    const toggleDetails = () => {
        if (!detailsPanel || !detailsToggle) {
            return;
        }
        state.detailsCollapsed = !state.detailsCollapsed;
        try {
            localStorage.setItem(detailsStorageKey, state.detailsCollapsed ? "1" : "0");
        } catch (error) {
            return;
        }
        applyDetailsState();
    };

    const loadSidebarState = () => {
        try {
            state.sidebarCollapsed = localStorage.getItem(sidebarStorageKey) === "1";
        } catch (error) {
            state.sidebarCollapsed = false;
        }
    };

    const loadDetailsState = () => {
        try {
            state.detailsCollapsed = localStorage.getItem(detailsStorageKey) === "1";
        } catch (error) {
            state.detailsCollapsed = false;
        }
    };

    const updateLoadMoreState = () => {
        if (!loadHistoryBtn) {
            return;
        }
        const labelEl = loadHistoryBtn.querySelector("span");
        const isVisible = state.hasHistoryNext;
        loadHistoryBtn.style.display = isVisible ? "inline-flex" : "none";
        loadHistoryBtn.disabled = state.loadingHistory;
        if (labelEl) {
            labelEl.textContent = state.loadingHistory ? "Loading..." : "Load More";
        }
    };

    const fetchAndShowPdfTextPreview = async (sourceUrl) => {
        const match = String(sourceUrl || "").match(/\/pdf-file\/(\d+)\/?$/);
        if (!match) {
            return;
        }
        const response = await fetch(`/api/pdf/${match[1]}/`, { credentials: "same-origin" });
        if (!response.ok || !panelReferences) {
            return;
        }
        const data = await response.json();
        const preview = String(data.preview || "").trim();
        if (!preview) {
            return;
        }
        const safePreview = escapeHtml(preview).replace(/\n/g, "<br>");
        const previewHtml = `<div class="chat-ref-link"><strong>PDF Preview</strong><div>${safePreview}</div></div>`;
        panelReferences.innerHTML = previewHtml + panelReferences.innerHTML;
    };

    const attachMessageClickHandlers = () => {
        messageScroller.querySelectorAll("[data-message-index]").forEach((node) => {
            node.addEventListener("click", () => {
                const index = Number.parseInt(node.dataset.messageIndex || "-1", 10);
                const thread = getActiveThread();
                if (!thread || !Number.isInteger(index) || index < 0 || index >= thread.messages.length) {
                    return;
                }
                const message = thread.messages[index];
                if (message.role === "assistant") {
                    renderSourcePanel(message.meta || null);
                }
            });
        });

        messageScroller.querySelectorAll("[data-open-source]").forEach((node) => {
            node.addEventListener("click", (event) => {
                event.preventDefault();
                const sourceUrl = node.getAttribute("href") || "";
                if (!sourceUrl) {
                    return;
                }
                fetchAndShowPdfTextPreview(sourceUrl).catch(() => {});
                if (sourceModal && sourceModalIframe) {
                    sourceModalIframe.src = sourceUrl;
                    sourceModal.show();
                } else {
                    window.open(sourceUrl, "_blank", "noopener");
                }
            });
        });

        root.querySelectorAll("[data-suggested-question]").forEach((node) => {
            if (node.dataset.listenerBound === "1") {
                return;
            }
            node.dataset.listenerBound = "1";
            node.addEventListener("click", () => {
                const question = node.getAttribute("data-suggested-question") || "";
                if (!question) {
                    return;
                }
                textarea.value = question;
                textarea.focus();
                textarea.dispatchEvent(new Event("input"));
                sendMessage();
            });
        });
    };

    const renderMarkdown = (markdownText) =>
        window.marked ? window.marked.parse(markdownText || "") : escapeHtml(markdownText || "").replace(/\n/g, "<br>");

    const formatPlainAssistantText = (rawText) => {
        const source = String(rawText || "").trim();
        if (!source) {
            return "";
        }

        if (source === STRICT_NO_RESULT_MESSAGE || source === NO_RESULT_MESSAGE) {
            return source;
        }

        const hasMarkdownStructure = /(^|\n)\s{0,3}(#{1,6}\s+|[-*+]\s+|\d+\.\s+)/m.test(source);
        if (hasMarkdownStructure) {
            return source;
        }

        const paragraphLines = source.split(/\n+/).map((line) => line.trim()).filter(Boolean);
        let bulletItems = paragraphLines;

        if (paragraphLines.length === 1) {
            const sentenceParts = paragraphLines[0]
                .split(/(?<=[.!?])\s+/)
                .map((part) => part.trim())
                .filter(Boolean);
            if (sentenceParts.length > 1) {
                bulletItems = sentenceParts;
            }
        }

        if (!bulletItems.length) {
            return `## Answer\n${source}`;
        }

        const bullets = bulletItems.map((item) => `- ${item}`).join("\n");
        return `## Answer\n${bullets}`;
    };

    const sectionClassFromLabel = (label) => {
        const key = String(label || "").toLowerCase();
        if (key.includes("definition")) return "is-definition";
        if (key.includes("explanation")) return "is-explanation";
        if (key.includes("key")) return "is-key-points";
        if (key.includes("example")) return "is-example";
        if (key.includes("conclusion")) return "is-conclusion";
        if (key.includes("reference")) return "is-references";
        return "is-main-answer";
    };

    const renderAssistantSections = (markdownText) => {
        const source = formatPlainAssistantText(markdownText);
        if (!source) {
            return "";
        }
        const headingRegex = /^#{2,6}\s+(.+?)\s*$/gim;
        const matches = [...source.matchAll(headingRegex)];
        if (!matches.length) {
            return renderMarkdown(source);
        }

        const sections = [];
        for (let i = 0; i < matches.length; i += 1) {
            const title = (matches[i][1] || "Section").trim();
            const normalized = normalizeSectionTitle(title);
            const start = matches[i].index + matches[i][0].length;
            const end = i + 1 < matches.length ? matches[i + 1].index : source.length;
            const body = source.slice(start, end).trim() || "No content available.";
            sections.push({ label: normalized.label || title, body, className: normalized.className || sectionClassFromLabel(title) });
        }

        const cards = sections.map((section) => (
            `<section class="chat-answer-card ${section.className}">` +
                `<h4 class="chat-answer-card-title">${escapeHtml(section.label)}</h4>` +
                `<div class="chat-answer-card-body">${renderMarkdown(section.body)}</div>` +
            `</section>`
        ));

        return `<div class="chat-answer-sections">${cards.join("")}</div>`;
    };

    const toSourceLabel = (reference) => {
        const row = reference || {};
        if (row.pdf_title && row.page_number) {
            return `${row.pdf_title} → Page ${row.page_number}`;
        }
        const raw = String(row.label || "").trim();
        if (!raw) {
            return "Not available";
        }
        return raw.replace(/\s*-\s*Page\s+/i, " → Page ");
    };

    const extractPageNumber = (reference) => {
        const value = reference?.page_number;
        if (Number.isFinite(Number(value))) {
            return String(value);
        }
        const label = String(reference?.label || "");
        const match = label.match(/page\s+(\d+)/i);
        return match ? match[1] : "";
    };

    const toOriginSegments = (meta) => {
        const references = Array.isArray(meta?.reference_previews) ? meta.reference_previews : [];
        const retrieval = Array.isArray(meta?.retrieval_previews) ? meta.retrieval_previews : [];
        const primary = references[0] || retrieval[0] || {};

        const subject = String(primary.subject_name || meta?.subject_name || "").trim();
        const unit = String(primary.unit_name || primary.unit_label || meta?.unit_name || "").trim();
        const page = extractPageNumber(primary);
        const pdf = String(primary.pdf_title || meta?.pdf_title || "").trim();

        return { subject, unit, page, pdf };
    };

    const buildSourceDisplay = (meta) => {
        const answerFrom = String(meta?.answer_from || "").trim();
        const segments = toOriginSegments(meta);
        const pathParts = [];
        if (segments.subject) {
            pathParts.push(`<span class="chat-source-chip">Subject: ${escapeHtml(segments.subject)}</span>`);
        }
        if (segments.unit) {
            pathParts.push(`<span class="chat-source-chip">Unit: ${escapeHtml(segments.unit)}</span>`);
        }
        if (segments.page) {
            pathParts.push(`<span class="chat-source-chip">Page: ${escapeHtml(segments.page)}</span>`);
        }

        if (!pathParts.length && !segments.pdf && !answerFrom) {
            return "";
        }

        const originPath = pathParts.length
            ? `<div class="chat-source-path">${pathParts.join('<span class="chat-source-sep">→</span>')}</div>`
            : "";
        const pdfLine = segments.pdf
            ? `<div class="chat-source-pdf">Source (PDF): ${escapeHtml(segments.pdf)}</div>`
            : "";
        const confidenceLabel = String(meta?.confidence_label || "").trim();
        const confidenceLine = confidenceLabel
            ? `<div class="chat-source-origin">Confidence: ${escapeHtml(confidenceLabel)}</div>`
            : "";

        return [
            '<div class="chat-answer-from-badge" role="status" aria-label="Answer source details">',
            '<span class="chat-answer-from-title">ANSWER FROM</span>',
            originPath,
            pdfLine,
            confidenceLine,
            '</div>'
        ].join("");
    };

    const renderMessageBubble = (message, index) => {
        const container = document.createElement("article");
        container.className = `chat-msg ${message.role}`;
        container.dataset.messageIndex = String(index);
        if (message.id) {
            container.dataset.messageId = String(message.id);
        }

        const wrapper = document.createElement("div");
        wrapper.className = "chat-bubble-wrap";

        const bubble = document.createElement("div");
        bubble.className = "chat-bubble";
        if (message.role === "assistant") {
            if (message.streaming) {
                const markdownSource = `${message.content}<span class="chat-cursor">▍</span>`;
                bubble.innerHTML = renderMarkdown(markdownSource);
            } else {
                bubble.innerHTML = renderAssistantSections(message.content);
                const sourceDisplay = buildSourceDisplay(message.meta || null);
                if (sourceDisplay) {
                    bubble.innerHTML += sourceDisplay;
                }
            }
        } else {
            bubble.textContent = message.content;
        }

        if (message.role === "assistant" && !message.streaming) {
            const actions = document.createElement("div");
            actions.className = "chat-msg-actions";
            const copyBtn = document.createElement("button");
            copyBtn.type = "button";
            copyBtn.className = "btn btn-outline-secondary btn-sm chat-copy-btn";
            copyBtn.innerHTML = '<i class="bi bi-clipboard" aria-hidden="true"></i><span>Copy</span>';
            copyBtn.addEventListener("click", async (event) => {
                event.preventDefault();
                const rawText = String(message.content || "").trim();
                if (!rawText) {
                    return;
                }
                try {
                    await navigator.clipboard.writeText(rawText);
                    const label = copyBtn.querySelector("span");
                    if (label) {
                        label.textContent = "Copied";
                        window.setTimeout(() => {
                            label.textContent = "Copy";
                        }, 1200);
                    }
                } catch (error) {
                    return;
                }
            });
            actions.appendChild(copyBtn);
            bubble.appendChild(actions);

            const diagrams = Array.isArray(message.meta?.diagrams) ? message.meta.diagrams : [];
            if (diagrams.length) {
                const diagramsWrap = document.createElement("div");
                diagramsWrap.className = "chat-inline-diagrams";
                const heading = document.createElement("h4");
                heading.textContent = "Related Diagrams";
                diagramsWrap.appendChild(heading);
                diagrams.forEach((url) => {
                    const img = document.createElement("img");
                    img.className = "chat-inline-diagram-image";
                    img.src = String(url || "");
                    img.alt = "Related diagram from referenced PDF page";
                    diagramsWrap.appendChild(img);
                });
                bubble.appendChild(diagramsWrap);
            }

            const suggestions = Array.isArray(message.meta?.follow_up_suggestions)
                ? message.meta.follow_up_suggestions
                : [];
            if (suggestions.length) {
                const suggestionsWrap = document.createElement("div");
                suggestionsWrap.className = "chat-followups";
                const heading = document.createElement("h4");
                heading.textContent = "Follow-up Questions";
                suggestionsWrap.appendChild(heading);

                suggestions.slice(0, 3).forEach((item) => {
                    const button = document.createElement("button");
                    button.type = "button";
                    button.className = "btn btn-outline-secondary btn-sm";
                    button.setAttribute("data-suggested-question", String(item || ""));
                    button.textContent = String(item || "");
                    suggestionsWrap.appendChild(button);
                });
                bubble.appendChild(suggestionsWrap);
            }
        }

        const time = document.createElement("span");
        time.className = "chat-time";
        time.textContent = message.timestamp || nowTime();

        wrapper.appendChild(bubble);
        wrapper.appendChild(time);
        container.appendChild(wrapper);
        return container;
    };

    const renderMessages = () => {
        const thread = getActiveThread();
        messageScroller.innerHTML = "";
        if (!thread || !thread.messages.length) {
            if (emptyState) {
                messageScroller.appendChild(emptyState);
            }
            renderSourcePanel(null);
            return;
        }

        const threshold = 15;
        const messages = thread.messages.length > threshold ? thread.messages.slice(-threshold) : thread.messages;
        const offset = thread.messages.length - messages.length;

        if (offset > 0) {
            const loadOlder = document.createElement("button");
            loadOlder.type = "button";
            loadOlder.className = "btn btn-outline-secondary btn-sm";
            loadOlder.textContent = `Showing last ${messages.length} messages`;
            messageScroller.appendChild(loadOlder);
        }

        messages.forEach((message, idx) => {
            const node = renderMessageBubble(message, offset + idx);
            messageScroller.appendChild(node);
        });

        attachMessageClickHandlers();
        scrollToLatestMessage(demoMode);

        const latestAssistant = [...thread.messages].reverse().find((message) => message.role === "assistant" && message.meta);
        if (detailsPanel && detailsToggle) {
            renderSourcePanel(latestAssistant ? latestAssistant.meta : null);
        }
    };

    const updateStreamingAssistantNode = (assistantMessage) => {
        if (!assistantMessage || !assistantMessage.id || !messageScroller) {
            return false;
        }
        const bubble = messageScroller.querySelector(`.chat-msg[data-message-id="${assistantMessage.id}"] .chat-bubble`);
        if (!bubble) {
            return false;
        }
        bubble.innerHTML = renderMarkdown(`${assistantMessage.content}<span class="chat-cursor">▍</span>`);
        return true;
    };

    const renderSourcePanel = (meta) => {
        const highlightReferencePages = (label) =>
            escapeHtml(label || "").replace(/(Page\s+\d+)/gi, '<span class="reference-highlight">$1</span>');

        if (!panelConfidence || !panelReferences) {
            return;
        }

        if (!meta) {
            if (panelConfidence) {
                panelConfidence.innerHTML = '<span class="chat-confidence-badge is-low">Low</span>';
            }
            if (panelReferences) {
                panelReferences.innerHTML = "References appear here.";
            }
            return;
        }

        if (panelConfidence) {
            const confidence = resolveConfidence(meta);
            const label = confidence.charAt(0).toUpperCase() + confidence.slice(1);
            panelConfidence.innerHTML = `<span class="chat-confidence-badge is-${confidence}">${escapeHtml(label)}</span>`;
        }

        const first = (meta.structured_response || [])[0] || null;

        // References
        const references = first?.reference_previews || [];
        const retrievalPreviews = meta.retrieval_previews || [];
        if (panelReferences && (references.length || retrievalPreviews.length)) {
            const referenceHtml = references.map((reference) => {
                const label = highlightReferencePages(reference.label || "Reference");
                const preview = escapeHtml(reference.preview || "");
                const url = escapeHtml(reference.pdf_url || "");
                return `<a class="chat-ref-link" href="${url}" data-open-source><strong>${label}</strong><div>${preview}</div></a>`;
            }).join("");
            const retrievalHtml = retrievalPreviews.map((item) => {
                const label = highlightReferencePages(item.label || "Retrieved chunk");
                const excerpt = escapeHtml(item.excerpt || "");
                const url = escapeHtml(item.pdf_url || "");
                return `<a class="chat-ref-link" href="${url}" data-open-source><strong>${label}</strong><div>${excerpt}</div></a>`;
            }).join("");
            panelReferences.innerHTML = referenceHtml + retrievalHtml;
        } else if (panelReferences) {
            panelReferences.innerHTML = "No references available.";
        }

        attachMessageClickHandlers();
    };

    const setThinking = (visible) => {
        thinkingEl.classList.toggle("is-visible", visible);
        thinkingEl.setAttribute("aria-hidden", visible ? "false" : "true");
    };

    const getCsrfToken = () => {
        if (!composer) {
            return "";
        }
        const hidden = composer.querySelector("input[name='csrfmiddlewaretoken']");
        return hidden ? hidden.value : "";
    };

    const SLOW_RESPONSE_MS = 2000;
    const thinkingTextEl = thinkingEl ? thinkingEl.querySelector("span:last-child") : null;
    const originalThinkingText = thinkingTextEl ? thinkingTextEl.textContent : "Thinking...";
    const sendBtnLabelEl = sendBtn ? sendBtn.querySelector("span") : null;
    const originalSendBtnLabel = sendBtnLabelEl ? sendBtnLabelEl.textContent : "Send";

    const streamAssistantResponse = async (thread, assistantMessage, payload, retryCount = 0) => {
        setThinking(true);
        if (thinkingTextEl) thinkingTextEl.textContent = originalThinkingText;
        state.isStreaming = true;
        const requestStart = performance.now();
        // After 2 s without a response, show a concise fallback status.
        const slowTimer = setTimeout(() => {
            if (thinkingTextEl) thinkingTextEl.textContent = "Still thinking...";
        }, SLOW_RESPONSE_MS);

        const body = new URLSearchParams();
        body.set("chat_id", payload.chatId || "");
        body.set("question", payload.question);
        body.set("subject_id", payload.subjectId || "");
        body.set("lesson_id", payload.lessonId || "");
        body.set("unit_id", payload.unitId || "");
        body.set("pdf_id", payload.pdfId || "");
        if (payload.strictMode) {
            body.set("strict_mode", "on");
        }

        let response;
        try {
            response = await fetch(buildScopedRequestUrl(streamUrl, payload), {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
                    "X-CSRFToken": getCsrfToken()
                },
                body: body.toString()
            });

            if (!response.ok || !response.body) {
                throw new Error("Streaming failed.");
            }
        } catch (error) {
            clearTimeout(slowTimer);
            if (thinkingTextEl) thinkingTextEl.textContent = originalThinkingText;
            throw error;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) {
                break;
            }
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed) {
                    continue;
                }
                let eventData;
                try {
                    eventData = JSON.parse(trimmed);
                } catch (error) {
                    continue;
                }

                if (eventData.type === "token") {
                    if (!assistantMessage._firstTokenLoggedAt) {
                        assistantMessage._firstTokenLoggedAt = performance.now();
                    }
                    assistantMessage.content += eventData.token || "";
                    if (!updateStreamingAssistantNode(assistantMessage)) {
                        renderMessages();
                    }
                    if (demoMode) {
                        scrollToLatestMessage(true);
                        await delay(22);
                    }
                } else if (eventData.type === "error") {
                    clearTimeout(slowTimer);
                    if (thinkingTextEl) thinkingTextEl.textContent = originalThinkingText;
                    setThinking(false);
                    assistantMessage.content = eventData.message || "Unable to generate answer.";
                    assistantMessage.streaming = false;
                    renderMessages();
                } else if (eventData.type === "done") {
                    clearTimeout(slowTimer);
                    if (thinkingTextEl) thinkingTextEl.textContent = originalThinkingText;
                    setThinking(false);
                    const payloadData = eventData.payload || {};
                    assistantMessage.streaming = false;
                    assistantMessage.content = payloadData.markdown || payloadData.bot_response || assistantMessage.content || "## Main Answer\nNo response received.";
                    assistantMessage.meta = payloadData || null;
                    assistantMessage.timestamp = nowTime();
                    thread.updatedAt = new Date().toISOString();
                    renderMessages();
                    if (detailsPanel && detailsToggle) {
                        renderSourcePanel(assistantMessage.meta);
                    }
                    scrollToLatestMessage(true);
                }
            }
        }

        clearTimeout(slowTimer);
        if (thinkingTextEl) thinkingTextEl.textContent = originalThinkingText;
        if (assistantMessage.streaming) {
            assistantMessage.streaming = false;
            setThinking(false);
            assistantMessage.content = assistantMessage.content || "## Main Answer\nNo response received.";
            renderMessages();
        }
    };

    const sendMessageJson = async (thread, assistantMessage, payload) => {
        const csrfToken = getCsrfToken();
        const response = await fetch(buildScopedRequestUrl(chatUrl, payload), {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
                "X-Requested-With": "XMLHttpRequest"
            },
            body: JSON.stringify({
                message: payload.question,
                question: payload.question,
                scope: normalizeScope(payload.scope || "global"),
                subject_id: payload.subjectId || "",
                lesson_id: payload.lessonId || "",
                unit_id: payload.unitId || "",
                pdf_id: payload.pdfId || "",
                regulation: payload.regulation || "",
                branch: payload.branch || "",
                semester: payload.semester || "",
                strict_mode: !!payload.strictMode
            })
        });

        if (!response.ok) {
            throw new Error(`Chat request failed with status ${response.status}`);
        }

        const data = await response.json();
        assistantMessage.streaming = false;
        assistantMessage.content = data.markdown || data.bot_response || "## Main Answer\nNo response received.";
        assistantMessage.meta = data || null;
        assistantMessage.timestamp = nowTime();
        thread.updatedAt = new Date().toISOString();
        renderMessages();
        if (detailsPanel && detailsToggle) {
            renderSourcePanel(assistantMessage.meta);
        }
        scrollToLatestMessage(true);
    };

    const sendMessage = async () => {
        if (!textarea) {
            return;
        }
        const text = (textarea.value || "").trim();
        if (!text || state.isStreaming || state.isSending) {
            return;
        }
        const selectedScope = normalizeConversationScope();
        state.isSending = true;
        state.isStreaming = true;
        setThinking(true);
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.setAttribute("aria-busy", "true");
            if (sendBtnLabelEl) {
                sendBtnLabelEl.textContent = "Searching syllabus...";
            }
        }

        let thread = getActiveThread();
        if (!thread) {
            thread = createThread(deriveTitleFromQuestion(text));
        }

        const userMessage = {
            role: "user",
            content: text,
            timestamp: nowTime()
        };
        upsertThreadMessage(thread.id, userMessage);

        const assistantMessage = {
            role: "assistant",
            content: "",
            timestamp: nowTime(),
            streaming: true,
            meta: null
        };
        upsertThreadMessage(thread.id, assistantMessage);

        textarea.value = "";
        textarea.style.height = "42px";
        saveThreads();
        renderThreadList();
        renderMessages();
        scrollToLatestMessage(true);

        try {
            const payload = {
                chatId: thread.id,
                question: text,
                scope: selectedScope,
                regulation: "",
                branch: "",
                semester: "",
                subjectId: subjectSelect ? subjectSelect.value : "",
                lessonId: "",
                unitId: "",
                pdfId: "",
                strictMode: strictInput ? !!strictInput.checked : true
            };
            try {
                await streamAssistantResponse(thread, assistantMessage, payload);
            } catch (streamError) {
                assistantMessage.streaming = true;
                assistantMessage.content = "";
                await sendMessageJson(thread, assistantMessage, payload);
            }
        } catch (error) {
            assistantMessage.streaming = false;
            assistantMessage.content = NO_RESULT_MESSAGE;
            renderMessages();
            scrollToLatestMessage(true);
        } finally {
            state.isSending = false;
            state.isStreaming = false;
            setThinking(false);
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.removeAttribute("aria-busy");
                if (sendBtnLabelEl) {
                    sendBtnLabelEl.textContent = originalSendBtnLabel;
                }
            }
            saveThreads();
            renderThreadList();
        }
    };

    const hydrateFromServerHistory = async () => {
        if (state.loadingHistory || !state.hasHistoryNext) {
            return;
        }
        state.loadingHistory = true;
        updateLoadMoreState();

        try {
            const response = await fetch(`${historyUrl}?page=${state.historyPage}&page_size=20`, { credentials: "same-origin" });
            if (!response.ok) {
                state.hasHistoryNext = false;
                return;
            }
            const data = await response.json();
            const existingIds = new Set(state.threads.map((thread) => thread.id));

            (data.items || []).forEach((item) => {
                const threadId = item.thread_id || `query-${item.created_at}`;
                if (existingIds.has(threadId)) {
                    return;
                }
                state.threads.push({
                    id: threadId,
                    title: item.title || "Past chat",
                    createdAt: item.created_at,
                    updatedAt: item.created_at,
                    scope: normalizeScope(item.scope || "global"),
                    regulation: item.regulation || "",
                    branch: item.branch || "",
                    semester: item.semester ? String(item.semester) : "",
                    subjectId: item.subject_id ? String(item.subject_id) : "",
                    lessonId: item.lesson_id ? String(item.lesson_id) : "",
                    unitId: item.unit_id ? String(item.unit_id) : "",
                    pdfId: item.reference_pdf_id ? String(item.reference_pdf_id) : "",
                    strictMode: !!item.strict_mode,
                    messages: [
                        {
                            role: "user",
                            content: item.question || "",
                            timestamp: new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                        },
                        {
                            role: "assistant",
                            content: item.response_text || "## Main Answer\nNo response stored.",
                            timestamp: new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                            meta: null
                        }
                    ]
                });
            });

            state.hasHistoryNext = !!data.has_next;
            state.historyPage = (data.page || state.historyPage) + 1;
            saveThreads();
            renderThreadList();
        } catch (error) {
            return;
        } finally {
            state.loadingHistory = false;
            updateLoadMoreState();
        }
    };

    if (composer) {
        composer.addEventListener("submit", (event) => {
            event.preventDefault();
            sendMessage();
        });
    }

    // Button uses native submit behavior; submit listener is the single send path.

    if (messageInput) {
        messageInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                if (composer && typeof composer.requestSubmit === "function") {
                    composer.requestSubmit();
                } else {
                    sendMessage();
                }
            }
        });

    }

    if (textarea) {
        textarea.addEventListener("input", () => {
            textarea.style.height = "42px";
            textarea.style.height = `${Math.min(textarea.scrollHeight, 140)}px`;
        });
    }

    if (newChatBtn) {
        newChatBtn.addEventListener("click", () => {
            state.activeThreadId = null;
            createThread();
        });
    }

    if (clearChatBtn) {
        clearChatBtn.addEventListener("click", () => {
            const thread = getActiveThread();
            if (!thread) {
                return;
            }
            if (!window.confirm("Clear messages in this conversation?")) {
                return;
            }
            thread.messages = [];
            thread.title = "New Chat";
            thread.updatedAt = new Date().toISOString();
            saveThreads();
            renderThreadList();
            renderMessages();
        });
    }

    if (scopeSelect) {
        scopeSelect.addEventListener("change", () => {
            applyScopeVisibility();
        });
    }
    if (subjectSelect) {
        subjectSelect.addEventListener("change", () => {
            renderLessonOptions(subjectSelect.value || "");
            if (lessonSelect) {
                lessonSelect.value = "";
            }
            clearScopeError();
        });
    }
    if (lessonSelect) {
        lessonSelect.addEventListener("change", clearScopeError);
    }
    if (unitSelect) {
        unitSelect.addEventListener("change", clearScopeError);
    }
    if (pdfSelect) {
        pdfSelect.addEventListener("change", clearScopeError);
    }
    if (loadHistoryBtn) {
        loadHistoryBtn.addEventListener("click", hydrateFromServerHistory);
    }

    if (sidebarToggle) {
        sidebarToggle.addEventListener("click", toggleSidebar);
    }

    if (detailsToggle && detailsPanel) {
        detailsToggle.addEventListener("click", toggleDetails);
    }

    window.addEventListener("resize", applySidebarState);

    if (sourceModalEl) {
        sourceModalEl.addEventListener("hidden.bs.modal", () => {
            if (sourceModalIframe) {
                sourceModalIframe.src = "about:blank";
            }
        });
    }

    loadThreads();
    renderLessonOptions(subjectSelect ? subjectSelect.value : "");
    applyScopeVisibility();
    loadSidebarState();
    loadDetailsState();
    applySidebarState();
    if (detailsPanel && detailsToggle) {
        applyDetailsState();
    }
    if (!state.threads.length) {
        renderThreadList();
        renderMessages();
    } else {
        renderThreadList();
        renderMessages();
    }
    updateLoadMoreState();
    hydrateFromServerHistory();
})();
