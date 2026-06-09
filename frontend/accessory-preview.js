(function () {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const ACCESSORIES = [
    { id: "accessory_bunan_black", name: "Bunan Black", file: "bunan_black_64.png", scale: 0.5, anchorX: 0.5, anchorY: 0.46 },
    { id: "accessory_maru_black", name: "Maru Black", file: "maru_black_64.png", scale: 0.46, anchorX: 0.5, anchorY: 0.45 },
    { id: "accessory_tsuyome_black", name: "Tsuyome Black", file: "tsuyome_black_64.png", scale: 0.52, anchorX: 0.5, anchorY: 0.46 },
    { id: "accessory_yasashime_black", name: "Yasashime Black", file: "yasashime_black_64.png", scale: 0.5, anchorX: 0.5, anchorY: 0.46 },
  ];
  const CONTROL_IDS = ["scale", "anchorX", "anchorY", "offsetX", "offsetY"];
  const state = {
    catalog: [],
    visible: [],
    selectedCharacterId: "",
    accessory: ACCESSORIES[0],
    overrides: {},
    images: new Map(),
    scale: ACCESSORIES[0].scale,
    anchorX: ACCESSORIES[0].anchorX,
    anchorY: ACCESSORIES[0].anchorY,
    offsetX: 0,
    offsetY: 0,
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
        else if (/^-?\d+(\.\d+)?$/.test(token) || /^-?\.\d+$/.test(token)) item[key] = Number(token);
        else item[key] = token;
      }
      return item;
    }).filter((item) => item.id && item.file);
  }

  function loadImage(src) {
    if (state.images.has(src)) return state.images.get(src);
    const promise = new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error(`Cannot load ${src}`));
      image.src = src;
    });
    state.images.set(src, promise);
    return promise;
  }

  function selectedCharacter() {
    return state.catalog.find((item) => item.id === state.selectedCharacterId) || state.catalog[0];
  }

  function defaultPlacement(accessory = state.accessory) {
    return {
      scale: Number(accessory.scale || 0.5),
      anchorX: Number(accessory.anchorX || 0.5),
      anchorY: Number(accessory.anchorY || 0.46),
      offsetX: 0,
      offsetY: 0,
    };
  }

  function placementFor(characterId, accessory = state.accessory) {
    return {
      ...defaultPlacement(accessory),
      ...(state.overrides?.[characterId]?.[accessory.id] || {}),
    };
  }

  function currentDraft() {
    return Object.fromEntries(CONTROL_IDS.map((id) => [id, Number(state[id] || 0)]));
  }

  function formatNumber(value) {
    const number = Number(value || 0);
    return Number.isInteger(number) ? String(number) : number.toFixed(2).replace(/0+$/, "").replace(/\.$/, "");
  }

  function setStatus(message) {
    $("#status").textContent = message;
  }

  function updateOutput() {
    $("#output").value = JSON.stringify(state.overrides, null, 2);
  }

  function syncControls() {
    for (const id of CONTROL_IDS) {
      const input = $(`#${id}`);
      const value = document.querySelector(`[data-value="${id}"]`);
      input.value = state[id];
      if (value) value.textContent = formatNumber(state[id]);
    }
    updateHeader();
    updateOutput();
  }

  function setDraft(next) {
    for (const id of CONTROL_IDS) state[id] = Number(next[id] ?? 0);
    syncControls();
  }

  function updateHeader() {
    const character = selectedCharacter();
    if (!character) return;
    $("#currentTitle").textContent = `${character.file.replace(".png", "")} + ${state.accessory.name}`;
    $("#currentMeta").textContent = `scale ${formatNumber(state.scale)} x ${formatNumber(state.offsetX)} y ${formatNumber(state.offsetY)}`;
    $("#accessoryName").textContent = state.accessory.name;
  }

  function renderCharacters() {
    const query = $("#search").value.trim().toLowerCase();
    const list = $("#characterList");
    state.visible = state.catalog.filter((item) => {
      const label = `${item.id} ${item.name} ${item.file}`.toLowerCase();
      return !query || label.includes(query);
    });
    list.replaceChildren(...state.visible.map((item) => {
      const button = document.createElement("button");
      button.className = "item";
      button.type = "button";
      button.dataset.id = item.id;
      button.dataset.on = item.id === state.selectedCharacterId ? "true" : "false";

      const thumb = document.createElement("span");
      thumb.className = "thumb";
      const canvas = document.createElement("canvas");
      canvas.width = 220;
      canvas.height = 180;
      canvas.dataset.thumb = item.id;
      thumb.appendChild(canvas);

      const name = document.createElement("span");
      name.className = "name";
      const saved = state.overrides?.[item.id]?.[state.accessory.id] ? " *" : "";
      name.textContent = item.file.replace(".png", "") + saved;

      button.append(thumb, name);
      return button;
    }));
    $("#characterCount").textContent = String(state.catalog.length);
  }

  function renderAccessories() {
    $("#accessoryList").replaceChildren(...ACCESSORIES.map((item) => {
      const button = document.createElement("button");
      button.className = "accessory";
      button.type = "button";
      button.title = item.name;
      button.dataset.id = item.id;
      button.dataset.on = item.id === state.accessory.id ? "true" : "false";

      const img = document.createElement("img");
      img.src = `assets/accessories/${item.file}`;
      img.alt = item.name;
      button.appendChild(img);
      return button;
    }));
  }

  function drawBackground(ctx, width, height) {
    ctx.fillStyle = "#f0f4ee";
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = "#b9c4b4";
    ctx.lineWidth = 1;
    for (let x = 0; x <= width; x += 26) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y <= height; y += 26) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  }

  function previewGeometry(canvas, character, draft) {
    const frameWidth = Number(character.frameWidth || 32);
    const frameHeight = Number(character.frameHeight || 32);
    const spriteScale = Math.min(canvas.height * 0.62 / frameHeight, canvas.width * 0.58 / frameWidth);
    const spriteWidth = frameWidth * spriteScale;
    const spriteHeight = frameHeight * spriteScale;
    const spriteLeft = canvas.width / 2 - spriteWidth / 2;
    const spriteTop = canvas.height / 2 - spriteHeight / 2 + canvas.height * 0.06;
    const accessorySize = Math.max(20, spriteWidth * Number(draft.scale || 0.5));
    const accessoryLeft = spriteLeft + spriteWidth * Number(draft.anchorX || 0.5) + Number(draft.offsetX || 0);
    const accessoryTop = spriteTop + spriteHeight * Number(draft.anchorY || 0.46) + Number(draft.offsetY || 0);
    return { frameWidth, frameHeight, spriteWidth, spriteHeight, spriteLeft, spriteTop, accessorySize, accessoryLeft, accessoryTop };
  }

  async function drawCharacter(canvas, character, draft, time) {
    const ctx = canvas.getContext("2d");
    ctx.imageSmoothingEnabled = false;
    drawBackground(ctx, canvas.width, canvas.height);

    const geo = previewGeometry(canvas, character, draft);
    const frames = Math.max(1, Number(character.frames || 1));
    const frameMs = 170 * Number(character.frameDuration || 1);
    const frame = Math.floor(time / frameMs) % frames;
    const [sprite, accessory] = await Promise.all([
      loadImage(`assets/characters/${character.file}`),
      loadImage(`assets/accessories/${state.accessory.file}`),
    ]);

    ctx.drawImage(
      sprite,
      frame * geo.frameWidth,
      0,
      geo.frameWidth,
      geo.frameHeight,
      Math.round(geo.spriteLeft),
      Math.round(geo.spriteTop),
      Math.round(geo.spriteWidth),
      Math.round(geo.spriteHeight),
    );
    ctx.drawImage(
      accessory,
      Math.round(geo.accessoryLeft - geo.accessorySize / 2),
      Math.round(geo.accessoryTop - geo.accessorySize / 2),
      Math.round(geo.accessorySize),
      Math.round(geo.accessorySize),
    );
  }

  function draw(time) {
    const character = selectedCharacter();
    if (character) drawCharacter($("#preview"), character, currentDraft(), time).catch(console.error);

    document.querySelectorAll("[data-thumb]").forEach((canvas) => {
      const item = state.catalog.find((characterItem) => characterItem.id === canvas.dataset.thumb);
      if (item) drawCharacter(canvas, item, placementFor(item.id), time).catch(console.error);
    });
    requestAnimationFrame(draw);
  }

  function selectCharacter(id) {
    state.selectedCharacterId = id;
    setDraft(placementFor(id));
    renderCharacters();
  }

  function selectAccessory(id) {
    const accessory = ACCESSORIES.find((item) => item.id === id);
    if (!accessory) return;
    state.accessory = accessory;
    setDraft(placementFor(state.selectedCharacterId, accessory));
    renderCharacters();
    renderAccessories();
  }

  function savePair() {
    const character = selectedCharacter();
    if (!character) return;
    state.overrides[character.id] = state.overrides[character.id] || {};
    state.overrides[character.id][state.accessory.id] = currentDraft();
    updateOutput();
    renderCharacters();
    setStatus(`Сохранено: ${character.file.replace(".png", "")} / ${state.accessory.name}`);
  }

  function clearPair() {
    const character = selectedCharacter();
    if (!character || !state.overrides[character.id]) return;
    delete state.overrides[character.id][state.accessory.id];
    if (!Object.keys(state.overrides[character.id]).length) delete state.overrides[character.id];
    setDraft(placementFor(character.id));
    renderCharacters();
    setStatus("Настройка пары сброшена");
  }

  async function saveFile() {
    try {
      const response = await fetch("/save-accessory-overrides", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(state.overrides),
      });
      if (!response.ok) throw new Error(await response.text());
      setStatus("JSON записан в frontend/accessory-placement-overrides.json");
    } catch {
      setStatus("Не удалось записать файл. Запустите через scripts/hat_tuner_server.py");
    }
  }

  async function copyJson() {
    updateOutput();
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
    $("#accessoryList").addEventListener("click", (event) => {
      const button = event.target.closest(".accessory");
      if (button) selectAccessory(button.dataset.id);
    });
    for (const id of CONTROL_IDS) {
      $(`#${id}`).addEventListener("input", (event) => {
        state[id] = Number(event.target.value || 0);
        syncControls();
      });
    }
    $("#savePair").addEventListener("click", savePair);
    $("#clearPair").addEventListener("click", clearPair);
    $("#saveFile").addEventListener("click", saveFile);
    $("#copyJson").addEventListener("click", copyJson);
  }

  async function boot() {
    bindEvents();
    const [appText, overrides] = await Promise.all([
      fetch("app.js", { cache: "no-store" }).then((response) => response.text()),
      fetch("accessory-placement-overrides.json", { cache: "no-store" })
        .then((response) => (response.ok ? response.json() : {}))
        .catch(() => ({})),
    ]);
    state.catalog = parseCatalog(appText);
    state.overrides = overrides;
    state.selectedCharacterId = state.catalog[0]?.id || "";
    setDraft(placementFor(state.selectedCharacterId));
    renderCharacters();
    renderAccessories();
    updateOutput();
    requestAnimationFrame(draw);
  }

  boot().catch((error) => {
    setStatus(error.message || String(error));
  });
}());
