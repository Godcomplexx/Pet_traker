(function () {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const ACCESSORIES = [
    { id: "accessory_bunan_black", name: "Bunan Black", file: "bunan_black_64.png", scale: 0.5, anchorX: 0.5, anchorY: 0.46 },
    { id: "accessory_maru_black", name: "Maru Black", file: "maru_black_64.png", scale: 0.46, anchorX: 0.5, anchorY: 0.45 },
    { id: "accessory_tsuyome_black", name: "Tsuyome Black", file: "tsuyome_black_64.png", scale: 0.52, anchorX: 0.5, anchorY: 0.46 },
    { id: "accessory_yasashime_black", name: "Yasashime Black", file: "yasashime_black_64.png", scale: 0.5, anchorX: 0.5, anchorY: 0.46 },
  ];
  const state = {
    catalog: [],
    visible: [],
    accessory: ACCESSORIES[0],
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

  function setControlsFromAccessory(accessory) {
    state.accessory = accessory;
    state.scale = accessory.scale;
    state.anchorX = accessory.anchorX;
    state.anchorY = accessory.anchorY;
    state.offsetX = 0;
    state.offsetY = 0;
    $("#scale").value = state.scale;
    $("#anchorX").value = state.anchorX;
    $("#anchorY").value = state.anchorY;
    $("#offsetX").value = state.offsetX;
    $("#offsetY").value = state.offsetY;
  }

  function renderShell() {
    const select = $("#accessory");
    select.replaceChildren(...ACCESSORIES.map((item) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = item.name;
      return option;
    }));
    select.value = state.accessory.id;
    setControlsFromAccessory(state.accessory);
    renderGrid();
  }

  function renderGrid() {
    const query = $("#search").value.trim().toLowerCase();
    state.visible = state.catalog.filter((item) => {
      const label = `${item.id} ${item.name} ${item.file}`.toLowerCase();
      return !query || label.includes(query);
    });
    $("#count").textContent = `${state.visible.length} / ${state.catalog.length} characters`;
    $("#grid").replaceChildren(...state.visible.map((item) => {
      const card = document.createElement("article");
      card.className = "card";

      const canvas = document.createElement("canvas");
      canvas.width = 220;
      canvas.height = 190;
      canvas.dataset.character = item.id;

      const name = document.createElement("div");
      name.className = "name";
      name.textContent = item.name || item.file.replace(".png", "");

      const sub = document.createElement("div");
      sub.className = "sub";
      sub.textContent = `${item.frameWidth}x${item.frameHeight} · ${item.frames || 1} frames`;

      card.append(canvas, name, sub);
      return card;
    }));
  }

  function drawBackground(ctx, width, height) {
    ctx.fillStyle = "#f5f8f2";
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = "rgba(185,197,180,.55)";
    ctx.lineWidth = 1;
    for (let x = 0; x <= width; x += 22) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y <= height; y += 22) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  }

  async function drawCharacter(canvas, character, time) {
    const ctx = canvas.getContext("2d");
    ctx.imageSmoothingEnabled = false;
    drawBackground(ctx, canvas.width, canvas.height);

    const frameWidth = Number(character.frameWidth || 32);
    const frameHeight = Number(character.frameHeight || 32);
    const frames = Math.max(1, Number(character.frames || 1));
    const frameMs = 170 * Number(character.frameDuration || 1);
    const frame = Math.floor(time / frameMs) % frames;
    const spriteScale = Math.min(4.8, 92 / frameHeight);
    const spriteWidth = frameWidth * spriteScale;
    const spriteHeight = frameHeight * spriteScale;
    const spriteLeft = canvas.width / 2 - spriteWidth / 2;
    const spriteTop = canvas.height / 2 - spriteHeight / 2 + 12;
    const sprite = await loadImage(`assets/characters/${character.file}`);
    const accessory = await loadImage(`assets/accessories/${state.accessory.file}`);

    ctx.drawImage(
      sprite,
      frame * frameWidth,
      0,
      frameWidth,
      frameHeight,
      Math.round(spriteLeft),
      Math.round(spriteTop),
      Math.round(spriteWidth),
      Math.round(spriteHeight),
    );

    const accessorySize = Math.max(20, spriteWidth * Number(state.scale || 0.5));
    const left = spriteLeft + spriteWidth * Number(state.anchorX || 0.5) + Number(state.offsetX || 0);
    const top = spriteTop + spriteHeight * Number(state.anchorY || 0.46) + Number(state.offsetY || 0);
    ctx.drawImage(
      accessory,
      Math.round(left - accessorySize / 2),
      Math.round(top - accessorySize / 2),
      Math.round(accessorySize),
      Math.round(accessorySize),
    );
  }

  function draw(time) {
    const canvases = Array.from(document.querySelectorAll("[data-character]"));
    for (const canvas of canvases) {
      const character = state.catalog.find((item) => item.id === canvas.dataset.character);
      if (character) drawCharacter(canvas, character, time).catch(console.error);
    }
    requestAnimationFrame(draw);
  }

  function bindEvents() {
    $("#search").addEventListener("input", renderGrid);
    $("#accessory").addEventListener("change", (event) => {
      const accessory = ACCESSORIES.find((item) => item.id === event.target.value);
      if (accessory) setControlsFromAccessory(accessory);
    });
    for (const id of ["scale", "anchorX", "anchorY", "offsetX", "offsetY"]) {
      $(`#${id}`).addEventListener("input", (event) => {
        state[id] = Number(event.target.value || 0);
      });
    }
    $("#reset").addEventListener("click", () => setControlsFromAccessory(state.accessory));
  }

  async function boot() {
    bindEvents();
    const appText = await fetch("app.js", { cache: "no-store" }).then((response) => response.text());
    state.catalog = parseCatalog(appText);
    renderShell();
    requestAnimationFrame(draw);
  }

  boot().catch((error) => {
    $("#count").textContent = error.message || String(error);
  });
}());
