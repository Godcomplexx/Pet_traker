!function () {
  "use strict";

  const sequence = ["ArrowUp", "ArrowUp", "ArrowRight", "ArrowLeft", "ArrowDown"];
  const videoSrc = "assets/easter-eggs/los-santos-2013.mp4";
  let progress = 0;
  let panel = null;

  function closePanel() {
    if (!panel) return;
    const video = panel.querySelector("video");
    if (video) {
      video.pause();
      video.removeAttribute("src");
      video.load();
    }
    panel.remove();
    panel = null;
  }

  function openPanel() {
    if (panel) {
      const video = panel.querySelector("video");
      panel.classList.remove("is-entering");
      panel.classList.add("is-active");
      if (video) video.play().catch(() => {});
      return;
    }

    panel = document.createElement("aside");
    panel.className = "easter-video is-entering";
    panel.setAttribute("aria-label", "Secret video");
    panel.innerHTML = `
      <div class="easter-video-bar">
        <span>Los Santos 2013</span>
        <button type="button" class="easter-video-close" aria-label="Close video">x</button>
      </div>
      <video src="${videoSrc}" controls autoplay playsinline></video>
    `;

    panel.querySelector(".easter-video-close").addEventListener("click", closePanel);
    const video = panel.querySelector("video");
    video.volume = 0.7;
    video.muted = false;
    video.addEventListener("ended", closePanel, { once: true });

    document.body.appendChild(panel);
    requestAnimationFrame(() => panel.classList.add("is-active"));
    video.play().catch(() => {});
  }

  document.addEventListener("keydown", (event) => {
    if (event.defaultPrevented || event.repeat) return;

    const expected = sequence[progress];
    if (event.key === expected) {
      progress += 1;
      if (progress === sequence.length) {
        progress = 0;
        openPanel();
      }
      return;
    }

    progress = event.key === sequence[0] ? 1 : 0;
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closePanel();
  });
}();
