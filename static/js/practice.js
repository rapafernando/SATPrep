/* Question page extras: answer timer, calculator, and a scratchpad that works with finger, mouse or pen. */
(function () {
  "use strict";

  // --- Timer: records how long the question took (sent with the answer) ---
  var startedAt = Date.now();
  var form = document.getElementById("question-form");
  var secondsField = document.getElementById("seconds");
  if (form && secondsField) {
    form.addEventListener("submit", function () {
      secondsField.value = String(Math.max(0, Math.round((Date.now() - startedAt) / 1000)));
    });
  }

  // Live clock next to the question (display only; the seconds sent come from the line above).
  var timerEl = document.getElementById("timer");
  if (timerEl) {
    setInterval(function () {
      var secs = Math.max(0, Math.round((Date.now() - startedAt) / 1000));
      timerEl.textContent = Math.floor(secs / 60) + ":" + String(secs % 60).padStart(2, "0");
    }, 1000);
  }

  // "Check answer" stays disabled until something is chosen or typed. Without JavaScript it is simply enabled,
  // and the server still refuses an empty answer.
  var checkBtn = document.getElementById("check-btn");
  if (form && checkBtn) {
    var hasAnswer = function () {
      var chosen = form.querySelector('input[name="answer"]:checked');
      var typed = form.querySelector('input[name="answer"][type="text"]');
      return Boolean(chosen) || Boolean(typed && typed.value.trim());
    };
    var sync = function () { checkBtn.disabled = !hasAnswer(); };
    form.addEventListener("input", sync);
    form.addEventListener("change", sync);
    sync();
  }

  function toggle(button, panel, onOpen) {
    if (!button || !panel) return;
    button.addEventListener("click", function () {
      var open = panel.hidden;
      panel.hidden = !open;
      button.setAttribute("aria-expanded", String(open));
      if (open && onOpen) onOpen();
    });
  }

  // --- Calculator ---
  var calcPanel = document.getElementById("calc-panel");
  var calcBuilt = false;
  function buildCalculator() {
    if (calcBuilt || !calcPanel || !window.CalcCore) return;
    calcBuilt = true;
    var wrap = document.createElement("div");
    wrap.className = "calc";
    var display = document.createElement("input");
    display.type = "text";
    display.inputMode = "none";
    display.setAttribute("aria-label", "Calculator display");
    display.autocomplete = "off";
    wrap.appendChild(display);
    var keys = document.createElement("div");
    keys.className = "calc-keys";
    var layout = [
      ["7"], ["8"], ["9"], ["÷", "op"],
      ["4"], ["5"], ["6"], ["×", "op"],
      ["1"], ["2"], ["3"], ["−", "op"],
      ["0"], ["."], ["(", "op"], [")", "op"],
      ["√(", "op"], ["^", "op"], ["π", "op"], ["+", "op"],
      ["C", "op"], ["⌫", "op"], ["Ans", "op"], ["=", "eq"],
    ];
    var last = "";
    layout.forEach(function (key) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = key[0];
      if (key[1]) b.className = key[1];
      b.addEventListener("click", function () {
        var k = key[0];
        if (k === "C") display.value = "";
        else if (k === "⌫") display.value = display.value.slice(0, -1);
        else if (k === "Ans") display.value += last;
        else if (k === "=") {
          try {
            last = String(window.CalcCore.evaluate(display.value));
            display.value = last;
          } catch (e) {
            display.value = "Error";
          }
        } else {
          if (display.value === "Error") display.value = "";
          display.value += k;
        }
      });
      keys.appendChild(b);
    });
    display.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        try {
          last = String(window.CalcCore.evaluate(display.value));
          display.value = last;
        } catch (e) {
          display.value = "Error";
        }
      }
    });
    wrap.appendChild(keys);
    calcPanel.appendChild(wrap);
  }
  toggle(document.getElementById("toggle-calc"), calcPanel, buildCalculator);

  // --- Scratchpad ---
  var padPanel = document.getElementById("pad-panel");
  var canvas = document.getElementById("pad");
  var strokes = []; // each stroke: array of {x, y, w}
  var current = null;
  var penSeen = false; // once a pen is used, ignore palm touches
  var ctx = null;

  function setup() {
    if (!canvas) return;
    var ratio = window.devicePixelRatio || 1;
    var rect = canvas.getBoundingClientRect();
    if (!rect.width) return;
    canvas.width = Math.round(rect.width * ratio);
    canvas.height = Math.round(rect.height * ratio);
    ctx = canvas.getContext("2d");
    ctx.scale(ratio, ratio);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    redraw();
  }
  function ink() {
    return getComputedStyle(document.body).color;
  }
  function redraw() {
    if (!ctx) return;
    var rect = canvas.getBoundingClientRect();
    ctx.clearRect(0, 0, rect.width, rect.height);
    ctx.strokeStyle = ink();
    strokes.forEach(drawStroke);
  }
  function drawStroke(stroke) {
    if (stroke.length === 1) {
      ctx.beginPath();
      ctx.arc(stroke[0].x, stroke[0].y, stroke[0].w / 2, 0, Math.PI * 2);
      ctx.fillStyle = ink();
      ctx.fill();
      return;
    }
    for (var i = 1; i < stroke.length; i++) {
      ctx.beginPath();
      ctx.lineWidth = stroke[i].w;
      ctx.moveTo(stroke[i - 1].x, stroke[i - 1].y);
      ctx.lineTo(stroke[i].x, stroke[i].y);
      ctx.stroke();
    }
  }
  function point(event) {
    var rect = canvas.getBoundingClientRect();
    var pressure = event.pressure > 0 && event.pointerType === "pen" ? event.pressure : 0.5;
    return { x: event.clientX - rect.left, y: event.clientY - rect.top, w: 1.5 + pressure * 2.5 };
  }

  if (canvas) {
    canvas.addEventListener("pointerdown", function (event) {
      if (event.pointerType === "pen") penSeen = true;
      if (event.pointerType === "touch" && penSeen) return; // palm rejection
      if (event.pointerType === "mouse" && event.button !== 0) return;
      canvas.setPointerCapture(event.pointerId);
      current = [point(event)];
      strokes.push(current);
      redraw();
      event.preventDefault();
    });
    canvas.addEventListener("pointermove", function (event) {
      if (!current) return;
      // Pens report many points; coalesced events keep fast handwriting smooth.
      var events = event.getCoalescedEvents ? event.getCoalescedEvents() : [event];
      if (!events.length) events = [event];
      events.forEach(function (e) { current.push(point(e)); });
      ctx.strokeStyle = ink();
      drawStroke(current.slice(-events.length - 1));
      event.preventDefault();
    });
    function end() { current = null; }
    canvas.addEventListener("pointerup", end);
    canvas.addEventListener("pointercancel", end);
    canvas.addEventListener("contextmenu", function (e) { e.preventDefault(); });
    var undo = document.getElementById("pad-undo");
    var clear = document.getElementById("pad-clear");
    if (undo) undo.addEventListener("click", function () { strokes.pop(); redraw(); });
    if (clear) clear.addEventListener("click", function () { strokes = []; redraw(); });
    window.addEventListener("resize", function () { if (!padPanel.hidden) setup(); });
  }
  toggle(document.getElementById("toggle-pad"), padPanel, setup);
})();
