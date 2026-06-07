(function () {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));

  function sanitizeHtml(html) {
    const doc = new DOMParser().parseFromString(String(html ?? ""), "text/html");
    doc.querySelectorAll("script, iframe, object, embed, link, meta").forEach((node) => node.remove());
    doc.querySelectorAll("*").forEach((node) => {
      [...node.attributes].forEach((attr) => {
        const name = attr.name.toLowerCase();
        const value = attr.value.trim();
        if (name.startsWith("on")) {
          node.removeAttribute(attr.name);
        } else if ((name === "href" || name === "src") && /^javascript:/i.test(value)) {
          node.removeAttribute(attr.name);
        }
      });
    });
    return [...doc.body.childNodes];
  }

  function setSafeHtml(target, html) {
    if (!target) return;
    target.replaceChildren(...sanitizeHtml(html));
  }

  const controls = ["opaqueTop", "opaqueCenter", "hatScale", "hatOffsetX", "hatOffsetY"];
  const state = {
    catalog: [],
    hatFit: {},
    hats: [],
    overrides: {},
    characterId: "",
    hatId: "hat_16",
    draft: null,
    images: new Map(),
  };

  function parseCatalog(text) {
    const match = text.match(/const CHARACTER_CATALOG = \[([\s\S]*?)\];/)
      || text.match(/\w+=\[(\{id:"char_[\s\S]*?\})\],\w+=Object\.fromEntries\(\w+\.map/);
    if (!match) throw new Error("CHARACTER_CATALOG not found");
    return [...match[1].matchAll(/\{([^{}]+)\}/g)].map((entry) => {
      const item = {};
      for (const pair of entry[1].matchAll(/(\w+):\s*(?:"([^"]*)"|'([^']*)'|(!0|!1|true|false|-?(?:\d+(?:\.\d*)?|\.\d+)))/g)) {
        const key = pair[1];
        const token = pair[2] || pair[3] || pair[4];
        if (token === "true" || token === "!0") item[key] = true;
        else if (token === "false" || token === "!1") item[key] = false;
        else if (/^-?\d+(\.\d+)?$/.test(token)) item[key] = Number(token);
        else if (/^-?\.\d+$/.test(token)) item[key] = Number(token);
        else item[key] = token;
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

  function formatNumber(value) {
    const number = Number(value || 0);
    return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
  }

  function setStatus(message) {
    $("#status").textContent = message;
  }

  function getCharacter() {
    return state.catalog.find((item) => item.id === state.characterId);
  }

  function getComboOverride(characterId = state.characterId, hatId = state.hatId) {
    return state.overrides[characterId]?.[hatId] || null;
  }

  function getBaseDraft(character = getCharacter()) {
    const override = getComboOverride(character.id, state.hatId);
    return {
      opaqueTop: Number(override?.opaqueTop ?? character.opaqueTop ?? 0),
      opaqueCenter: Number(override?.opaqueCenter ?? character.opaqueCenter ?? character.frameWidth / 2),
      hatScale: Number(override?.hatScale ?? character.hatScale ?? 1),
      hatOffsetX: Number(override?.hatOffsetX ?? character.hatOffsetX ?? 0),
      hatOffsetY: Number(override?.hatOffsetY ?? character.hatOffsetY ?? 0),
      hatFlip: Boolean(override?.hatFlip ?? character.hatFlip ?? false),
    };
  }

  function slimDraft(draft) {
    return {
      opaqueTop: Number(draft.opaqueTop),
      opaqueCenter: Number(draft.opaqueCenter),
      hatScale: Number(draft.hatScale),
      hatOffsetX: Number(draft.hatOffsetX),
      hatOffsetY: Number(draft.hatOffsetY),
      hatFlip: Boolean(draft.hatFlip),
    };
  }

  function refreshOutput() {
    $("#output").value = JSON.stringify(state.overrides, null, 2);
  }

  function renderCharacters() {
    const query = $("#search").value.trim().toLowerCase();
    const list = $("#characterList");
    const filtered = state.catalog.filter((item) => {
      const label = `${item.id} ${item.name} ${item.file}`.toLowerCase();
      return !query || label.includes(query);
    });
    setSafeHtml(list, filtered.map((item) => `
      <button class="item" data-id="${item.id}" data-on="${item.id === state.characterId}">
        <span class="thumb"><img src="assets/characters/${item.file}" alt=""></span>
        <span class="name">${item.file.replace(".png", "")}</span>
      </button>
    `).join(""));
    $("#characterCount").textContent = String(state.catalog.length);
  }

  function renderHats() {
    setSafeHtml($("#hatList"), state.hats.map((id) => `
      <button class="hat" data-id="${id}" data-on="${id === state.hatId}" title="${id}">
        <img src="assets/hats/${id}.png" alt="">
      </button>
    `).join(""));
    $("#hatName").textContent = state.hatId;
  }

  function syncControls() {
    if (!state.draft) return;
    for (const id of controls) {
      const input = $(`#${id}`);
      input.value = state.draft[id];
      $(`[data-value="${id}"]`).textContent = formatNumber(state.draft[id]);
    }
    $("#hatFlip").checked = Boolean(state.draft.hatFlip);
  }

  function loadImage(src) {
    if (state.images.has(src)) return state.images.get(src);
    const promise = new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = src;
    });
    state.images.set(src, promise);
    return promise;
  }

  function drawPreviewGrid(ctx, canvas) {
    ctx.fillStyle = "#f0f4ee";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "#b9c4b4";
    ctx.lineWidth = 1;
    for (let x = 0; x <= canvas.width; x += 26) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, canvas.height);
      ctx.stroke();
    }
    for (let y = 0; y <= canvas.height; y += 26) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(canvas.width, y);
      ctx.stroke();
    }
  }

  function previewGeometry(canvas, character) {
    const frameWidth = Number(character.frameWidth || 32);
    const frameHeight = Number(character.frameHeight || 32);
    const spriteScale = 176 / frameHeight;
    const spriteWidth = frameWidth * spriteScale;
    const spriteHeight = frameHeight * spriteScale;
    const spriteCenterX = canvas.width / 2;
    const spriteTop = canvas.height / 2 - spriteHeight / 2 + 28;
    const spriteLeft = spriteCenterX - spriteWidth / 2;
    const fittedHatSize = 176 * Number(state.draft.hatScale || 1);
    const boxHeight = fittedHatSize * 0.72;
    const headTop = spriteTop + Number(state.draft.opaqueTop || 0) * spriteScale;
    const headX = spriteCenterX
      + (Number(state.draft.opaqueCenter || frameWidth / 2) - frameWidth / 2) * spriteScale
      + Number(state.draft.hatOffsetX || 0) * spriteScale;
    const headOverlap = Math.min(7, 2.5 * spriteScale);
    const top = headTop - boxHeight + headOverlap + Number(state.draft.hatOffsetY || 0) * spriteScale;
    const fit = state.hatFit[state.hatId] || { bottom: 10, center: 0 };
    const flip = state.draft.hatFlip ? -1 : 1;
    const imageShiftY = (Number(fit.bottom || 0) / 30) * fittedHatSize;
    const imageShiftX = (-Number(fit.center || 0) / 30) * fittedHatSize * flip;
    const left = headX - fittedHatSize / 2 + imageShiftX;
    const hatTop = top + boxHeight - fittedHatSize + imageShiftY;
    return {
      frameWidth, frameHeight, spriteWidth, spriteHeight, spriteLeft, spriteTop,
      fittedHatSize, headX, headTop, left, hatTop, flip,
    };
  }

  function drawHat(ctx, hat, geo) {
    ctx.save();
    if (geo.flip === -1) {
      ctx.translate(Math.round(geo.left + geo.fittedHatSize / 2), 0);
      ctx.scale(-1, 1);
      ctx.drawImage(
        hat,
        Math.round(-geo.fittedHatSize / 2),
        Math.round(geo.hatTop),
        Math.round(geo.fittedHatSize),
        Math.round(geo.fittedHatSize),
      );
    } else {
      ctx.drawImage(
        hat,
        Math.round(geo.left),
        Math.round(geo.hatTop),
        Math.round(geo.fittedHatSize),
        Math.round(geo.fittedHatSize),
      );
    }
    ctx.restore();
  }

  async function drawPreview() {
    const character = getCharacter();
    if (!character || !state.draft) return;

    const canvas = $("#preview");
    const ctx = canvas.getContext("2d");
    ctx.imageSmoothingEnabled = false;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawPreviewGrid(ctx, canvas);

    const geo = previewGeometry(canvas, character);
    const sprite = await loadImage(`assets/characters/${character.file}`);
    const hat = await loadImage(`assets/hats/${state.hatId}.png`);
    ctx.drawImage(
      sprite,
      0,
      0,
      geo.frameWidth,
      geo.frameHeight,
      Math.round(geo.spriteLeft),
      Math.round(geo.spriteTop),
      Math.round(geo.spriteWidth),
      Math.round(geo.spriteHeight),
    );
    drawHat(ctx, hat, geo);

    ctx.fillStyle = "rgba(47,125,70,.8)";
    ctx.fillRect(Math.round(geo.headX) - 2, Math.round(geo.headTop) - 2, 5, 5);

    $("#currentTitle").textContent = `${character.file.replace(".png", "")} + ${state.hatId}`;
    $("#currentMeta").textContent = `top ${formatNumber(state.draft.opaqueTop)} cx ${formatNumber(state.draft.opaqueCenter)} flip ${state.draft.hatFlip ? "Y" : "N"}`;
  }

  function selectCharacter(id) {
    state.characterId = id;
    state.draft = getBaseDraft();
    renderCharacters();
    syncControls();
    drawPreview();
  }

  function selectHat(id) {
    state.hatId = id;
    state.draft = getBaseDraft();
    renderHats();
    syncControls();
    drawPreview();
  }

  function saveCombo() {
    const character = getCharacter();
    if (!character) return;
    state.overrides[character.id] = state.overrides[character.id] || {};
    state.overrides[character.id][state.hatId] = slimDraft(state.draft);
    refreshOutput();
    setStatus(`Сохранено: ${character.file.replace(".png", "")} / ${state.hatId}`);
  }

  function clearCombo() {
    const character = getCharacter();
    if (!character || !state.overrides[character.id]) return;
    delete state.overrides[character.id][state.hatId];
    if (!Object.keys(state.overrides[character.id]).length) delete state.overrides[character.id];
    state.draft = getBaseDraft();
    syncControls();
    refreshOutput();
    drawPreview();
    setStatus("Настройка пары сброшена");
  }

  async function saveFile() {
    try {
      const response = await fetch("/save-hat-overrides", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(state.overrides),
      });
      if (!response.ok) throw new Error(await response.text());
      setStatus("JSON записан в frontend/hat-placement-overrides.json");
    } catch (error) {
      setStatus("Не удалось записать файл. Запустите через scripts/hat_tuner_server.py");
    }
  }

  async function copyJson() {
    refreshOutput();
    try {
      await navigator.clipboard.writeText($("#output").value);
      setStatus("JSON скопирован");
    } catch {
      $("#output").select();
      setStatus("JSON выделен, можно скопировать вручную");
    }
  }

  function bindEvents() {
    $("#search").addEventListener("input", renderCharacters);
    $("#characterList").addEventListener("click", (event) => {
      const button = event.target.closest(".item");
      if (button) selectCharacter(button.dataset.id);
    });
    $("#hatList").addEventListener("click", (event) => {
      const button = event.target.closest(".hat");
      if (button) selectHat(button.dataset.id);
    });
    for (const id of controls) {
      $(`#${id}`).addEventListener("input", (event) => {
        state.draft[id] = Number(event.target.value);
        syncControls();
        drawPreview();
      });
    }
    $("#hatFlip").addEventListener("change", (event) => {
      state.draft.hatFlip = event.target.checked;
      drawPreview();
    });
    $("#saveCombo").addEventListener("click", saveCombo);
    $("#clearCombo").addEventListener("click", clearCombo);
    $("#saveFile").addEventListener("click", saveFile);
    $("#copyJson").addEventListener("click", copyJson);
  }

  async function boot() {
    bindEvents();
    const appText = await fetch("app.js").then((response) => response.text());
    state.catalog = parseCatalog(appText);
    state.hatFit = parseHatFit(appText);
    state.hats = Object.keys(state.hatFit).sort();
    if (!state.hats.length) {
      state.hats = Array.from({ length: 25 }, (_, index) => `hat_${String(index + 1).padStart(2, "0")}`);
    }
    try {
      state.overrides = await fetch("hat-placement-overrides.json", { cache: "no-store" }).then((response) => {
        if (!response.ok) return {};
        return response.json();
      });
    } catch {
      state.overrides = {};
    }
    state.characterId = state.catalog[0]?.id || "";
    state.hatId = state.hats.includes("hat_16") ? "hat_16" : state.hats[0];
    state.draft = getBaseDraft();
    renderCharacters();
    renderHats();
    syncControls();
    refreshOutput();
    drawPreview();
  }

  boot().catch((error) => {
    setStatus(error.message || String(error));
  });
}());
