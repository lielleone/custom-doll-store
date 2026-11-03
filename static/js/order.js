/* Order form: a 3-step wizard, the drawing "workshop" (preview with a
   scanning and stitching effect), embroidery option cards with a live
   preview and total, and a stitched submit button.
   Without JS the form is the normal one-page form. The server checks
   everything again; these checks only help the visitor. */
(function () {
  "use strict";

  var form = document.querySelector("form[data-wizard]");
  if (!form) {
    return;
  }

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var animate = !!window.gsap && !reduceMotion;
  if (window.gsap && window.DrawSVGPlugin) {
    gsap.registerPlugin(DrawSVGPlugin);
  }

  // Same rules and messages as the server (orders.py)
  var ALLOWED = [".jpg", ".jpeg", ".png", ".pdf"];
  var MAX_BYTES = 10 * 1024 * 1024;
  var MSG_FILE_REQUIRED = "יש להעלות את הציור או התמונה.";
  var MSG_FILE_TYPE = "סוג הקובץ אינו נתמך. הקבצים המותרים מופיעים מתחת לשדה ההעלאה.";
  var MSG_FILE_SIZE = "הקובץ גדול מדי. הגודל המרבי הוא 10 מגה-בייט.";
  var MSG_EMB_TEXT = "סימנת רקמה אישית, ולכן יש להזין את הטקסט לרקמה.";
  var MSG_MISSING = "יש למלא את השדה: ";
  var MSG_EMAIL = "כתובת הדואר האלקטרוני אינה תקינה.";
  var MSG_TERMS = "יש לאשר את התקנון ואת מדיניות הפרטיות.";

  // Hebrew messages (the same as the server's) instead of the browser's own text
  function labelText(field) {
    var label = form.querySelector('label[for="' + field.id + '"]');
    return label ? label.textContent.replace(/\s+/g, " ").trim() : "";
  }
  function setHebrewMessage(field) {
    if (field.type === "file" || field === embText) {
      return;                         // handled by their own code
    }
    field.setCustomValidity("");
    if (field.id === "accept_terms" && !field.checked) {
      field.setCustomValidity(MSG_TERMS);
    } else if (field.validity.valueMissing) {
      field.setCustomValidity(MSG_MISSING + labelText(field));
    } else if (field.validity.typeMismatch && field.type === "email") {
      field.setCustomValidity(MSG_EMAIL);
    }
  }
  form.addEventListener("input", function (event) {
    if (event.target.matches("input, textarea") && event.target.type !== "file" && event.target !== embText) {
      event.target.setCustomValidity("");
    }
  });
  form.addEventListener("change", function (event) {
    if (event.target.id === "accept_terms") {
      event.target.setCustomValidity("");
    }
  });

  /* ---------- drawing workshop ---------- */
  var workshop = form.querySelector("[data-workshop]");
  var fileInput = form.querySelector("#drawing");
  var drop = workshop.querySelector(".workshop-drop");
  var preview = workshop.querySelector(".workshop-preview");
  var previewImg = workshop.querySelector(".workshop-img");
  var previewPdf = workshop.querySelector(".workshop-pdf");
  var status = workshop.querySelector(".workshop-status");
  var objectUrl = null;

  function setStatus(text, isError) {
    status.textContent = text;
    status.classList.toggle("is-error", !!isError);
  }

  function clearFile(message) {
    workshop.classList.remove("has-file", "is-ready");
    preview.hidden = true;
    fileInput.setCustomValidity(message || "");
    setStatus(message || "", !!message);
  }

  function scan() {
    workshop.classList.remove("is-ready");
    var paper = workshop.querySelector(".workshop-paper");
    if (!animate) {
      workshop.classList.add("is-ready");
      return;
    }
    var grid = paper.querySelector(".workshop-grid");
    var laser = paper.querySelector(".workshop-laser");
    var stitch = paper.querySelector(".workshop-stitch rect");
    var ready = workshop.querySelector(".workshop-ready");
    gsap.killTweensOf([paper, grid, laser, stitch, ready]);
    var tl = gsap.timeline({
      onComplete: function () {
        workshop.classList.add("is-ready");
        gsap.set([grid, laser, ready], { clearProps: "opacity" });
      }
    });
    tl.fromTo(paper, { scale: 0.9, rotation: 4, opacity: 0 },
                     { scale: 1, rotation: -1.5, opacity: 1, duration: 0.45, ease: "back.out(1.6)" })
      .to(grid, { opacity: 1, duration: 0.25 }, 0.2)
      .fromTo(laser, { top: "0%", opacity: 1 }, { top: "100%", duration: 0.6, ease: "power1.inOut" }, 0.3)
      .to(laser, { top: "0%", duration: 0.45, ease: "power1.inOut" })
      .to(laser, { opacity: 0, duration: 0.1 })
      .to(grid, { opacity: 0, duration: 0.3 }, "<")
      .set(paper.querySelector(".workshop-stitch"), { opacity: 1 }, "<")
      .fromTo(stitch, { drawSVG: "0%" }, { drawSVG: "100%", duration: 0.5, ease: "power1.inOut" }, "<")
      .fromTo(ready, { opacity: 0, y: 8 }, { opacity: 1, y: 0, duration: 0.25, ease: "back.out(2)" });
  }

  function handleFile() {
    var file = fileInput.files && fileInput.files[0];
    if (objectUrl) {
      URL.revokeObjectURL(objectUrl);
      objectUrl = null;
    }
    if (!file) {
      clearFile("");
      return;
    }
    var name = file.name.toLowerCase();
    var ext = name.slice(name.lastIndexOf("."));
    if (ALLOWED.indexOf(ext) === -1) {
      clearFile(MSG_FILE_TYPE);
      return;
    }
    if (file.size > MAX_BYTES) {
      clearFile(MSG_FILE_SIZE);
      return;
    }
    fileInput.setCustomValidity("");
    workshop.classList.add("has-file");
    preview.hidden = false;
    if (ext === ".pdf") {
      previewImg.hidden = true;
      previewImg.removeAttribute("src");
      previewPdf.hidden = false;
    } else {
      objectUrl = URL.createObjectURL(file);     // stays in the browser, nothing is uploaded yet
      previewImg.src = objectUrl;
      previewImg.alt = "הציור שנבחר";
      previewImg.hidden = false;
      previewPdf.hidden = true;
    }
    setStatus("נבחר הקובץ: " + file.name + ". לחיצה על האזור מחליפה את הקובץ.", false);
    scan();
  }

  fileInput.addEventListener("change", handleFile);
  ["dragenter", "dragover"].forEach(function (type) {
    drop.addEventListener(type, function () {
      drop.classList.add("is-dragover");
    });
  });
  ["dragleave", "drop"].forEach(function (type) {
    drop.addEventListener(type, function () {
      drop.classList.remove("is-dragover");
    });
  });

  /* ---------- embroidery cards, preview and total ---------- */
  var radios = form.querySelectorAll('input[name="embroidery"]');
  var embBox = form.querySelector("[data-embroidery-box]");
  var embText = form.querySelector("#embroidery_text");
  var embPreview = form.querySelector("[data-embroidery-preview]");
  var totals = form.querySelectorAll("[data-total]");
  var price = parseInt(form.dataset.price, 10);
  var embPrice = parseInt(form.dataset.embroideryPrice, 10);

  function embroideryChosen() {
    var chosen = form.querySelector('input[name="embroidery"]:checked');
    return !!chosen && chosen.value === "yes";
  }

  function updateOptions(fromUser) {
    var yes = embroideryChosen();
    embBox.hidden = !yes;
    embText.required = yes;
    embText.setCustomValidity("");
    embPreview.textContent = embText.value.trim() || "שם הילד";
    var total = String(price + (yes ? embPrice : 0));
    totals.forEach(function (el) {
      if (el.textContent !== total) {
        el.textContent = total;
        if (fromUser && animate) {
          gsap.fromTo(el.parentNode, { scale: 1.15 }, { scale: 1, duration: 0.35, ease: "back.out(3)" });
        }
      }
    });
    if (fromUser && yes && animate) {
      gsap.from(embBox, { opacity: 0, y: -10, duration: 0.3 });
    }
  }

  radios.forEach(function (radio) {
    radio.addEventListener("change", function () {
      updateOptions(true);
    });
  });
  embText.addEventListener("input", function () {
    embText.setCustomValidity("");
    embPreview.textContent = embText.value.trim() || "שם הילד";
  });

  /* ---------- the wizard ---------- */
  var panels = Array.prototype.slice.call(form.querySelectorAll(".wizard-panel"));
  var stepper = document.querySelector(".wizard-steps");
  var stepButtons = stepper ? stepper.querySelectorAll("[data-goto]") : [];
  var current = 1;
  var reached = 1;

  form.classList.add("is-wizard");
  form.noValidate = true;            // we check each step ourselves
  if (stepper) {
    stepper.hidden = false;
  }

  function renderStepper() {
    stepButtons.forEach(function (btn) {
      var n = parseInt(btn.dataset.goto, 10);
      btn.disabled = n > reached;
      btn.classList.toggle("is-done", n < current);
      if (n === current) {
        btn.setAttribute("aria-current", "step");
      } else {
        btn.removeAttribute("aria-current");
      }
    });
  }

  function show(n, moveFocus) {
    var forward = n > current;
    panels.forEach(function (panel) {
      panel.hidden = parseInt(panel.dataset.panel, 10) !== n;
    });
    current = n;
    reached = Math.max(reached, n);
    renderStepper();
    var panel = panels[n - 1];
    if (animate && moveFocus) {
      // RTL: going forward, the new step comes in from the left
      gsap.fromTo(panel, { x: forward ? -36 : 36, opacity: 0 },
                         { x: 0, opacity: 1, duration: 0.4, ease: "power3.out", clearProps: "transform,opacity" });
    }
    if (moveFocus) {
      var top = (stepper || form).getBoundingClientRect().top;
      if (top < 0) {
        (stepper || form).scrollIntoView({ block: "start" });
      }
      panel.querySelector("fieldset").focus({ preventScroll: true });
    }
  }

  function checkPanel(n) {
    if (n === 1 && !(fileInput.files && fileInput.files.length)) {
      fileInput.setCustomValidity(MSG_FILE_REQUIRED);   // Hebrew instead of the browser's own text
    }
    if (n === 2 && embroideryChosen() && !embText.value.trim()) {
      embText.setCustomValidity(MSG_EMB_TEXT);
    }
    var fields = panels[n - 1].querySelectorAll("input, textarea, select");
    for (var i = 0; i < fields.length; i++) {
      var field = fields[i];
      if (field.type === "hidden" || field.disabled || field.closest("[hidden]")) {
        continue;
      }
      setHebrewMessage(field);
      if (!field.checkValidity()) {
        return field;
      }
    }
    return null;
  }

  function report(field) {
    if (field === fileInput) {
      setStatus(fileInput.validationMessage, true);
      if (animate) {
        gsap.fromTo(drop, { x: -8 }, { x: 0, duration: 0.4, ease: "elastic.out(1, 0.3)" });
      }
    }
    field.reportValidity();
    field.focus();
  }

  form.querySelectorAll("[data-next]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var bad = checkPanel(current);
      if (bad) {
        report(bad);
        return;
      }
      show(current + 1, true);
    });
  });
  form.querySelectorAll("[data-back]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      show(current - 1, true);
    });
  });
  stepButtons.forEach(function (btn) {
    btn.addEventListener("click", function () {
      var n = parseInt(btn.dataset.goto, 10);
      if (n <= reached && n !== current) {
        show(n, true);
      }
    });
  });

  /* ---------- stitched submit ---------- */
  var submitting = false;
  var submitBtn = form.querySelector(".magic-submit");

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (submitting) {
      return;
    }
    for (var n = 1; n <= panels.length; n++) {
      var bad = checkPanel(n);
      if (bad) {
        if (n !== current) {
          show(n, true);
        }
        report(bad);
        return;
      }
    }
    submitting = true;
    submitBtn.disabled = true;
    submitBtn.setAttribute("aria-busy", "true");
    if (!animate) {
      form.submit();
      return;
    }
    var rect = submitBtn.querySelector(".magic-stitch rect");
    gsap.timeline({ onComplete: function () { form.submit(); } })
      .set(submitBtn.querySelector(".magic-stitch"), { opacity: 1 })
      .fromTo(rect, { drawSVG: "0%" }, { drawSVG: "100%", duration: 0.6, ease: "power1.inOut" })
      .fromTo(submitBtn.querySelector(".magic-stamp"),
              { scale: 2.2, rotation: -25, opacity: 0 },
              { scale: 1, rotation: -12, opacity: 1, duration: 0.25, ease: "power4.in" }, "-=0.1")
      .to(submitBtn, { scale: 0.96, duration: 0.08, yoyo: true, repeat: 1 });
  });

  // If the page comes back from the browser cache (Back button), allow sending again
  window.addEventListener("pageshow", function () {
    submitting = false;
    submitBtn.disabled = false;
    submitBtn.removeAttribute("aria-busy");
  });

  /* ---------- start ---------- */
  updateOptions(false);
  show(1, false);
  if (form.hasAttribute("data-had-errors")) {
    // The browser drops the chosen file after a server error, so start at the drawing.
    setStatus(MSG_FILE_REQUIRED, false);
  }
})();
