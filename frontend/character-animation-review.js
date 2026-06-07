(function () {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const state = {
    catalog: [],
    hats: [],
    hatFit: {},
    overrides: {},
    votes: {},
    dimensions: {},
    frameDeltas: {},
    activeId: "",
    hatId: "hat_16",
    paused: false,
    frame: 0,
    timer: null,
  };

  function esc(value) {
    return String(value ?? "").replace(/[&<>"]/g, (char) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;",
    }[char]));
  }

  function setHtml(target, html) {
    const template = document.createElement("template");
    template.innerHTML = String(html ?? "");
    template.content.querySelectorAll("script, iframe, object, embed, link, meta").forEach((node) => node.remove());
    target.replaceChildren(template.content.cloneNode(true));
  }

  function parseCatalog(text) {
    const match = text.match(/const CHARACTER_CATALOG = \[([\s\S]*?)\];/)
      || text.match(/\w+=\[(\{id:"char_[\s\S]*?\})\],\w+=Object\.fromEntries\(\w+\.map/);
    if (!match) throw new Error("CHARACTER_CATALOG not found in app.js");
    return [...match[1].matchAll(/\{([^{}]+)\}/g)].map((entry) => {
      const item = {};
      for (const pair of entry[1].matchAll(/(\w+):\s*(?:"([^"]*)"|'([^']*)'|(!0|!1|true|false|-?(?:\d+(?:\.\d*)?|\.\d+)))/g)) {
        const token = pair[2] || pair[3] || pair[4];
        if (token === "true" || token === "!0") item[pair[1]] = true;
        else if (token === "false" || token === "!1") item[pair[1]] = false;
        else if (/^-?(?:\d+(?:\.\d*)?|\.\d+)$/.test(token)) item[pair[1]] = Number(token);
        else item[pair[1]] = token;
      }
      return item;
    }).filter((item) => item.id && item.file);
  }

  function parseHatFit(text) {
    const fit = {};
    for (const entry of text.matchAll(/(hat_\d+):\s*\{\s*bottom:\s*(-?(?:\d+(?:\.\d*)?|\.\d+)),\s*center:\s*(-?(?:\d+(?:\.\d*)?|\.\d+))\s*\}/g)) {
      fit[entry[1]] = { bottom: Number(entry[2]), center: Number(entry[3]) };
    }
    return fit;
  }

  function character() {
    return state.catalog.find((item) => item.id === state.activeId);
  }

  function characterConfig(item = character(), frame = state.frame) {
    if (!item) return null;
    const override = state.overrides[item.id]?.[state.hatId] || {};
    const config = { ...item, ...override };
    const delta = state.frameDeltas[item.id]?.[frame];
    if (delta) {
      config.opaqueTop = Number(config.opaqueTop || 0) + delta.topDelta * Number(config.hatTrackY ?? 1);
      config.opaqueCenter = Number(config.opaqueCenter || Number(config.frameWidth || 32) / 2) + delta.centerDelta * Number(config.hatTrackX ?? 1);
    }
    return config;
  }

  function voteFor(id = state.activeId, hatId = state.hatId) {
    return state.votes[id]?.[hatId] || null;
  }

  function voteClass(id) {
    const vote = voteFor(id);
    return vote?.status === "ok" ? "ok" : vote?.status === "bad" ? "bad" : "";
  }

  function setStatus(message) {
    $("#status").textContent = message;
  }

  function saveLocal() {
    try { localStorage.setItem("petpro_hat_animation_review", JSON.stringify(state.votes)); } catch { setStatus("Local backup недоступен"); }
  }

  function zoomFor(item) {
    return Math.max(2, Math.min(8, Math.floor(176 / Number(item.frameHeight || 32))));
  }

  function comboLayout(item, frame, boxWidth, boxHeight, zoom) {
    const config = characterConfig(item, frame) || item;
    const frameWidth = Number(config.frameWidth || 32);
    const frameHeight = Number(config.frameHeight || 32);
    const spriteWidth = frameWidth * zoom;
    const spriteHeight = frameHeight * zoom;
    const spriteLeft = (boxWidth - spriteWidth) / 2;
    const spriteTop = (boxHeight - spriteHeight) / 2;
    const hatSize = frameHeight * zoom * Number(config.hatScale || 1);
    const headTop = spriteTop + Number(config.opaqueTop || 0) * zoom;
    const headX = boxWidth / 2
      + (Number(config.opaqueCenter || frameWidth / 2) - frameWidth / 2) * zoom
      + Number(config.hatOffsetX || 0) * zoom;
    const boxHatHeight = hatSize * 0.72;
    const fit = state.hatFit[state.hatId] || { bottom: 10, center: 0 };
    const flip = config.hatFlip ? -1 : 1;
    return {
      size: hatSize,
      left: headX - hatSize / 2 + (-Number(fit.center || 0) / 30) * hatSize * flip,
      top: headTop - boxHatHeight + Math.min(7, 2.5 * zoom)
        + Number(config.hatOffsetY || 0) * zoom + boxHatHeight - hatSize
        + (Number(fit.bottom || 0) / 30) * hatSize,
      flip,
    };
  }

  function applySpriteVars(target, item, frame, thumb = false) {
    target.style.setProperty("--sprite-url", `url("assets/characters/${item.file}")`);
    target.style.setProperty("--frame-w", Number(item.frameWidth || 32));
    target.style.setProperty("--frame-h", Number(item.frameHeight || 32));
    target.style.setProperty("--frame", frame);
    target.style.setProperty("--zoom", zoomFor(item));
    target.style.setProperty("--thumb-zoom", Math.max(1, Math.min(4, Math.floor(48 / Number(item.frameHeight || 32)))));
  }

  function applyHatVars(target, layout) {
    target.src = `assets/hats/${state.hatId}.png`;
    target.style.setProperty("--hat-size", `${Math.round(layout.size)}px`);
    target.style.setProperty("--hat-left", `${Math.round(layout.left)}px`);
    target.style.setProperty("--hat-top", `${Math.round(layout.top)}px`);
    target.style.setProperty("--hat-flip", String(layout.flip));
  }

  function renderPreview() {
    const item = character();
    if (!item) return;
    const frames = Number(item.frames || 1);
    state.frame = Math.max(0, Math.min(frames - 1, state.frame));
    applySpriteVars($("#sprite"), item, state.frame);
    applyHatVars($("#hat"), comboLayout(item, state.frame, 260, 220, zoomFor(item)));
    $("#frames").querySelectorAll("[data-frame]").forEach((node) => {
      node.dataset.on = String(Number(node.dataset.frame) === state.frame);
    });
  }

  function renderList() {
    const query = $("#search").value.trim().toLowerCase();
    const filtered = state.catalog.filter((item) => {
      const label = `${item.id} ${item.name} ${item.file}`.toLowerCase();
      return !query || label.includes(query);
    });
    setHtml($("#items"), filtered.map((item) => `
      <button class="item" data-id="${esc(item.id)}" data-on="${item.id === state.activeId}">
        <img src="assets/characters/${esc(item.file)}" alt="">
        <span><span class="name">${esc(item.name || item.id)}</span><span class="file">${esc(item.file)}</span></span>
        <span class="vote-dot ${voteClass(item.id)}"></span>
      </button>
    `).join(""));
    $("#count").textContent = String(state.catalog.length);
  }

  function renderHats() {
    setHtml($("#hats"), state.hats.map((id) => `
      <button class="hat-option" data-hat="${esc(id)}" data-on="${id === state.hatId}" title="${esc(id)}">
        <img src="assets/hats/${esc(id)}.png" alt="">
      </button>
    `).join(""));
  }

  function renderFrames(item) {
    const frames = Number(item.frames || 1);
    setHtml($("#frames"), Array.from({ length: frames }, (_, frame) => `
      <button class="frame" data-frame="${frame}" data-on="${frame === state.frame}">
        <span class="mini-combo">
          <span class="frame-sprite"></span>
          <img class="frame-hat" alt="">
        </span>
      </button>
    `).join(""));
    $("#frames").querySelectorAll(".frame").forEach((button) => {
      const frame = Number(button.dataset.frame);
      const sprite = button.querySelector(".frame-sprite");
      const hat = button.querySelector(".frame-hat");
      applySpriteVars(sprite, item, frame, true);
      applyHatVars(hat, comboLayout(item, frame, 64, 64, Math.max(1, Math.min(4, Math.floor(48 / Number(item.frameHeight || 32))))));
    });
  }

  function renderMeta(item) {
    const dim = state.dimensions[item.id];
    const expectedWidth = Number(item.frameWidth || 32) * Number(item.frames || 1);
    const expectedHeight = Number(item.frameHeight || 32);
    const override = state.overrides[item.id]?.[state.hatId] ? "есть override" : "base";
    const sizeText = dim ? `${dim.width}x${dim.height}` : "loading";
    setHtml($("#meta"), `
      <div><b>${esc(item.name || item.id)}</b> + ${esc(state.hatId)}</div>
      <div>${esc(item.id)}</div>
      <div>file: ${esc(item.file)}</div>
      <div>frame: ${Number(item.frameWidth || 32)}x${Number(item.frameHeight || 32)} / ${Number(item.frames || 1)} frames</div>
      <div>png: ${esc(sizeText)} / expected ${expectedWidth}x${expectedHeight}</div>
      <div>hat placement: ${override}</div>
    `);
  }

  function renderStats() {
    const ok = state.catalog.filter((item) => voteFor(item.id)?.status === "ok").length;
    const bad = state.catalog.filter((item) => voteFor(item.id)?.status === "bad").length;
    const todo = state.catalog.length - ok - bad;
    setHtml($("#stats"), `
      <div class="stat"><b>${ok}</b><br>ok</div>
      <div class="stat"><b>${bad}</b><br>bad</div>
      <div class="stat"><b>${todo}</b><br>todo</div>
    `);
    $("#progress").textContent = `${state.hatId}: ${ok + bad}/${state.catalog.length}`;
  }

  function renderActive() {
    const item = character();
    if (!item) return;
    state.frame = Math.min(state.frame, Number(item.frames || 1) - 1);
    $("#title").textContent = `${item.name || item.id} + ${state.hatId}`;
    $("#play").textContent = state.paused ? "Играть" : "Пауза";
    $("#note").value = voteFor()?.note || "";
    const vote = voteFor();
    $("#voteLabel").textContent = vote?.status === "ok" ? "правильно" : vote?.status === "bad" ? "неправильно" : "не проверено";
    renderMeta(item);
    renderHats();
    renderFrames(item);
    renderList();
    renderStats();
    renderPreview();
    restartTimer();
  }

  function restartTimer() {
    clearInterval(state.timer);
    const item = character();
    const frames = Number(item?.frames || 1);
    if (state.paused || frames <= 1) return;
    state.timer = setInterval(() => {
      state.frame = (state.frame + 1) % frames;
      renderPreview();
    }, Math.max(50, Math.round(1000 * Number(item.frameDuration || 1.05) / frames)));
  }

  function select(id) {
    state.activeId = id;
    state.frame = 0;
    state.paused = false;
    renderActive();
  }

  function move(offset) {
    const index = state.catalog.findIndex((item) => item.id === state.activeId);
    select(state.catalog[(index + offset + state.catalog.length) % state.catalog.length].id);
  }

  function mark(status) {
    const item = character();
    if (!item) return;
    state.votes[item.id] = state.votes[item.id] || {};
    state.votes[item.id][state.hatId] = { status, note: $("#note").value.trim(), updatedAt: new Date().toISOString() };
    saveLocal();
    renderActive();
    setStatus(status === "ok" ? "Отмечено: шапка двигается правильно" : "Отмечено: шапку нужно править");
  }

  async function saveFile() {
    try {
      const response = await fetch("/save-character-animation-review", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(state.votes),
      });
      if (!response.ok) throw new Error(await response.text());
      setStatus("JSON записан в frontend/character-animation-review.json");
    } catch {
      setStatus("Не удалось записать файл. Запусти через scripts/hat_tuner_server.py");
    }
  }

  function bind() {
    $("#search").addEventListener("input", renderList);
    $("#items").addEventListener("click", (event) => {
      const button = event.target.closest("[data-id]");
      if (button) select(button.dataset.id);
    });
    $("#hats").addEventListener("click", (event) => {
      const button = event.target.closest("[data-hat]");
      if (!button) return;
      state.hatId = button.dataset.hat;
      state.frame = 0;
      renderActive();
    });
    $("#frames").addEventListener("click", (event) => {
      const button = event.target.closest("[data-frame]");
      if (!button) return;
      state.frame = Number(button.dataset.frame || 0);
      state.paused = true;
      renderActive();
    });
    $("#play").addEventListener("click", () => {
      state.paused = !state.paused;
      renderActive();
    });
    $("#prev").addEventListener("click", () => move(-1));
    $("#next").addEventListener("click", () => move(1));
    $("#markOk").addEventListener("click", () => mark("ok"));
    $("#markBad").addEventListener("click", () => mark("bad"));
    $("#clearVote").addEventListener("click", () => {
      if (state.votes[state.activeId]) delete state.votes[state.activeId][state.hatId];
      saveLocal();
      renderActive();
      setStatus("Оценка сброшена");
    });
    $("#saveFile").addEventListener("click", saveFile);
    $("#note").addEventListener("change", () => {
      const vote = voteFor();
      if (!vote) return;
      vote.note = $("#note").value.trim();
      vote.updatedAt = new Date().toISOString();
      saveLocal();
    });
  }

  function loadImage(src) {
    return new Promise((resolve) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => resolve(null);
      image.src = src;
    });
  }

  async function measureFrames(item) {
    const image = await loadImage(`assets/characters/${item.file}`);
    if (!image) return;
    state.dimensions[item.id] = { width: image.naturalWidth, height: image.naturalHeight };
    const frameWidth = Number(item.frameWidth || 32);
    const frameHeight = Number(item.frameHeight || 32);
    const frames = Number(item.frames || 1);
    const canvas = document.createElement("canvas");
    canvas.width = frameWidth * frames;
    canvas.height = frameHeight;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(image, 0, 0);
    const bounds = [];
    for (let frame = 0; frame < frames; frame += 1) {
      const data = ctx.getImageData(frame * frameWidth, 0, frameWidth, frameHeight).data;
      let left = frameWidth, right = -1, top = frameHeight;
      for (let y = 0; y < frameHeight; y += 1) for (let x = 0; x < frameWidth; x += 1) {
        if (data[(y * frameWidth + x) * 4 + 3] > 8) {
          left = Math.min(left, x); right = Math.max(right, x); top = Math.min(top, y);
        }
      }
      bounds.push(right >= left ? { top, center: (left + right) / 2 } : { top: 0, center: frameWidth / 2 });
    }
    const base = bounds[0] || { top: 0, center: frameWidth / 2 };
    state.frameDeltas[item.id] = bounds.map((bound) => ({
      topDelta: bound.top - base.top,
      centerDelta: bound.center - base.center,
    }));
  }

  async function boot() {
    bind();
    const appText = await fetch("app.js").then((response) => response.text());
    state.catalog = parseCatalog(appText);
    state.hatFit = parseHatFit(appText);
    state.hats = Object.keys(state.hatFit).sort();
    if (!state.hats.length) state.hats = Array.from({ length: 25 }, (_, index) => `hat_${String(index + 1).padStart(2, "0")}`);
    try {
      state.overrides = await fetch("hat-placement-overrides.json", { cache: "no-store" }).then((response) => response.ok ? response.json() : {});
    } catch {
      state.overrides = {};
    }
    try {
      const saved = await fetch("character-animation-review.json", { cache: "no-store" }).then((response) => response.ok ? response.json() : {});
      state.votes = saved && typeof saved === "object" ? saved : {};
    } catch {
      state.votes = JSON.parse(localStorage.getItem("petpro_hat_animation_review") || "{}");
    }
    state.activeId = state.catalog[0]?.id || "";
    state.hatId = state.hats.includes("hat_16") ? "hat_16" : state.hats[0];
    renderActive();
    for (const item of state.catalog) {
      await measureFrames(item);
      if (item.id === state.activeId) renderActive();
    }
  }

  boot().catch((error) => setStatus(error.message || String(error)));
}());
