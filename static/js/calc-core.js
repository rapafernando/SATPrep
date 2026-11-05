/* A tiny, safe expression evaluator for the on-screen calculator. No eval(). */
(function (root) {
  "use strict";

  function tokenize(input) {
    var s = String(input)
      .replace(/×/g, "*")
      .replace(/÷/g, "/")
      .replace(/−/g, "-")
      .replace(/π/g, "pi")
      .replace(/√/g, "sqrt");
    var tokens = [];
    var i = 0;
    while (i < s.length) {
      var ch = s[i];
      if (/\s/.test(ch)) { i++; continue; }
      if (/[0-9.]/.test(ch)) {
        var j = i;
        while (j < s.length && /[0-9.]/.test(s[j])) j++;
        var text = s.slice(i, j);
        if ((text.match(/\./g) || []).length > 1) throw new Error("bad number");
        tokens.push({ t: "num", v: parseFloat(text) });
        i = j;
        continue;
      }
      if (/[a-z]/i.test(ch)) {
        var k = i;
        while (k < s.length && /[a-z]/i.test(s[k])) k++;
        tokens.push({ t: "id", v: s.slice(i, k).toLowerCase() });
        i = k;
        continue;
      }
      if ("+-*/^()".indexOf(ch) >= 0) { tokens.push({ t: ch }); i++; continue; }
      throw new Error("bad character");
    }
    return tokens;
  }

  function evaluate(input) {
    var tokens = tokenize(input);
    var pos = 0;
    function peek() { return tokens[pos]; }
    function take(type) {
      if (!tokens[pos] || tokens[pos].t !== type) throw new Error("expected " + type);
      return tokens[pos++];
    }

    function expr() {
      var value = term();
      while (peek() && (peek().t === "+" || peek().t === "-")) {
        var op = tokens[pos++].t;
        var rhs = term();
        value = op === "+" ? value + rhs : value - rhs;
      }
      return value;
    }
    function term() {
      var value = unary();
      while (peek() && (peek().t === "*" || peek().t === "/" || peek().t === "(" || peek().t === "num" || peek().t === "id")) {
        if (peek().t === "*" || peek().t === "/") {
          var op = tokens[pos++].t;
          var rhs = unary();
          if (op === "/" && rhs === 0) throw new Error("divide by zero");
          value = op === "*" ? value * rhs : value / rhs;
        } else {
          value = value * power(); // implicit multiplication: 2(3+4), 2pi
        }
      }
      return value;
    }
    function unary() {
      if (peek() && peek().t === "-") { pos++; return -unary(); }
      if (peek() && peek().t === "+") { pos++; return unary(); }
      return power();
    }
    function power() {
      var base = primary();
      if (peek() && peek().t === "^") { pos++; return Math.pow(base, unary()); }
      return base;
    }
    function primary() {
      var token = peek();
      if (!token) throw new Error("unexpected end");
      if (token.t === "num") { pos++; return token.v; }
      if (token.t === "(") { pos++; var inner = expr(); take(")"); return inner; }
      if (token.t === "id") {
        pos++;
        if (token.v === "pi") return Math.PI;
        if (token.v === "sqrt") {
          take("(");
          var arg = expr();
          take(")");
          if (arg < 0) throw new Error("negative root");
          return Math.sqrt(arg);
        }
        throw new Error("unknown name");
      }
      throw new Error("unexpected " + token.t);
    }

    var result = expr();
    if (pos !== tokens.length) throw new Error("unexpected input");
    if (!isFinite(result)) throw new Error("not a number");
    return Math.round(result * 1e10) / 1e10;
  }

  var api = { evaluate: evaluate };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.CalcCore = api;
})(typeof window !== "undefined" ? window : this);
