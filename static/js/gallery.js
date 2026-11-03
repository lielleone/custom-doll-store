/* Home page gallery: entrance on scroll, a soft 3D tilt with a light
   sheen that follows the pointer, and an enlarged view in a <dialog>.
   Without JS the photos are plain links to the full image. */
(function () {
  "use strict";

  var items = document.querySelectorAll("[data-gallery-item]");
  var dialog = document.querySelector(".gallery-dialog");
  if (!items.length || !dialog || typeof dialog.showModal !== "function") {
    return;
  }

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
  var hasGsap = !!window.gsap;
  var dialogImg = dialog.querySelector(".gallery-dialog-img");
  var lastTrigger = null;

  // Enlarged view
  function openItem(item) {
    var img = item.querySelector("img");
    dialogImg.src = item.getAttribute("href");
    dialogImg.alt = img.alt;
    lastTrigger = item;
    dialog.showModal();
    if (hasGsap && !reduceMotion) {
      gsap.fromTo(dialog.querySelector(".gallery-dialog-box"),
        { scale: 0.88, rotation: -2, opacity: 0 },
        { scale: 1, rotation: 0, opacity: 1, duration: 0.35, ease: "back.out(1.7)" });
    }
  }
  dialog.addEventListener("close", function () {
    dialogImg.src = "";
    if (lastTrigger) {
      lastTrigger.focus();
    }
  });
  dialog.querySelector("[data-gallery-close]").addEventListener("click", function () {
    dialog.close();
  });
  dialog.addEventListener("click", function (event) {
    if (event.target === dialog) {   // click on the backdrop
      dialog.close();
    }
  });

  items.forEach(function (item) {
    item.addEventListener("click", function (event) {
      event.preventDefault();
      openItem(item);
    });
  });

  if (!hasGsap || reduceMotion) {
    return;
  }

  // Entrance when the gallery scrolls into view
  if (window.ScrollTrigger) {
    gsap.registerPlugin(ScrollTrigger);
    gsap.from(".gallery-card", {
      y: 48,
      opacity: 0,
      duration: 0.8,
      ease: "power3.out",
      stagger: 0.15,
      scrollTrigger: { trigger: ".gallery-grid", start: "top 85%", once: true }
    });
  }

  // Tilt + sheen, only with a mouse or trackpad
  if (!finePointer) {
    return;
  }
  items.forEach(function (item) {
    gsap.set(item, { transformPerspective: 900 });
    var rotX = gsap.quickTo(item, "rotationX", { duration: 0.5, ease: "power3.out" });
    var rotY = gsap.quickTo(item, "rotationY", { duration: 0.5, ease: "power3.out" });
    var lift = gsap.quickTo(item, "z", { duration: 0.5, ease: "power3.out" });
    item.addEventListener("pointermove", function (event) {
      var box = item.getBoundingClientRect();
      var x = (event.clientX - box.left) / box.width;    // 0..1
      var y = (event.clientY - box.top) / box.height;
      rotY((x - 0.5) * 12);
      rotX((0.5 - y) * 10);
      lift(30);
      item.style.setProperty("--sheen-x", (x * 100).toFixed(1) + "%");
      item.style.setProperty("--sheen-y", (y * 100).toFixed(1) + "%");
    });
    item.addEventListener("pointerleave", function () {
      rotX(0);
      rotY(0);
      lift(0);
    });
  });
})();
