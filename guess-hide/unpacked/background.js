chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || message.type === "quit") {
    chrome.windows.getCurrent((win) => {
      if (win && win.id != null) chrome.windows.remove(win.id)
    })
    return
  }
  if (message.type !== "next") return
  nextRound().then(sendResponse).catch((error) => {
    sendResponse({ ok: false, error: String(error && error.message ? error.message : error) })
  })
  return true
})

var USA = [
  [40.68, -74.03, 40.82, -73.90],
  [34.00, -118.45, 34.12, -118.22],
  [41.78, -87.75, 41.95, -87.60],
  [25.74, -80.28, 25.86, -80.12],
  [47.55, -122.42, 47.70, -122.28],
  [37.75, -122.48, 37.81, -122.39],
  [29.73, -95.40, 29.79, -95.34],
  [42.33, -71.10, 42.38, -71.04]
]
var EU = [
  [51.47, -0.20, 51.55, -0.05],
  [48.83, 2.28, 48.90, 2.42],
  [52.47, 13.33, 52.55, 13.46],
  [41.87, 12.45, 41.93, 12.52],
  [40.38, -3.75, 40.46, -3.65],
  [52.34, 4.83, 52.40, 4.95],
  [59.31, 18.02, 59.36, 18.12],
  [38.70, -9.20, 38.76, -9.12],
  [50.05, 14.38, 50.12, 14.48],
  [48.18, 16.32, 48.24, 16.42],
  [52.20, 20.95, 52.28, 21.05],
  [37.96, 23.70, 38.02, 23.76],
  [41.00, 28.94, 41.06, 29.02]
]
var ASIA = [
  [35.65, 139.68, 35.73, 139.80],
  [37.52, 126.92, 37.58, 127.05],
  [1.27, 103.80, 1.36, 103.90],
  [13.72, 100.48, 13.78, 100.56],
  [31.20, 121.45, 31.25, 121.52],
  [22.27, 114.15, 22.32, 114.20],
  [19.05, 72.82, 19.12, 72.88],
  [28.60, 77.18, 28.68, 77.25]
]
var OTHER = [
  [43.63, -79.45, 43.72, -79.32],
  [19.35, -99.20, 19.48, -99.10],
  [-33.90, 151.15, -33.84, 151.23],
  [-37.85, 144.94, -37.78, 145.00],
  [-33.95, 18.40, -33.90, 18.50],
  [-22.95, -43.25, -22.88, -43.16],
  [-34.64, -58.45, -34.57, -58.37]
]
var BOXES = {
  everywhere: USA.concat(EU, ASIA, OTHER),
  usa: USA,
  eu: EU,
  asia: ASIA
}

function nativeNext() {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendNativeMessage("com.lessunderrated.geoguess", { type: "next" }, (doc) => {
        if (chrome.runtime.lastError) {
          resolve(null)
          return
        }
        var url = mapsUrlOnly(doc && doc.url)
        resolve(doc && doc.ok && url ? { ok: true, url: url } : null)
      })
    } catch (error) {
      resolve(null)
    }
  })
}

function pick(list) {
  return list[Math.floor(Math.random() * list.length)]
}

function tileXY(lat, lon) {
  var size = Math.pow(2, 17)
  var x = Math.floor((lon + 180) / 360 * size)
  var latR = Math.max(-85, Math.min(85, lat)) * Math.PI / 180
  var y = Math.floor((1 - Math.log(Math.tan(latR) + 1 / Math.cos(latR)) / Math.PI) / 2 * size)
  return [Math.max(0, x), Math.max(0, y)]
}

function safePanoid(pano) {
  return typeof pano === "string" && /^[A-Za-z0-9_-]{4,200}$/.test(pano)
}

function mapsUrlOnly(url) {
  var s = String(url || "").split("#")[0]
  if (s.length < 24 || s.length > 4096) return ""
  if (!/^https:\/\/(www\.google\.com\/maps|maps\.google\.com)\//.test(s)) return ""
  if (!/^[A-Za-z0-9._~:/?#@!+=&%,-]+$/.test(s)) return ""
  return s
}

function permalink(pano, lat, lon) {
  if (!safePanoid(pano)) return ""
  var kind = (pano.indexOf("CIHM0og") === 0 || pano.length > 22) ? 10 : 2
  return "https://www.google.com/maps/@" + lat + "," + lon + ",3a,75y,0h,90t/data=!3m4!1e1!3m2!1s" + pano + "!2e" + kind
}

var MAX_HTTP_BYTES = 2 * 1024 * 1024

async function readBoundedText(response, limit) {
  limit = limit || MAX_HTTP_BYTES
  var declared = Number(response.headers.get("content-length"))
  if (Number.isFinite(declared) && declared > limit) {
    throw new Error("response too large")
  }
  if (!response.body || typeof response.body.getReader !== "function") {
    var buffer = await response.arrayBuffer()
    if (buffer.byteLength > limit) throw new Error("response too large")
    return new TextDecoder("utf-8").decode(buffer)
  }
  var reader = response.body.getReader()
  var chunks = []
  var total = 0
  for (;;) {
    var step = await reader.read()
    if (step.done) break
    total += step.value.byteLength
    if (total > limit) {
      try { await reader.cancel() } catch (error) {}
      throw new Error("response too large")
    }
    chunks.push(step.value)
  }
  var bytes = new Uint8Array(total)
  var offset = 0
  for (var i = 0; i < chunks.length; i++) {
    bytes.set(chunks[i], offset)
    offset += chunks[i].byteLength
  }
  return new TextDecoder("utf-8").decode(bytes)
}

async function officialPanos(tileX, tileY) {
  var url = "https://www.google.com/maps/photometa/ac/v1?pb=!1m1!1smaps_sv.tactile!6m3!1i"
    + tileX + "!2i" + tileY + "!3i17!8b1"
  try {
    var response = await fetch(url)
    var text = await readBoundedText(response)
  } catch (error) {
    return []
  }
  var panos = []
  var match
  var re = /\[2,"([^"]+)"\],null,\[\[null,null,(-?\d+\.\d+),(-?\d+\.\d+)\]/g
  while ((match = re.exec(text))) {
    if (!safePanoid(match[1])) continue
    if (match[1].indexOf("CIHM0og") === 0 || match[1].length > 22) continue
    panos.push({ pano: match[1], lat: parseFloat(match[2]), lon: parseFloat(match[3]) })
  }
  return panos
}

async function localStreet() {
  var boxes = BOXES.everywhere
  for (var attempt = 0; attempt < 8; attempt++) {
    var box = pick(boxes)
    var lat = box[0] + Math.random() * (box[2] - box[0])
    var lon = box[1] + Math.random() * (box[3] - box[1])
    var tile = tileXY(lat, lon)
    var panos = await officialPanos(tile[0], tile[1])
    if (panos.length) {
      var pano = pick(panos)
      var url = mapsUrlOnly(permalink(pano.pano, pano.lat, pano.lon))
      if (url) return { ok: true, url: url }
    }
  }
  return { ok: false, error: "No walkable Street View found" }
}

async function nextRound() {
  var native = await nativeNext()
  if (native) return native
  return localStreet()
}
