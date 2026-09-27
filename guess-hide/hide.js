/* Maps redraws its chrome after load, and the place name is not a stable id.
   Only rounds opened with #geoguess are stripped. A normal Maps tab is left alone. */
(function () {
  if (location.hash.indexOf("geoguess") !== -1) sessionStorage.setItem("geoguess", "1")
  if (sessionStorage.getItem("geoguess") !== "1") return

  var style = document.createElement("style")
  style.textContent = [
    "#gb,",
    "button[aria-label='Search'],",
    "button[aria-label='Directions'],",
    "button[aria-label='Menu'],",
    "button[aria-label='Collapse side panel'],",
    "button[aria-label='Show location on map'],",
    "button[aria-label='Share'],",
    "a[aria-label='Google apps'],",
    "a[aria-label='Sign in'],",
    "[aria-label='Interactive map'],",
    "[aria-label='Explore this area'],",
    "h1, h2, form, label,",
    "[role='main'],",
    "[role='complementary'],",
    "nav { display: none !important; }"
  ].join("\n")
  document.documentElement.appendChild(style)

  var title = "Geo Guess"
  var hiddenLabels = {
    "Search": true,
    "Directions": true,
    "Menu": true,
    "Collapse side panel": true,
    "Show location on map": true,
    "Share": true,
    "Google apps": true,
    "Sign in": true,
    "Interactive map": true,
    "Explore this area": true,
    "Saved": true,
    "Recents": true,
    "Get app": true,
    "See photos": true,
    "Browse Street View images": true
  }

  var keepLabels = {
    "Close": true,
    "Back": true,
    "Zoom in": true,
    "Zoom out": true,
    "Rotate clockwise": true,
    "Rotate counterclockwise": true,
    "Rotate the view clockwise": true,
    "Rotate the view counterclockwise": true,
    "Show imagery": true,
    "Hide imagery": true,
    "Compass": true,
    "Move forward": true,
    "Move backward": true,
    "Move left": true,
    "Move right": true,
    "Go forward": true,
    "Go back": true,
    "Look up": true,
    "Look down": true,
    "Street View & 360": true,
    "Browse Street View images": true
  }

  document.addEventListener("pointerdown", function (event) {
    var node = event.target
    if (!node || !node.closest) return
    var button = node.closest("button, [role='button']")
    if (!button || button.getAttribute("aria-label") !== "Close") return
    event.preventDefault()
    event.stopPropagation()
    chrome.runtime.sendMessage({ type: "quit" })
  }, true)

  function hide(el) {
    if (!el || el.dataset.atlasHidden === "1") return
    if (el.id === "atlas-guess" || el.id === "atlas-guess-sheet" || el.id === "atlas-guess-dim" || (el.closest && (el.closest("#atlas-guess") || el.closest("#atlas-guess-sheet") || el.closest("#atlas-guess-dim")))) return
    el.dataset.atlasHidden = "1"
    el.style.setProperty("display", "none", "important")
  }

  function smallCard(el) {
    var rect = el.getBoundingClientRect()
    return rect.width > 40 && rect.width < window.innerWidth * 0.6
      && rect.height > 16 && rect.height < window.innerHeight * 0.55
  }

  function hideCard(start) {
    var node = start
    var chosen = start
    for (var i = 0; i < 6 && node && node !== document.body; i++) {
      if (smallCard(node)) chosen = node
      node = node.parentElement
    }
    hide(chosen)
  }

  function scrub() {
    if (document.title !== title) document.title = title
    var labeled = document.querySelectorAll("[aria-label]")
    for (var i = 0; i < labeled.length; i++) {
      var label = labeled[i].getAttribute("aria-label")
      if (hiddenLabels[label]) hideCard(labeled[i])
    }
    var headings = document.querySelectorAll("h1")
    for (var h = 0; h < headings.length; h++) hideCard(headings[h])
    var forms = document.querySelectorAll("form")
    for (var f = 0; f < forms.length; f++) hideCard(forms[f])

    var clickables = document.querySelectorAll("button, [role='button'], a[aria-label]")
    for (var c = 0; c < clickables.length; c++) {
      var placeLabel = clickables[c].getAttribute("aria-label") || ""
      if (!placeLabel || hiddenLabels[placeLabel] || keepLabels[placeLabel]) continue
      if (clickables[c].getAttribute("role") === "tab") continue
      if (clickables[c].closest && clickables[c].closest("#atlas-guess, #atlas-guess-sheet")) continue
      hide(clickables[c])
    }

    var tips = document.querySelectorAll("[role='dialog'], [role='tooltip']")
    for (var t = 0; t < tips.length; t++) {
      if (tips[t].closest && tips[t].closest("#atlas-guess, #atlas-guess-sheet")) continue
      hideCard(tips[t])
    }

    var panels = document.querySelectorAll("[role='main'], [role='complementary'], nav, h2")
    for (var p = 0; p < panels.length; p++) {
      if (panels[p].closest && panels[p].closest("#atlas-guess, #atlas-guess-sheet")) continue
      hide(panels[p])
    }

    var regions = document.querySelectorAll("[role='region']")
    for (var g = 0; g < regions.length; g++) {
      var regionLabel = regions[g].getAttribute("aria-label") || ""
      if (/information for|photos of|review/i.test(regionLabel)) hide(regions[g])
    }

    var footer = document.querySelectorAll("[role='contentinfo'] button, [role='contentinfo'] a")
    for (var u = 0; u < footer.length; u++) {
      var footerText = (footer[u].innerText || "").replace(/\s+/g, " ").trim()
      if (footerText === "Terms" || footerText === "Privacy" || footerText === "Report a problem") continue
      hide(footer[u])
    }

    var cards = document.querySelectorAll("button, a, div")
    for (var k = 0; k < cards.length; k++) {
      if (cards[k].closest && cards[k].closest("#atlas-guess, #atlas-guess-sheet, #atlas-guess-dim")) continue
      var box = cards[k].getBoundingClientRect()
      if (box.width < 90 || box.width > 420 || box.height < 50 || box.height > 220) continue
      if (box.top < window.innerHeight * 0.45) continue
      if (!cards[k].querySelector("img, canvas")) continue
      var cardText = (cards[k].innerText || "").replace(/\s+/g, " ").trim()
      if (cardText.length < 2 || cardText.length > 80) continue
      hide(cards[k])
    }

    var bits = document.querySelectorAll("div, span, button, a")
    for (var b = 0; b < bits.length; b++) {
      if (bits[b].closest && bits[b].closest("#atlas-guess, #atlas-guess-sheet")) continue
      if (bits[b].childElementCount > 6) continue
      var text = bits[b].textContent || ""
      if (text.length < 4 || text.length > 160) continue
      if (text.indexOf("reviews") === -1 && text.indexOf("★") === -1) continue
      hideCard(bits[b])
    }
  }

  scrub()
  new MutationObserver(scrub).observe(document.documentElement, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ["aria-label", "class"]
  })
  setInterval(scrub, 500)

  /* Guess map. Official panoramas keep their coordinates in the page URL;
     they stay unread until the player places a pin. */
  var mapZoom = 1
  var countries = []
  var mapSheets = {}
  function mapSheet(name) {
    var img = mapSheets[name]
    if (img) return img
    img = new Image()
    mapSheets[name] = img
    img.onload = function () { drawMap() }
    img.src = chrome.runtime.getURL("map/" + name)
    return img
  }
  var towns = []
  var stateLines = []
  var mapLat = 20
  var mapLon = 0
  var pin = null
  var revealed = false
  var dragging = false
  var drawQueued = false
  var dragX = 0
  var dragY = 0
  var dragLat = 0
  var dragLon = 0

  var guessMode = /#geoguess(?:$|[^a-z])/i.test(location.href)
  var seenPano = false

  function isPano() {
    var href = location.href
    return /,3a,/.test(href) || /!1e1/.test(href) || /streetviewpixels/.test(href)
  }

  function onMaps() {
    return /google\.com\/maps|maps\.google\.com/.test(location.href)
  }

  function wrapLon(lon) {
    var x = ((lon + 180) % 360 + 360) % 360
    return x - 180
  }

  function lonToX(lon, z) {
    return (lon + 180) / 360 * Math.pow(2, z)
  }

  function latToY(lat, z) {
    var s = Math.sin(lat * Math.PI / 180)
    var n = Math.log((1 + s) / (1 - s))
    return (0.5 - n / (4 * Math.PI)) * Math.pow(2, z)
  }

  function xToLon(x, z) {
    return x / Math.pow(2, z) * 360 - 180
  }

  function yToLat(y, z) {
    var n = Math.PI - 2 * Math.PI * y / Math.pow(2, z)
    return 180 / Math.PI * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)))
  }

  function haversineKm(aLat, aLon, bLat, bLon) {
    var r = 6371
    var p1 = aLat * Math.PI / 180
    var p2 = bLat * Math.PI / 180
    var dp = (bLat - aLat) * Math.PI / 180
    var dl = (bLon - aLon) * Math.PI / 180
    var h = Math.sin(dp / 2) * Math.sin(dp / 2)
      + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) * Math.sin(dl / 2)
    return 2 * r * Math.asin(Math.min(1, Math.sqrt(h)))
  }

  var savedAnswer = null

  function answerFromUrl() {
    var match = location.href.match(/@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/)
    if (!match) match = location.href.match(/!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)/)
    if (match) savedAnswer = { lat: parseFloat(match[1]), lon: parseFloat(match[2]) }
    return savedAnswer
  }

  var root = document.createElement("div")
  root.id = "atlas-guess"
  root.style.cssText = [
    "position:fixed", "right:16px", "bottom:16px", "z-index:2147483646",
    "width:384px", "height:216px",
    "background:#16181d", "border-radius:12px",
    "box-shadow:0 8px 28px rgba(0,0,0,.45)",
    "font:15px/1.4 sans-serif", "overflow:hidden", "user-select:none"
  ].join(";")

  var viewport = document.createElement("div")
  viewport.style.cssText = "position:absolute;inset:0;z-index:1;overflow:hidden;background:#16181d;cursor:crosshair"

  var pinEl = document.createElement("div")
  pinEl.style.cssText = "position:absolute;width:14px;height:14px;margin:-7px 0 0 -7px;border-radius:50%;background:#e23b3b;border:2px solid #fff;display:none;pointer-events:none;z-index:2"

  var answerEl = document.createElement("div")
  answerEl.style.cssText = "position:absolute;width:14px;height:14px;margin:-7px 0 0 -7px;border-radius:50%;background:#2f9e44;border:2px solid #fff;display:none;pointer-events:none;z-index:2"

  var dim = document.createElement("div")
  dim.id = "atlas-guess-dim"
  dim.style.cssText = [
    "position:fixed", "inset:0", "z-index:2147483646",
    "background:rgba(0,0,0,.55)", "opacity:0", "pointer-events:none",
    "transition:opacity .35s ease"
  ].join(";")

  var sheet = document.createElement("div")
  sheet.id = "atlas-guess-sheet"
  sheet.style.cssText = [
    "position:fixed", "left:50%", "top:50%", "z-index:2147483647",
    "width:min(560px,92vw)", "transform:translate(-50%, 18%)",
    "opacity:0", "pointer-events:none",
    "transition:transform .4s ease, opacity .35s ease",
    "background:#161616", "color:#f2f2f2", "padding:16px",
    "border-radius:16px", "box-shadow:0 18px 50px rgba(0,0,0,.45)",
    "font:15px/1.4 sans-serif", "overflow:hidden"
  ].join(";")

  var mapCanvas = document.createElement("canvas")
  mapCanvas.style.cssText = "position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none"

  var confirmBtn = document.createElement("button")
  confirmBtn.type = "button"
  confirmBtn.textContent = "Guess"
  confirmBtn.style.cssText = [
    "position:absolute", "right:8px", "bottom:8px", "z-index:5",
    "display:none", "padding:6px 12px", "border:0", "border-radius:999px",
    "background:#f2f2f2", "color:#111", "font:600 12px sans-serif",
    "cursor:pointer", "pointer-events:auto", "box-shadow:0 2px 8px rgba(0,0,0,.35)"
  ].join(";")

  viewport.appendChild(mapCanvas)
  viewport.appendChild(pinEl)
  viewport.appendChild(answerEl)
  root.appendChild(viewport)
  root.appendChild(confirmBtn)

  function worldSize() {
    return 256 * Math.pow(2, mapZoom)
  }

  // Pick the copy of this longitude that sits nearest the camera, so a guess
  // in Florida and an answer in Tokyo meet across the Pacific instead of the
  // long way around the map.
  function nearestWorldX(lon) {
    var world = worldSize()
    var x = lonToX(lon, mapZoom) * 256
    var origin = lonToX(mapLon, mapZoom) * 256
    return x + Math.round((origin - x) / world) * world
  }

  function placeMarker(el, lat, lon) {
    var width = viewport.clientWidth
    var height = viewport.clientHeight
    var cx = lonToX(mapLon, mapZoom) * 256
    var cy = latToY(mapLat, mapZoom) * 256
    var px = nearestWorldX(lon) - (cx - width / 2)
    var py = latToY(lat, mapZoom) * 256 - (cy - height / 2)
    el.style.left = px + "px"
    el.style.top = py + "px"
    el.style.display = (px < -20 || py < -20 || px > width + 20 || py > height + 20) ? "none" : "block"
  }

  function pointInRing(lon, lat, ring) {
    var inside = false
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      var yi = ring[i][1]
      var yj = ring[j][1]
      if ((yi > lat) === (yj > lat)) continue
      var xi = ring[i][0]
      var xj = ring[j][0]
      var x = (xj - xi) * (lat - yi) / (yj - yi) + xi
      if (lon < x) inside = !inside
    }
    return inside
  }

  function ringCenter(ring) {
    var area = 0
    var cx = 0
    var cy = 0
    var minLon = 180
    var maxLon = -180
    var minLat = 90
    var maxLat = -90
    for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      var x1 = ring[j][0]
      var y1 = ring[j][1]
      var x2 = ring[i][0]
      var y2 = ring[i][1]
      var cross = x1 * y2 - x2 * y1
      area += cross
      cx += (x1 + x2) * cross
      cy += (y1 + y2) * cross
      if (x2 < minLon) minLon = x2
      if (x2 > maxLon) maxLon = x2
      if (y2 < minLat) minLat = y2
      if (y2 > maxLat) maxLat = y2
    }
    if (maxLon - minLon > 180 || Math.abs(area) < 1e-8) return null
    var lon = cx / (3 * area)
    var lat = cy / (3 * area)
    if (!pointInRing(lon, lat, ring)) {
      var best = null
      var bestDist = Infinity
      for (var gy = 1; gy <= 11; gy++) {
        for (var gx = 1; gx <= 11; gx++) {
          var glon = minLon + (maxLon - minLon) * gx / 12
          var glat = minLat + (maxLat - minLat) * gy / 12
          if (!pointInRing(glon, glat, ring)) continue
          var dist = (glon - lon) * (glon - lon) + (glat - lat) * (glat - lat)
          if (dist < bestDist) {
            bestDist = dist
            best = [glon, glat]
          }
        }
      }
      if (!best) return null
      lon = best[0]
      lat = best[1]
    }
    return { lon: lon, lat: lat, ring: ring }
  }

  function borderRings(geometry) {
    if (!geometry) return []
    var polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates
    var outlines = []
    for (var p = 0; p < polygons.length; p++) {
      var ring = polygons[p] && polygons[p][0]
      if (!ring || ring.length < 4) continue
      var minLon = 180
      var maxLon = -180
      var minLat = 90
      var maxLat = -90
      for (var i = 0; i < ring.length; i++) {
        var x = ring[i][0]
        var y = ring[i][1]
        if (x < minLon) minLon = x
        if (x > maxLon) maxLon = x
        if (y < minLat) minLat = y
        if (y > maxLat) maxLat = y
      }
      outlines.push({ ring: ring, box: [minLon, minLat, maxLon, maxLat] })
    }
    return outlines
  }

  function countryLabel(feature) {
    var geometry = feature.geometry
    var name = feature.properties && feature.properties.name
    if (!geometry || !name) return null
    var polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates
    var best = null
    var bestArea = 0
    for (var p = 0; p < polygons.length; p++) {
      var ring = polygons[p] && polygons[p][0]
      if (!ring || ring.length < 3) continue
      var center = ringCenter(ring)
      if (!center) continue
      var area = 0
      for (var i = 0, j = ring.length - 1; i < ring.length; j = i++) {
        area += ring[j][0] * ring[i][1] - ring[i][0] * ring[j][1]
      }
      area = Math.abs(area)
      if (area > bestArea) {
        bestArea = area
        best = { name: name, lon: center.lon, lat: center.lat, ring: ring }
      }
    }
    return best
  }

  function labelFits(label, spot, textW, textH, left, top) {
    var hw = textW / 2
    var hh = textH / 2
    var samples = [
      [0, 0], [-1, -1], [1, -1], [-1, 1], [1, 1],
      [0, -1], [0, 1], [-1, 0], [1, 0]
    ]
    for (var i = 0; i < samples.length; i++) {
      var px = spot[0] + samples[i][0] * hw
      var py = spot[1] + samples[i][1] * hh
      var lon = wrapLon(xToLon((left + px) / 256, mapZoom))
      var lat = yToLat((top + py) / 256, mapZoom)
      if (!pointInRing(lon, lat, label.ring)) return false
    }
    return true
  }

  function project(lon, lat, left, top) {
    return [nearestWorldX(lon) - left, latToY(lat, mapZoom) * 256 - top]
  }

  function drawMap() {
    var width = viewport.clientWidth || 320
    var height = viewport.clientHeight || 210
    var dpr = window.devicePixelRatio || 1
    var bw = Math.round(width * dpr)
    var bh = Math.round(height * dpr)
    if (mapCanvas.width !== bw || mapCanvas.height !== bh) {
      mapCanvas.width = bw
      mapCanvas.height = bh
    }
    var ctx = mapCanvas.getContext("2d")
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    ctx.fillStyle = "#16181d"
    ctx.fillRect(0, 0, width, height)
    var cx = lonToX(mapLon, mapZoom) * 256
    var cy = latToY(mapLat, mapZoom) * 256
    var left = cx - width / 2
    var top = cy - height / 2
    function levelNames(level) {
      if (level < 6) return ["z" + level + ".png"]
      var grid = level === 7 ? 4 : 2
      var names = []
      for (var qy = 0; qy < grid; qy++) {
        for (var qx = 0; qx < grid; qx++) names.push("z" + level + "-" + qx + "-" + qy + ".png")
      }
      return names
    }
    function levelReady(level) {
      var names = levelNames(level)
      for (var i = 0; i < names.length; i++) {
        var sheet = mapSheets[names[i]]
        if (!sheet || !sheet.complete || !sheet.naturalWidth) return false
      }
      return true
    }
    function blit(img, destX, destY, destW, destH) {
      if (!img.complete || !img.naturalWidth || destW <= 0 || destH <= 0) return
      var world = worldSize()
      var copy0 = Math.floor(-destX / world) - 1
      var copy1 = Math.ceil((width - destX) / world) + 1
      for (var copy = copy0; copy <= copy1; copy++) {
        var dx = destX + copy * world
        var x0 = Math.max(dx, 0)
        var y0 = Math.max(destY, 0)
        var x1 = Math.min(dx + destW, width)
        var y1 = Math.min(destY + destH, height)
        if (x1 <= x0 || y1 <= y0) continue
        var sx = (x0 - dx) / destW * img.naturalWidth
        var sy = (y0 - destY) / destH * img.naturalHeight
        var sw = (x1 - x0) / destW * img.naturalWidth
        var sh = (y1 - y0) / destH * img.naturalHeight
        ctx.drawImage(img, sx, sy, sw, sh, x0, y0, x1 - x0, y1 - y0)
      }
    }
    function drawLevel(level, alpha) {
      if (alpha <= 0) return
      var scale = Math.pow(2, mapZoom - level)
      ctx.save()
      ctx.globalAlpha = alpha
      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = "medium"
      if (level < 6) {
        var sheet = mapSheet("z" + level + ".png")
        blit(sheet, -left, -top, 256 * Math.pow(2, level) * scale, 256 * Math.pow(2, level) * scale)
      } else {
        var grid = level === 7 ? 4 : 2
        var part = 8192 * scale
        for (var qy = 0; qy < grid; qy++) {
          for (var qx = 0; qx < grid; qx++) {
            blit(mapSheet("z" + level + "-" + qx + "-" + qy + ".png"), qx * part - left, qy * part - top, part, part)
          }
        }
      }
      ctx.restore()
    }
    // Finer than the 512 px world sheet, so coastlines stay smooth, but only
    // the visible patch is painted. Zoom uses this same sheet as the still map.
    var dpr = window.devicePixelRatio || 1
    var live = Math.max(1, Math.min(7, Math.ceil(mapZoom + Math.log2(Math.max(1, dpr)) - 1e-6)))
    var want = Math.max(live, Math.min(7, Math.ceil(mapZoom + Math.log2(Math.max(1, dpr)) + 1 - 1e-6)))
    levelNames(want).forEach(mapSheet)
    var level = want
    while (level > 1 && !levelReady(level)) level--
    if (!levelReady(level)) levelNames(level).forEach(mapSheet)
    drawLevel(level, 1)
    var finer = Math.min(7, level + 1)
    if (finer > level && mapZoom > finer - 1) {
      levelNames(finer).forEach(mapSheet)
      if (levelReady(finer)) drawLevel(finer, Math.min(1, mapZoom - (finer - 1)))
    }
    // Baked borders shrink to a fraction of a pixel at world zoom. Stroke the
    // country outlines at a steady screen width until the bake is thick enough.
    // State and province lines are not in the bake, so they stay on at every zoom.
    var worldPx = 256 * Math.pow(2, mapZoom)
    function traceRings(outlines) {
      if (!outlines) return
      for (var r = 0; r < outlines.length; r++) {
        var box = outlines[r].box
        if (box[2] - box[0] <= 180) {
          var midLon = (box[0] + box[2]) / 2
          var shift = nearestWorldX(midLon) - lonToX(midLon, mapZoom) * 256
          var xA = lonToX(box[0], mapZoom) * 256 + shift - left
          var xB = lonToX(box[2], mapZoom) * 256 + shift - left
          var yA = latToY(box[3], mapZoom) * 256 - top
          var yB = latToY(box[1], mapZoom) * 256 - top
          if (xB < -8 || xA > width + 8 || yB < -8 || yA > height + 8) continue
        }
        var ring = outlines[r].ring
        var prevX = null
        for (var k = 0; k < ring.length; k++) {
          var sx = nearestWorldX(ring[k][0]) - left
          var sy = latToY(ring[k][1], mapZoom) * 256 - top
          if (k === 0 || (prevX !== null && Math.abs(sx - prevX) > worldPx * 0.5)) ctx.moveTo(sx, sy)
          else ctx.lineTo(sx, sy)
          prevX = sx
        }
      }
    }
    ctx.beginPath()
    ctx.lineWidth = 0.75
    ctx.lineJoin = "round"
    ctx.strokeStyle = "rgba(214, 218, 224, 0.95)"
    if (mapZoom < 6) {
      for (var c = 0; c < countries.length; c++) {
        var outlines = mapZoom < 3 && countries[c].borderCoarse && countries[c].borderCoarse.length
          ? countries[c].borderCoarse
          : countries[c].borderMid
        traceRings(outlines)
      }
    }
    traceRings(stateLines)
    ctx.stroke()
    var shortName = {
      "United States of America": "United States",
      "Democratic Republic of the Congo": "DR Congo",
      "United Republic of Tanzania": "Tanzania"
    }
    function nameChip(text, x, y, size) {
      ctx.font = "500 " + size + "px sans-serif"
      var textW = ctx.measureText(text).width
      var chipX = x + 7
      var chipY = y - 8
      if (chipX < 4 || chipY < 4 || chipX + textW + 8 > width || chipY + 16 > height) return false
      ctx.fillStyle = "#e8e8e8"
      ctx.fillRect(x - 1, y - 1, 2, 2)
      ctx.fillStyle = "rgba(22,24,29,0.88)"
      ctx.fillRect(chipX, chipY, textW + 6, 16)
      ctx.fillStyle = "#e8e8e8"
      ctx.textAlign = "left"
      ctx.textBaseline = "middle"
      ctx.fillText(text, chipX + 3, chipY + 8)
      return true
    }
    for (var n = 0; n < countries.length; n++) {
      var label = countries[n].label
      if (!label) continue
      if (mapZoom >= 4.5) continue
      var spot = project(label.lon, label.lat, left, top)
      var name = shortName[label.name] || label.name
      ctx.font = "500 12px sans-serif"
      if (!labelFits(label, spot, ctx.measureText(name).width, 12, left, top)) continue
      nameChip(name, spot[0], spot[1], 12)
    }
    if (mapZoom >= 4.5) {
      var placed = []
      for (var t = 0; t < towns.length; t++) {
        var town = towns[t]
        if (town.z > mapZoom + 1.3) continue
        var spotT = project(town.lon, town.lat, left, top)
        if (spotT[0] < 8 || spotT[1] < 8 || spotT[0] > width - 8 || spotT[1] > height - 8) continue
        var crowded = false
        for (var q = 0; q < placed.length; q++) {
          var dx = placed[q][0] - spotT[0]
          var dy = placed[q][1] - spotT[1]
          if (dx * dx + dy * dy < 34 * 34) { crowded = true; break }
        }
        if (crowded) continue
        if (!nameChip(town.n, spotT[0], spotT[1], 12)) continue
        placed.push(spotT)
      }
    }
    if (revealed && pin) {
      var answerLine = answerFromUrl()
      if (answerLine) {
        var from = project(pin.lon, pin.lat, left, top)
        var to = project(answerLine.lon, answerLine.lat, left, top)
        ctx.save()
        ctx.strokeStyle = "#f2f2f2"
        ctx.lineWidth = 2
        ctx.setLineDash([2, 7])
        ctx.beginPath()
        ctx.moveTo(from[0], from[1])
        ctx.lineTo(to[0], to[1])
        ctx.stroke()
        ctx.restore()
        placeMarker(answerEl, answerLine.lat, answerLine.lon)
      }
    }
    if (pin) placeMarker(pinEl, pin.lat, pin.lon)
  }

  function requestDraw() {
    if (drawQueued) return
    drawQueued = true
    requestAnimationFrame(function () {
      drawQueued = false
      drawMap()
    })
  }

  fetch(chrome.runtime.getURL("countries.json")).then(function (response) {
    return response.json()
  }).then(function (data) {
    countries = data.features || []
    for (var i = 0; i < countries.length; i++) {
      var geometry = countries[i].geometry
      countries[i].label = countryLabel(countries[i])
      countries[i].borderCoarse = borderRings(countries[i].coarse)
      countries[i].borderMid = borderRings(countries[i].mid || countries[i].geometry)
      countries[i].bounds = []
      if (!geometry) continue
      var polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates
      for (var p = 0; p < polygons.length; p++) {
        var outer = polygons[p][0] || []
        var minLon = 180
        var maxLon = -180
        var minLat = 90
        var maxLat = -90
        for (var b = 0; b < outer.length; b++) {
          var bx = outer[b][0]
          var by = outer[b][1]
          if (bx < minLon) minLon = bx
          if (bx > maxLon) maxLon = bx
          if (by < minLat) minLat = by
          if (by > maxLat) maxLat = by
        }
        countries[i].bounds.push([minLon, minLat, maxLon, maxLat])
      }
    }
    drawMap()
  }).catch(function () {})

  fetch(chrome.runtime.getURL("towns.json")).then(function (response) {
    return response.json()
  }).then(function (rows) {
    towns = rows || []
    drawMap()
  }).catch(function () {})

  fetch(chrome.runtime.getURL("states.json")).then(function (response) {
    return response.json()
  }).then(function (rows) {
    stateLines = []
    for (var i = 0; i < rows.length; i++) {
      var line = rows[i]
      if (!line || line.length < 2) continue
      var minLon = 180
      var maxLon = -180
      var minLat = 90
      var maxLat = -90
      for (var k = 0; k < line.length; k++) {
        var x = line[k][0]
        var y = line[k][1]
        if (x < minLon) minLon = x
        if (x > maxLon) maxLon = x
        if (y < minLat) minLat = y
        if (y > maxLat) maxLat = y
      }
      stateLines.push({ ring: line, box: [minLon, minLat, maxLon, maxLat] })
    }
    drawMap()
  }).catch(function () {})

  viewport.addEventListener("mousedown", function (event) {
    if (revealed) return
    dragging = true
    dragX = event.clientX
    dragY = event.clientY
    dragLat = mapLat
    dragLon = mapLon
    viewport.style.cursor = "grabbing"
  })
  window.addEventListener("mouseup", function () {
    if (!dragging) return
    dragging = false
    viewport.style.cursor = "grab"
    drawMap()
  })
  window.addEventListener("mousemove", function (event) {
    if (!dragging) return
    var dx = event.clientX - dragX
    var dy = event.clientY - dragY
    var scale = 360 / (256 * Math.pow(2, mapZoom))
    mapLon = wrapLon(dragLon - dx * scale)
    mapLat = Math.max(-75, Math.min(75, dragLat + dy * scale))
    requestDraw()
  })
  viewport.addEventListener("wheel", function (event) {
    event.preventDefault()
    var delta = event.deltaY
    if (event.deltaMode === 1) delta *= 16
    var step = Math.max(-0.22, Math.min(0.22, -delta / 700))
    if (Math.abs(step) < 0.01) return
    mapZoom = Math.max(1, Math.min(8, mapZoom + step))
    requestDraw()
  }, { passive: false })
  viewport.addEventListener("click", function (event) {
    if (revealed || dragging || event.target === confirmBtn) return
    var moved = Math.abs(event.clientX - dragX) + Math.abs(event.clientY - dragY)
    if (moved > 6) return
    var rect = viewport.getBoundingClientRect()
    var width = rect.width
    var height = rect.height
    var cx = lonToX(mapLon, mapZoom) * 256
    var cy = latToY(mapLat, mapZoom) * 256
    var wx = cx - width / 2 + (event.clientX - rect.left)
    var wy = cy - height / 2 + (event.clientY - rect.top)
    pin = { lat: yToLat(wy / 256, mapZoom), lon: wrapLon(xToLon(wx / 256, mapZoom)) }
    confirmBtn.style.display = "block"
    drawMap()
  })
  function countryNameAt(lon, lat) {
    for (var c = 0; c < countries.length; c++) {
      var geometry = countries[c].geometry
      var name = countries[c].properties && countries[c].properties.name
      if (!geometry || !name) continue
      var polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates
      for (var p = 0; p < polygons.length; p++) {
        var ring = polygons[p] && polygons[p][0]
        if (ring && pointInRing(lon, lat, ring)) return name
      }
    }
    return ""
  }

  function describePlace(lat, lon) {
    var country = countryNameAt(lon, lat)
    var nearest = null
    var best = Infinity
    for (var i = 0; i < towns.length; i++) {
      var town = towns[i]
      var km = haversineKm(lat, lon, town.lat, town.lon)
      if (km < best) {
        best = km
        nearest = town
      }
    }
    if (nearest && best <= 60) {
      var bits = []
      if (nearest.r && nearest.r !== nearest.n) bits.push(nearest.r)
      if (nearest.c) bits.push(nearest.c)
      else if (country) bits.push(country)
      return { title: nearest.n, detail: bits.join(" · ") }
    }
    var away = nearest ? (best >= 100 ? Math.round(best) + " km from " + nearest.n : best.toFixed(0) + " km from " + nearest.n) : ""
    return { title: country || "Unknown place", detail: away }
  }

  function confirmGuess() {
    if (!pin || revealed) return
    var answer = answerFromUrl()
    if (!answer) return
    revealed = true
    confirmBtn.style.display = "none"
    var km = haversineKm(pin.lat, pin.lon, answer.lat, answer.lon)
    var shown = km >= 100 ? Math.round(km).toLocaleString() + " km" : km.toFixed(1) + " km"
    var place = describePlace(answer.lat, answer.lon)
    sheet.textContent = ""
    var distance = document.createElement("div")
    distance.textContent = shown
    distance.style.cssText = "font-size:26px;font-weight:700;margin:0 4px 4px"
    var where = document.createElement("div")
    where.textContent = place.title
    where.style.cssText = "font-size:18px;font-weight:600;margin:0 4px 2px"
    var detail = document.createElement("div")
    detail.textContent = place.detail
    detail.style.cssText = "opacity:.75;margin:0 4px 12px"
    root.style.position = "relative"
    root.style.right = "auto"
    root.style.bottom = "auto"
    root.style.width = "100%"
    root.style.height = "280px"
    root.style.boxShadow = "none"
    var actions = document.createElement("div")
    actions.style.cssText = "display:flex;gap:8px;margin-top:12px"
    var nextBtn = document.createElement("button")
    nextBtn.type = "button"
    nextBtn.textContent = "New round"
    var quitBtn = document.createElement("button")
    quitBtn.type = "button"
    quitBtn.textContent = "Quit"
    var actionStyle = "flex:1;padding:10px 12px;border:0;border-radius:10px;background:#f2f2f2;color:#111;font:600 14px sans-serif;cursor:pointer"
    nextBtn.style.cssText = actionStyle
    quitBtn.style.cssText = actionStyle
    nextBtn.addEventListener("click", function () {
      nextBtn.disabled = true
      nextBtn.textContent = "Finding a place…"
      chrome.runtime.sendMessage({ type: "next" }, function (doc) {
        if (doc && doc.ok && doc.url) {
          location.href = String(doc.url).split("#")[0] + "#geoguess"
          return
        }
        nextBtn.disabled = false
        nextBtn.textContent = (doc && doc.error) ? String(doc.error) : "New round"
      })
    })
    quitBtn.addEventListener("click", function () {
      chrome.runtime.sendMessage({ type: "quit" })
    })
    actions.appendChild(nextBtn)
    actions.appendChild(quitBtn)
    sheet.appendChild(distance)
    sheet.appendChild(where)
    sheet.appendChild(detail)
    sheet.appendChild(root)
    sheet.appendChild(actions)
    dim.style.opacity = "1"
    dim.style.pointerEvents = "auto"
    sheet.style.opacity = "1"
    sheet.style.pointerEvents = "auto"
    sheet.style.transform = "translate(-50%, -50%)"
    requestAnimationFrame(function () {
      frameBoth(pin, answer)
      drawMap()
    })
  }
  function frameBoth(a, b) {
    var width = viewport.clientWidth || 520
    var height = viewport.clientHeight || 280
    var pad = 48
    var zoom = 0.4
    for (var z = 5; z >= 0.4; z -= 0.1) {
      var world = 256 * Math.pow(2, z)
      var x1 = lonToX(a.lon, z) * 256
      var y1 = latToY(Math.max(-75, Math.min(75, a.lat)), z) * 256
      var x2 = lonToX(b.lon, z) * 256
      var y2 = latToY(Math.max(-75, Math.min(75, b.lat)), z) * 256
      if (x2 - x1 > world / 2) x1 += world
      if (x1 - x2 > world / 2) x2 += world
      if (Math.abs(x2 - x1) <= width - pad * 2 && Math.abs(y2 - y1) <= height - pad * 2) {
        zoom = z
        break
      }
    }
    mapZoom = zoom
    var world = 256 * Math.pow(2, zoom)
    var x1 = lonToX(a.lon, zoom) * 256
    var y1 = latToY(Math.max(-75, Math.min(75, a.lat)), zoom) * 256
    var x2 = lonToX(b.lon, zoom) * 256
    var y2 = latToY(Math.max(-75, Math.min(75, b.lat)), zoom) * 256
    if (x2 - x1 > world / 2) x1 += world
    if (x1 - x2 > world / 2) x2 += world
    mapLon = wrapLon(xToLon(((x1 + x2) / 2) / 256, zoom))
    mapLat = Math.max(-75, Math.min(75, yToLat(((y1 + y2) / 2) / 256, zoom)))
  }
  confirmBtn.addEventListener("pointerdown", function (event) {
    event.stopPropagation()
  })
  confirmBtn.addEventListener("click", function (event) {
    event.preventDefault()
    event.stopPropagation()
    confirmGuess()
  })
  window.addEventListener("resize", drawMap)

  function mount() {
    if (!guessMode) {
      if (root.parentNode) root.remove()
      if (sheet.parentNode) sheet.remove()
      if (dim.parentNode) dim.remove()
      return
    }
    if (isPano()) {
      seenPano = true
      answerFromUrl()
    }
    if (!onMaps()) {
      seenPano = false
      revealed = false
      if (root.parentNode) root.remove()
      if (sheet.parentNode) sheet.remove()
      if (dim.parentNode) dim.remove()
      return
    }
    if (!seenPano) return
    if (!revealed && !root.parentNode) document.documentElement.appendChild(root)
    if (!dim.parentNode) document.documentElement.appendChild(dim)
    if (!sheet.parentNode) document.documentElement.appendChild(sheet)
    drawMap()
  }

  mount()
  setInterval(mount, 1000)
  setInterval(function () {
    if (!onMaps() || !seenPano) return
    try { chrome.runtime.sendMessage({ type: "ping" }) } catch (e) {}
  }, 8000)
})()
