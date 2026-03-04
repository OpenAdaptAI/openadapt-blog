/**
 * OpenAdapt Replay — protocol handler + fallback detection.
 *
 * Flow:
 *   1. User clicks "Replay with OpenAdapt".
 *   2. We try to open openadapt://play?id=...
 *   3. If the app is installed, the browser opens it (user sees OS confirmation).
 *   4. If not installed (detected via timeout), we show install panel.
 */

(function () {
  'use strict';

  var PROTOCOL = 'openadapt';
  var TIMEOUT_MS = 2500;
  var ORIGIN = window.location.hostname;

  /**
   * Build the openadapt:// deep link URL.
   */
  function buildDeepLink(recordingId) {
    return PROTOCOL + '://play?id=' + encodeURIComponent(recordingId) +
      '&src=' + encodeURIComponent(ORIGIN) + '&v=1';
  }

  /**
   * Try to open a custom protocol URL.
   * Uses hidden iframe + blur/timeout detection (industry standard pattern).
   * Returns a promise that resolves to true (app opened) or false (not installed).
   */
  function tryOpenProtocol(url) {
    return new Promise(function (resolve) {
      var resolved = false;
      var timeout;

      function done(result) {
        if (resolved) return;
        resolved = true;
        clearTimeout(timeout);
        window.removeEventListener('blur', onBlur);
        resolve(result);
      }

      function onBlur() {
        // Browser lost focus — the app likely opened
        done(true);
      }

      window.addEventListener('blur', onBlur);

      // Try opening via iframe (avoids navigation away from page)
      var iframe = document.createElement('iframe');
      iframe.style.display = 'none';
      iframe.src = url;
      document.body.appendChild(iframe);

      // Also try window.location as fallback for browsers that block iframe protocols
      setTimeout(function () {
        window.location.href = url;
      }, 100);

      // If no blur after timeout, app is probably not installed
      timeout = setTimeout(function () {
        document.body.removeChild(iframe);
        done(false);
      }, TIMEOUT_MS);

      // Clean up iframe after a longer delay regardless
      setTimeout(function () {
        if (iframe.parentNode) {
          document.body.removeChild(iframe);
        }
      }, TIMEOUT_MS + 1000);
    });
  }

  /**
   * Show the install panel for a recording.
   */
  function showInstallPanel(recordingId) {
    var panel = document.getElementById('oa-install-' + recordingId);
    if (panel) {
      panel.style.display = 'block';
    }
  }

  /**
   * Load steps from manifest.json into the step container.
   */
  function loadManifestSteps(recordingId, manifestURL) {
    var container = document.getElementById('oa-steps-' + recordingId);
    if (!container || container.children.length > 0) return; // Already has content

    fetch(manifestURL)
      .then(function (res) { return res.json(); })
      .then(function (manifest) {
        if (!manifest.actions_summary || manifest.actions_summary.length === 0) return;

        manifest.actions_summary.forEach(function (step, i) {
          var div = document.createElement('div');
          div.className = 'oa-step';
          div.setAttribute('data-step', i + 1);

          var header = document.createElement('div');
          header.className = 'oa-step-header';

          var num = document.createElement('span');
          num.className = 'oa-step-number';
          num.textContent = i + 1;

          var caption = document.createElement('span');
          caption.className = 'oa-step-caption';
          caption.textContent = step;

          header.appendChild(num);
          header.appendChild(caption);
          div.appendChild(header);
          container.appendChild(div);
        });
      })
      .catch(function () {
        // Manifest not available — steps stay empty (that's fine)
      });
  }

  /**
   * Main replay handler — called by the button onclick.
   */
  window.openadaptReplay = function (recordingId, manifestURL) {
    var url = buildDeepLink(recordingId);

    tryOpenProtocol(url).then(function (opened) {
      if (!opened) {
        showInstallPanel(recordingId);
      }
    });
  };

  // On page load, try to load manifest steps for any recording on the page
  document.addEventListener('DOMContentLoaded', function () {
    var recordings = document.querySelectorAll('.oa-recording');
    recordings.forEach(function (el) {
      var id = el.getAttribute('data-recording-id');
      var manifest = el.getAttribute('data-manifest-url');
      if (id && manifest) {
        loadManifestSteps(id, manifest);
      }
    });
  });
})();
