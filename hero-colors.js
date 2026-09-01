/* hero-colors.js — color journey for the animated sun orb
   White → red → orange → yellow → green → blue → dark purple → light purple → amber (#F7AE00)
   Keyed to the same scroll math as the main hero animation (arc phase s = clamp(o/18, 0, 1)) */
(function () {
  'use strict';

  // 9 stops: white at Day 0, 7 satellite colors, amber at High Noon
  var stops = [
    [255, 255, 255], // white      — Day 0
    [232,  27,  27], // #E81B1B   — red
    [240, 112,  32], // #F07020   — orange
    [255, 224,  32], // #FFE020   — yellow
    [ 24, 184,  53], // #18B835   — green
    [ 30, 144, 240], // #1E90F0   — blue
    [ 91,  16, 144], // #5B1090   — dark purple
    [144,  64, 200], // #9040C8   — light purple
    [247, 174,   0], // #F7AE00   — amber (High Noon)
  ];

  function clamp(v, lo, hi) { return v < lo ? lo : v > hi ? hi : v; }

  function lerpColor(t) {
    var n   = stops.length - 1;
    var pos = clamp(t, 0, 1) * n;
    var i   = Math.min(Math.floor(pos), n - 1);
    var f   = pos - i;
    var a   = stops[i], b = stops[i + 1];
    return 'rgb(' +
      Math.round(a[0] + (b[0] - a[0]) * f) + ',' +
      Math.round(a[1] + (b[1] - a[1]) * f) + ',' +
      Math.round(a[2] + (b[2] - a[2]) * f) + ')';
  }

  function updateColor() {
    var hero = document.getElementById('hero');
    var sun  = document.getElementById('hn-sun');
    if (!hero || !sun) return;
    var o = -hero.getBoundingClientRect().top;
    var s = clamp(o / 18, 0, 1);   // matches main animation arc progress
    sun.setAttribute('fill', lerpColor(s));
  }

  // Throttle to one RAF per scroll tick
  var pending = false;
  window.addEventListener('scroll', function () {
    if (!pending) {
      pending = true;
      requestAnimationFrame(function () { pending = false; updateColor(); });
    }
  }, { passive: true });

  // Initialise on load (sets orb to white at scroll=0)
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateColor);
  } else {
    updateColor();
  }
}());
