/* Story hero on the home page: a child's sketch turns into the felt doll
   while the visitor scrolls. GSAP + ScrollTrigger + DrawSVG + MorphSVG
   (static/vendor/gsap). Without GSAP, or with prefers-reduced-motion,
   nothing runs and the page keeps the normal hero. */
(function () {
  "use strict";

  var story = document.getElementById("story");
  if (!story) {
    return;
  }
  if (!window.gsap || !window.ScrollTrigger ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    // No animation: show the normal hero with the steps listed.
    document.documentElement.classList.remove("js");
    return;
  }

  gsap.registerPlugin(ScrollTrigger, DrawSVGPlugin, MorphSVGPlugin);

  function q(selector) {
    return story.querySelector(selector);
  }
  function qa(selector) {
    return story.querySelectorAll(selector);
  }

  // The stage sticks below the sticky header.
  var header = document.querySelector("header");
  function setHeaderHeight() {
    var h = header ? header.offsetHeight : 0;
    document.documentElement.style.setProperty("--header-h", h + "px");
  }
  setHeaderHeight();
  window.addEventListener("resize", setHeaderHeight);

  story.classList.add("is-animated");

  // Keep the stage clean: the floating bubbles and stickers of the page
  // background fade back while the story is on screen.
  var background = document.querySelector(".bg-layer");
  function dimBackground(dim) {
    if (background) {
      gsap.to(background, { opacity: dim ? 0.18 : 1, duration: 0.6, overwrite: true });
    }
  }

  // The felt texture filter is heavy on phones.
  if (window.matchMedia("(max-width: 767px)").matches) {
    q("#s-felt").removeAttribute("filter");
  }

  var svg = q(".story-svg");
  var steps = qa(".story-step");
  var dots = qa(".story-progress span");
  var STEP_AT = [0, 0.13, 0.45, 0.86];   // scroll progress where each text step starts
  var current = -1;

  function showStep(index) {
    if (index === current) {
      return;
    }
    current = index;
    steps.forEach(function (step, i) {
      gsap.to(step, { autoAlpha: i === index ? 1 : 0, duration: 0.35, overwrite: true });
    });
    dots.forEach(function (dot, i) {
      dot.classList.toggle("is-active", i === index);
    });
  }

  function stepFor(progress) {
    var index = 0;
    for (var i = 0; i < STEP_AT.length; i++) {
      if (progress >= STEP_AT[i]) {
        index = i;
      }
    }
    return index;
  }

  // Starting state of every layer
  gsap.set(steps, { autoAlpha: 0 });
  showStep(0);
  // The notebook rests on a desk, tilted away from the "camera", a little out of focus.
  var desk = q(".story-desk");
  var isPhone = window.matchMedia("(max-width: 767px)").matches;
  var START = {
    rotationX: 32,
    rotation: -7,
    scale: isPhone ? 0.84 : 0.8,
    y: isPhone ? 18 : 34,
    filter: isPhone ? "blur(0px)" : "blur(1.6px)"   // blur is heavy on phones
  };
  gsap.set(svg, Object.assign({ transformPerspective: 900, transformOrigin: "50% 80%" }, START));  // keep 80% in sync with ORIGIN_Y
  gsap.set(desk, { opacity: 1, scaleX: 1 });

  // How far the camera may zoom in: up to 112%, but the page must stay inside
  // the pinned area (and above the text on phones). Recomputed on resize.
  var ORIGIN_Y = 0.8;
  function zoomScale() {
    var pin = q(".story-pin").getBoundingClientRect();
    var art = q(".story-art").getBoundingClientRect();
    var text = q(".story-text").getBoundingClientRect();
    var h = art.height || 1;
    var above = art.top - pin.top - 8;
    var below = (isPhone ? text.top : pin.bottom) - art.bottom - 8;
    var fit = 1 + Math.min(above / (ORIGIN_Y * h), below / ((1 - ORIGIN_Y) * h));
    return Math.max(1, Math.min(1.12, fit));
  }
  gsap.set(qa(".scr"), { drawSVG: "0%" });
  gsap.set(qa(".st-reveal"), { drawSVG: "0%" });
  gsap.set("#f-tail", { x: 46, y: 16, rotation: 14, transformOrigin: "0% 50%" });
  gsap.set("#f-eyes", { y: -26 });
  gsap.set(".f-spot", { opacity: 0, scale: 1.4, transformOrigin: "50% 50%" });

  // Intro: the child draws the cat when the page opens.
  gsap.from(qa("#s-sketch .sk"), {
    drawSVG: "0%",
    duration: 1.6,
    ease: "power1.inOut",
    stagger: 0.06,
    onComplete: function () {
      gsap.set(qa("#s-sketch .sk"), { clearProps: "strokeDasharray,strokeDashoffset" });
    }
  });

  // The needle follows the outline while the outline stitches are sewn.
  var outline = q("#f-body");
  var outlineLength = outline.getTotalLength();
  var needle = q("#s-needle");
  var sewing = { t: 0 };
  function placeNeedle() {
    var at = sewing.t * outlineLength;
    var p = outline.getPointAtLength(at);
    var next = outline.getPointAtLength(Math.min(at + 2, outlineLength));
    var angle = Math.atan2(next.y - p.y, next.x - p.x) * 180 / Math.PI;
    needle.setAttribute("transform", "translate(" + p.x + " " + p.y + ") rotate(" + angle + ")");
  }
  placeNeedle();

  dimBackground(true);
  ScrollTrigger.create({
    trigger: story,
    start: "top bottom",
    end: "bottom 35%",
    onEnter: function () { dimBackground(true); },
    onEnterBack: function () { dimBackground(true); },
    onLeave: function () { dimBackground(false); },
    onLeaveBack: function () { dimBackground(false); }
  });

  // Scroll timeline: 10 units from the top of the story to its end.
  var tl = gsap.timeline({
    defaults: { ease: "none" },
    scrollTrigger: {
      trigger: story,
      start: function () {
        return "top " + (header ? header.offsetHeight : 0);
      },
      end: "bottom bottom",
      scrub: 0.6,
      invalidateOnRefresh: true,
      onUpdate: function (self) {
        showStep(stepFor(self.progress));
      }
    }
  });

  // 0-2.5  the child colours the drawing in
  // 0-3    the camera dives in: the page lifts off the desk, flattens, comes into focus
  //        and fills the frame while the child colours the drawing in
  tl.to(svg, { rotationX: 0, rotation: 0, y: 0, scale: zoomScale, filter: "blur(0px)",
               duration: 2.8, ease: "power2.inOut" }, 0)
    .to(desk, { opacity: 0, scaleX: 0.7, duration: 1.6, ease: "power1.in" }, 0)
    .to(qa(".scr"), { drawSVG: "100%", duration: 1.3, stagger: 0.12 }, 0.4)
    // a step back, to make room for the felt pieces that spread out
    .to(svg, { scale: 1, duration: 1.4, ease: "power1.inOut" }, 3.4);

  // 2.5-4  the drawing becomes a sewing pattern
  tl.to("#s-scribble", { opacity: 0, duration: 0.8 }, 2.6)
    .to(qa("#s-sketch .sk:not(#sk-outline)"), { opacity: 0, duration: 0.8 }, 2.6)
    .to("#sk-outline", { morphSVG: "#f-body", duration: 1.2, ease: "power1.inOut" }, 2.6)
    .to("#s-cut", { opacity: 1, duration: 0.8 }, 3.2)
    .to("#s-sketch", { opacity: 0, duration: 0.6 }, 3.6)
    .to("#cut-outline", { strokeDashoffset: -90, duration: 2.6 }, 3.2);

  // 4-5    felt pieces are cut out (still apart)
  tl.to(["#s-felt", "#s-eyes"], { opacity: 1, duration: 0.8 }, 4.0);

  // 5-7.4  pieces come together, spots go on, everything is sewn
  tl.to(["#f-tail", "#f-eyes"], { x: 0, y: 0, rotation: 0, duration: 1.4, ease: "power2.inOut" }, 5.0)
    .to(".f-spot", { opacity: 1, scale: 1, duration: 0.6, stagger: 0.1, ease: "back.out(1.6)" }, 5.0)
    .to("#s-cut", { opacity: 0, duration: 0.6 }, 5.2)
    .to(needle, { opacity: 1, duration: 0.2 }, 5.8)
    .to(sewing, { t: 1, duration: 1.6, onUpdate: placeNeedle }, 5.8)
    .to(qa(".st-reveal"), { drawSVG: "100%", duration: 1.6, stagger: 0.05 }, 5.8)
    .to(needle, { opacity: 0, duration: 0.2 }, 7.4);

  // 7.2-9  depth: light, shadow, a little tilt and puff
  tl.to("#s-paper", { opacity: 0, duration: 1 }, 7.2)
    .to("#s-shade", { opacity: 1, duration: 1 }, 7.2)
    .to("#s-floor", { opacity: 0.28, duration: 1 }, 7.4)
    .to("#s-shine", { opacity: 1, duration: 0.4 }, 7.8)
    .to(svg, { rotationY: -14, rotationX: 6, scale: 1.05, duration: 0.9, ease: "power1.inOut" }, 7.4)
    .to(svg, { rotationY: 0, rotationX: 0, scale: 1, duration: 0.8, ease: "power1.inOut" }, 8.3);

  // 9-10   the real doll
  tl.to(".story-final", { autoAlpha: 1, duration: 0.7 }, 9.0)
    .to(svg, { opacity: 0, duration: 0.7 }, 9.0)
    .to({}, { duration: 0.3 }, 9.7);
})();
