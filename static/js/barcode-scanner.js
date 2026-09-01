/* Barcode scanning support for Kiryana Sale/Purchase entry.

   Two independent scan sources feed into the same onScan(code) callback:

   1. initScannerInput(inputEl, onScan) - for USB/Bluetooth handheld
      scanners. These act exactly like a keyboard: they "type" the
      barcode's digits into whatever field has focus, then send Enter.
      No special driver or pairing beyond what the OS already does for
      any keyboard - just keep this input focused (or click into it)
      before scanning.

   2. initCameraScanner(buttonEl, videoWrapEl, onScan) - for scanning
      with a phone/tablet's camera straight from the browser, using the
      native BarcodeDetector API (Chrome/Edge/Android). There's no
      universal fallback for browsers without it (notably Safari/iOS as
      of this writing) - rather than show a control that silently fails,
      the button just hides itself when unsupported. */

function initScannerInput(inputEl, onScan) {
  if (!inputEl) return;
  inputEl.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      const code = inputEl.value.trim();
      inputEl.value = '';
      if (code) onScan(code);
    }
  });
}

function initCameraScanner(buttonEl, videoWrapEl, onScan) {
  if (!buttonEl || !videoWrapEl) return;
  if (!('BarcodeDetector' in window)) {
    buttonEl.style.display = 'none';
    return;
  }

  let stream = null;
  let detecting = false;
  let video = null;

  function stop() {
    detecting = false;
    if (stream) stream.getTracks().forEach(function (t) { t.stop(); });
    stream = null;
    videoWrapEl.style.display = 'none';
    videoWrapEl.innerHTML = '';
    buttonEl.textContent = '📷 Scan with Camera';
  }

  async function scanLoop(detector) {
    if (!detecting) return;
    try {
      const codes = await detector.detect(video);
      if (codes.length) {
        const value = codes[0].rawValue;
        stop();
        onScan(value);
        return;
      }
    } catch (err) {
      // transient decode errors happen constantly while aiming the
      // camera - just keep trying rather than surfacing them
    }
    requestAnimationFrame(function () { scanLoop(detector); });
  }

  async function start() {
    const detector = new BarcodeDetector();
    video = document.createElement('video');
    video.setAttribute('playsinline', '');
    video.setAttribute('muted', '');
    video.style.width = '100%';
    video.style.display = 'block';
    video.style.borderRadius = 'var(--radius)';
    videoWrapEl.innerHTML = '';
    videoWrapEl.appendChild(video);
    videoWrapEl.style.display = '';
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    } catch (err) {
      videoWrapEl.innerHTML = '<p style="color:var(--red); font-size:12.5px; margin:0;">Could not access the camera - check permissions.</p>';
      return;
    }
    video.srcObject = stream;
    await video.play();
    detecting = true;
    buttonEl.textContent = '✕ Stop Camera';
    scanLoop(detector);
  }

  buttonEl.addEventListener('click', function () {
    if (detecting) stop(); else start();
  });
}

/* Selects (or creates, for a freshly quick-added item) an <option> on a
   searchable-select-wrapped <select>, and keeps the visible search box
   text in sync since that box - not the real <select> - is what's shown
   to the user (see searchable-select.js). */
function selectSearchableOption(selectEl, id, text, rate) {
  if (!selectEl) return;
  let opt = Array.from(selectEl.options).find(function (o) { return String(o.value) === String(id); });
  if (!opt) {
    opt = document.createElement('option');
    opt.value = id;
    opt.dataset.stock = 0; // a freshly created item (not a match on an existing <option>) always starts at 0 stock
    selectEl.appendChild(opt);
  }
  opt.textContent = text;
  if (rate !== undefined && rate !== null) opt.dataset.rate = rate;
  selectEl.value = id;
  const visibleInput = selectEl.parentElement && selectEl.parentElement.querySelector('.searchable-input');
  if (visibleInput) visibleInput.value = text;
  selectEl.dispatchEvent(new Event('change'));
}
