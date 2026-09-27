import QtQuick
import "StreetModel.js" as Geo

Item {
  id: root

  property var countries: []
  property var stations: []
  property var selectedStation: null
  readonly property string selectedStationUuid: selectedStation ? String(selectedStation.uuid || "") : ""
  readonly property real stationHitRadius: 12
  property string activeCountryCode: ""

  property real centreLatitude: 18
  property real centreLongitude: -20
  property real globeScale: 1
  property real minimumScale: 0.72
  property real maximumScale: 24
  property real longitudeSensitivity: 0.22
  property real latitudeSensitivity: 0.18
  readonly property real kineticLaunchSpeed: 120
  readonly property real kineticMaximumSpeed: 2400
  readonly property real kineticDeceleration: 1800
  readonly property real kineticMaximumFrameTime: 0.1
  readonly property real kineticMaximumSampleAge: 100

  property color backgroundColor: "#090a0c"
  property color sphereColor: "#11151a"
  property color landColor: "#283039"
  property color gridColor: "#7d8791"
  property color outlineColor: "#9099a3"
  property color signalColor: "#d9dee3"
  property color accentColor: "#ff8a3d"
  property color textColor: "#f3f4f5"
  property string fontFamily: "monospace"

  property var hoveredStation: null
  property real hoverX: 0
  property real hoverY: 0
  property var highlightedStation: null
  property real highlightX: 0
  property real highlightY: 0
  property real kineticVelocityX: 0
  property real kineticVelocityY: 0
  property int kineticLaunchGeneration: 0
  property bool suppressNextTap: false
  property var preparedStations: []

  signal stationActivated(var station)
  signal countryActivated(string code, string name)
  signal coordinateActivated(real latitude, real longitude)
  signal interactionStarted()
  signal pointerMoved()

  clip: true
  Accessible.name: "Interactive Geo Guess globe"
  Accessible.description: "Drag or flick to rotate, use the mouse wheel to zoom, and select a place"
  Accessible.role: Accessible.Pane

  function radius() {
    return Math.min(width, height) * 0.44 * globeScale
  }

  function withAlpha(color, alpha) {
    return Qt.rgba(color.r, color.g, color.b, alpha)
  }

  function clearLandingHighlight() {
    highlightedStation = null
    highlightX = 0
    highlightY = 0
  }

  function stopKineticRotation(clearLanding) {
    kineticLaunchGeneration += 1
    kineticAnimation.running = false
    kineticVelocityX = 0
    kineticVelocityY = 0
    if (clearLanding === true) clearLandingHighlight()
  }

  function startKineticRotation(velocityX, velocityY) {
    var launch = Geo.kineticLaunchVelocity(
      velocityX, velocityY, kineticLaunchSpeed, kineticMaximumSpeed)
    if (!launch.active) return false

    kineticLaunchGeneration += 1
    clearLandingHighlight()
    hoveredStation = null
    kineticVelocityX = launch.x
    kineticVelocityY = launch.y
    kineticAnimation.running = true
    return true
  }

  function finishKineticRotation() {
    kineticAnimation.running = false
    kineticVelocityX = 0
    kineticVelocityY = 0
    hoveredStation = null
    var excludedUuid = selectedStation ? selectedStation.uuid : ""
    highlightedStation = Geo.nearestVisibleStation(
      stations, centreLatitude, centreLongitude, excludedUuid,
      width, height, globeScale)
  }

  function rotateByPointerDelta(deltaX, deltaY) {
    centreLongitude = Geo.wrapLongitude(
      centreLongitude - deltaX * longitudeSensitivity / globeScale)
    centreLatitude = Geo.clamp(
      centreLatitude + deltaY * latitudeSensitivity / globeScale, -78, 78)
  }

  function stationByUuid(uuid) {
    var wanted = String(uuid || "")
    var rows = Array.isArray(stations) ? stations : []
    for (var i = 0; i < rows.length; i++)
      if (String(rows[i] && rows[i].uuid || "") === wanted) return rows[i]
    return null
  }

  function refreshLandingHighlight() {
    if (!highlightedStation) return
    var replacement = stationByUuid(highlightedStation.uuid)
    if (!replacement) {
      clearLandingHighlight()
      return
    }
    highlightedStation = replacement
    updateHighlightPosition()
  }

  function updateHighlightPosition() {
    if (!highlightedStation) return
    var position = Geo.stationPosition(
      highlightedStation, width, height, globeScale, centreLatitude, centreLongitude)
    if (!position) {
      clearLandingHighlight()
      return
    }
    highlightX = position.x
    highlightY = position.y
  }

  function focusCoordinate(latitude, longitude) {
    var nextLatitude = Number(latitude)
    var nextLongitude = Number(longitude)
    if (!isFinite(nextLatitude) || !isFinite(nextLongitude)) return

    stopKineticRotation(true)
    centreLatitude = Geo.clamp(nextLatitude, -78, 78)
    centreLongitude = Geo.wrapLongitude(nextLongitude)
  }

  function focusCountry(code) {
    var coordinate = Geo.countryCentre(countries, code)
    if (coordinate) focusCoordinate(coordinate.latitude, coordinate.longitude)
  }

  function markerPlacement(station) {
    return Geo.stationPosition(
      station, width, height, globeScale, centreLatitude, centreLongitude)
  }

  function prepareStationGeometry() {
    var output = []
    var rows = Array.isArray(stations) ? stations : []
    for (var i = 0; i < rows.length; i++) {
      var station = rows[i]
      if (!station || station.latitude === null || station.longitude === null) continue
      output.push({
        station: station,
        visible: false,
        screenX: 0,
        screenY: 0,
        depth: -1
      })
    }
    return output
  }

  function paintLandRing(ctx, ring, mapWidth, mapHeight) {
    if (!Array.isArray(ring) || ring.length < 3) return
    var drawing = false
    var previousLongitude = 0
    ctx.beginPath()
    for (var i = 0; i < ring.length; i++) {
      var longitude = Number(ring[i][0])
      var latitude = Number(ring[i][1])
      if (!isFinite(longitude) || !isFinite(latitude)) continue
      if (drawing) {
        var jump = longitude - previousLongitude
        if (jump > 180 || jump < -180) {
          ctx.closePath()
          ctx.fill()
          ctx.beginPath()
          drawing = false
        }
      }
      var x = (longitude + 180) / 360 * mapWidth
      var y = (90 - latitude) / 180 * mapHeight
      if (!drawing) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
      drawing = true
      previousLongitude = longitude
    }
    if (drawing) {
      ctx.closePath()
      ctx.fill()
    }
  }

  function strokeLandRing(ctx, ring, mapWidth, mapHeight) {
    if (!Array.isArray(ring) || ring.length < 3) return
    var drawing = false
    var previousLongitude = 0
    ctx.beginPath()
    for (var i = 0; i < ring.length; i++) {
      var longitude = Number(ring[i][0])
      var latitude = Number(ring[i][1])
      if (!isFinite(longitude) || !isFinite(latitude)) continue
      if (drawing) {
        var jump = longitude - previousLongitude
        if (jump > 180 || jump < -180) {
          ctx.stroke()
          ctx.beginPath()
          drawing = false
        }
      }
      var x = (longitude + 180) / 360 * mapWidth
      var y = (90 - latitude) / 180 * mapHeight
      if (!drawing) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
      drawing = true
      previousLongitude = longitude
    }
    if (drawing) ctx.stroke()
  }

  function paintLandAtlas(ctx) {
    var mapWidth = landAtlas.width
    var mapHeight = landAtlas.height
    ctx.reset()
    ctx.clearRect(0, 0, mapWidth, mapHeight)
    var rows = Array.isArray(countries) ? countries : []
    var activeCode = activeCountryCode.toUpperCase()
    var highlighted = []
    // Wikipedia "Google Street View coverage": public coverage is a bold name
    // with an asterisk. Everything else is little or no Street View.
    var uncovered = {
      "AF": true, "DZ": true, "AO": true, "AQ": true, "AM": true, "AZ": true,
      "BS": true, "BZ": true, "BJ": true, "BI": true, "BF": true, "CM": true,
      "CF": true, "TD": true, "CN": true, "CG": true, "CD": true, "CU": true,
      "CY": true, "DJ": true, "EG": true, "GQ": true, "ER": true, "ET": true,
      "FK": true, "FJ": true, "TF": true, "GA": true, "GM": true, "GN": true,
      "GW": true, "GY": true, "HT": true, "HN": true, "IR": true, "IQ": true,
      "CI": true, "JM": true, "KW": true, "LR": true, "LY": true, "MG": true,
      "MW": true, "ML": true, "MR": true, "MD": true, "MA": true, "MZ": true,
      "MM": true, "NC": true, "NI": true, "NE": true, "KP": true, "PK": true,
      "PG": true, "PY": true, "SA": true, "SL": true, "SB": true, "SO": true,
      "SS": true, "SD": true, "SR": true, "SY": true, "TJ": true, "TZ": true,
      "TL": true, "TG": true, "TT": true, "TM": true, "UZ": true, "VU": true,
      "VE": true, "EH": true, "YE": true, "ZM": true, "ZW": true, "BN": true,
      "SV": true
    }
    for (var i = 0; i < rows.length; i++) {
      var feature = rows[i]
      if (!feature || !feature.geometry) continue
      var code = String(feature.properties && feature.properties.code || "").toUpperCase()
      ctx.fillStyle = uncovered[code] ? "#330000" : "#ff0000"
      if (code === activeCode) {
        highlighted.push(feature)
        continue
      }
      var geometry = feature.geometry
      var polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates
      if (!Array.isArray(polygons)) continue
      for (var p = 0; p < polygons.length; p++)
        paintLandRing(ctx, polygons[p] && polygons[p][0], mapWidth, mapHeight)
    }
    ctx.fillStyle = "#00ff00"
    for (var h = 0; h < highlighted.length; h++) {
      var activeGeometry = highlighted[h].geometry
      var activePolygons = activeGeometry.type === "Polygon"
        ? [activeGeometry.coordinates] : activeGeometry.coordinates
      if (!Array.isArray(activePolygons)) continue
      for (var ringIndex = 0; ringIndex < activePolygons.length; ringIndex++)
        paintLandRing(ctx, activePolygons[ringIndex] && activePolygons[ringIndex][0], mapWidth, mapHeight)
    }

    // Blue channel is the border mask. Drawn thick so country lines stay
    // readable after the GPU globe samples this texture.
    ctx.strokeStyle = "#0000ff"
    ctx.lineWidth = Math.max(1.25, mapWidth / 1400)
    ctx.lineJoin = "round"
    ctx.lineCap = "round"
    for (var borderIndex = 0; borderIndex < rows.length; borderIndex++) {
      var borderFeature = rows[borderIndex]
      if (!borderFeature || !borderFeature.geometry) continue
      var borderGeometry = borderFeature.geometry
      var borderPolygons = borderGeometry.type === "Polygon"
        ? [borderGeometry.coordinates] : borderGeometry.coordinates
      if (!Array.isArray(borderPolygons)) continue
      for (var borderRing = 0; borderRing < borderPolygons.length; borderRing++)
        strokeLandRing(ctx, borderPolygons[borderRing] && borderPolygons[borderRing][0], mapWidth, mapHeight)
    }
  }

  function stationUnderPointer(x, y) {
    var nearest = null
    var nearestDistance = stationHitRadius * stationHitRadius
    for (var i = 0; i < preparedStations.length; i++) {
      var station = preparedStations[i].station
      var position = markerPlacement(station)
      if (!position) continue
      var deltaX = position.x - x
      var deltaY = position.y - y
      var distance = deltaX * deltaX + deltaY * deltaY
      if (distance > nearestDistance) continue
      nearest = station
      nearestDistance = distance
    }
    return nearest
  }

  function activateAt(x, y) {
    clearLandingHighlight()
    var station = stationUnderPointer(x, y)
    if (station) {
      stationActivated(station)
      return
    }

    var globeRadius = radius()
    var normalizedX = (x - width / 2) / globeRadius
    var normalizedY = -(y - height / 2) / globeRadius
    var coordinate = Geo.unproject(
      normalizedX, normalizedY, centreLatitude, centreLongitude)
    if (!coordinate) return
    coordinateActivated(coordinate.latitude, coordinate.longitude)
    var country = Geo.countryAt(
      countries, coordinate.latitude, coordinate.longitude)
    if (!country || !country.code || country.code === "-99") return
    countryActivated(String(country.code).toUpperCase(), String(country.name || country.code))
  }

  onCountriesChanged: {
    landAtlas.requestPaint()
    if (activeCountryCode) focusCountry(activeCountryCode)
  }
  onStationsChanged: {
    preparedStations = prepareStationGeometry()
    refreshLandingHighlight()
  }
  onSelectedStationUuidChanged: clearLandingHighlight()
  onActiveCountryCodeChanged: landAtlas.requestPaint()
  onCentreLatitudeChanged: updateHighlightPosition()
  onCentreLongitudeChanged: updateHighlightPosition()
  onGlobeScaleChanged: updateHighlightPosition()
  onWidthChanged: updateHighlightPosition()
  onHeightChanged: updateHighlightPosition()
  onHighlightedStationChanged: updateHighlightPosition()
  onVisibleChanged: {
    if (!visible) stopKineticRotation(true)
  }

  // Equirectangular land mask. Painted once, then sampled by the shader.
  Canvas {
    id: landAtlas
    width: 2048
    height: 1024
    visible: false
    renderTarget: Canvas.FramebufferObject
    renderStrategy: Canvas.Cooperative
    onPaint: {
      var ctx = getContext("2d")
      if (ctx) root.paintLandAtlas(ctx)
    }
  }

  ShaderEffect {
    id: globeShader
    anchors.fill: parent
    fragmentShader: Qt.resolvedUrl("globe.frag.qsb")

    property color oceanColor: root.sphereColor
    property color landColor: root.landColor
    property color highlightColor: root.accentColor
    property color gridColor: root.withAlpha(root.gridColor, 0.55)
    property color backgroundColor: root.backgroundColor
    property color rimColor: root.outlineColor
    property vector2d viewSize: Qt.vector2d(width, height)
    property real latitude: root.centreLatitude
    property real longitude: root.centreLongitude
    property real radiusPx: root.radius()
    property variant landMap: landAtlas
  }

  Repeater {
    model: root.preparedStations

    delegate: Item {
      required property var modelData
      property var place: root.markerPlacement(modelData.station)
      property bool hot: root.hoveredStation
        && modelData.station.uuid === root.hoveredStation.uuid
      property bool pinned: modelData.station.uuid === "selection-pin"
        || modelData.station.uuid === "round-answer"
      visible: !!place
      x: place ? place.x : 0
      y: place ? place.y : 0

      Item {
        visible: parent.pinned
        width: 14
        height: 20
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.verticalCenter
        Rectangle {
          width: 12
          height: 12
          radius: 6
          color: root.accentColor
          border.color: "#ffffff"
          border.width: 1.5
          anchors.horizontalCenter: parent.horizontalCenter
          anchors.top: parent.top
        }
        Rectangle {
          width: 2
          height: 8
          color: root.accentColor
          anchors.horizontalCenter: parent.horizontalCenter
          anchors.bottom: parent.bottom
        }
      }

      Rectangle {
        visible: !parent.pinned
        property real depth: parent.place ? parent.place.z : 0
        property real markerRadius: parent.hot ? 3.7 : 1.7 + depth * 1.25
        width: markerRadius * 2
        height: width
        radius: width / 2
        color: parent.hot ? root.accentColor : root.signalColor
        opacity: parent.hot ? 1 : 0.42 + depth * 0.48
        anchors.centerIn: parent
      }
    }
  }

  Component.onCompleted: {
    preparedStations = prepareStationGeometry()
    landAtlas.requestPaint()
  }

  HoverHandler {
    id: hoverHandler
    cursorShape: dragHandler.active || tapHandler.pressed
      ? Qt.ClosedHandCursor
      : (root.hoveredStation ? Qt.PointingHandCursor : Qt.OpenHandCursor)

    onPointChanged: {
      root.hoverX = point.position.x
      root.hoverY = point.position.y
      root.pointerMoved()
      root.hoveredStation = kineticAnimation.running || dragHandler.active
        ? null : root.stationUnderPointer(point.position.x, point.position.y)
    }

    onHoveredChanged: {
      if (!hovered) root.hoveredStation = null
    }
  }

  TapHandler {
    id: tapHandler
    acceptedButtons: Qt.LeftButton
    gesturePolicy: TapHandler.DragThreshold

    onPressedChanged: {
      if (!pressed) return
      root.interactionStarted()
      var caughtKineticRotation = kineticAnimation.running
      root.stopKineticRotation(true)
      root.suppressNextTap = caughtKineticRotation
      root.hoveredStation = null
    }

    onTapped: function(eventPoint) {
      if (root.suppressNextTap) {
        root.suppressNextTap = false
        return
      }
      root.activateAt(eventPoint.position.x, eventPoint.position.y)
      root.hoveredStation = hoverHandler.hovered
        ? root.stationUnderPointer(eventPoint.position.x, eventPoint.position.y) : null
    }

    onCanceled: root.suppressNextTap = false
  }

  DragHandler {
    id: dragHandler
    target: null
    acceptedButtons: Qt.LeftButton

    property bool wasActive: false
    property bool launchCanceled: false
    property bool launchPending: false
    property int pendingLaunchGeneration: 0
    property real pendingVelocityX: 0
    property real pendingVelocityY: 0
    property real recentVelocityX: 0
    property real recentVelocityY: 0
    property real recentVelocityAt: 0
    property real samplePositionX: 0
    property real samplePositionY: 0
    property real sampleStartedAt: 0

    function resetMotionSample() {
      recentVelocityX = 0
      recentVelocityY = 0
      recentVelocityAt = 0
      samplePositionX = centroid.position.x
      samplePositionY = centroid.position.y
      sampleStartedAt = Date.now()
    }

    function recordMotionSample() {
      var now = Date.now()
      var elapsedMilliseconds = now - sampleStartedAt
      if (elapsedMilliseconds <= 0) return

      var deltaX = centroid.position.x - samplePositionX
      var deltaY = centroid.position.y - samplePositionY
      samplePositionX = centroid.position.x
      samplePositionY = centroid.position.y
      sampleStartedAt = now
      if (elapsedMilliseconds > 250) return

      var sampledVelocityX = deltaX * 1000 / elapsedMilliseconds
      var sampledVelocityY = deltaY * 1000 / elapsedMilliseconds
      if (!isFinite(sampledVelocityX) || !isFinite(sampledVelocityY)) return
      if (recentVelocityAt > 0) {
        recentVelocityX = recentVelocityX * 0.25 + sampledVelocityX * 0.75
        recentVelocityY = recentVelocityY * 0.25 + sampledVelocityY * 0.75
      } else {
        recentVelocityX = sampledVelocityX
        recentVelocityY = sampledVelocityY
      }
      recentVelocityAt = now
    }

    onActiveChanged: {
      if (active) {
        root.stopKineticRotation(true)
        wasActive = true
        launchCanceled = false
        launchPending = false
        root.suppressNextTap = false
        root.interactionStarted()
        root.hoveredStation = null
        resetMotionSample()
        return
      }
      if (!wasActive) return

      wasActive = false
      var releaseVelocity = Geo.kineticReleaseVelocity(
        centroid.velocity.x, centroid.velocity.y,
        recentVelocityX, recentVelocityY,
        recentVelocityAt > 0 ? Date.now() - recentVelocityAt : Infinity,
        root.kineticMaximumSampleAge)
      pendingVelocityX = releaseVelocity.x
      pendingVelocityY = releaseVelocity.y
      pendingLaunchGeneration = root.kineticLaunchGeneration
      launchPending = !launchCanceled
      Qt.callLater(function() {
        if (!dragHandler.launchPending || dragHandler.launchCanceled) return
        if (dragHandler.pendingLaunchGeneration !== root.kineticLaunchGeneration) {
          dragHandler.launchPending = false
          return
        }
        dragHandler.launchPending = false
        root.startKineticRotation(
          dragHandler.pendingVelocityX, dragHandler.pendingVelocityY)
      })
    }

    onTranslationChanged: function(delta) {
      if (!active) return
      recordMotionSample()
      root.rotateByPointerDelta(delta.x, delta.y)
    }

    onCanceled: {
      launchCanceled = true
      launchPending = false
      recentVelocityAt = 0
      root.stopKineticRotation(false)
    }
  }

  WheelHandler {
    id: wheelHandler
    target: null
    acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
    blocking: true

    onWheel: function(event) {
      root.interactionStarted()
      root.stopKineticRotation(true)
      root.suppressNextTap = false
      root.hoveredStation = null
      var factor = Math.exp(event.angleDelta.y / 720)
      root.globeScale = Geo.clamp(
        root.globeScale * factor, root.minimumScale, root.maximumScale)
      event.accepted = true
    }
  }

  FrameAnimation {
    id: kineticAnimation
    running: false

    onTriggered: {
      if (frameTime > root.kineticMaximumFrameTime) {
        root.stopKineticRotation(true)
        return
      }
      if (frameTime <= 0) return

      var step = Geo.advanceKineticRotation({
        longitude: root.centreLongitude,
        latitude: root.centreLatitude,
        velocityX: root.kineticVelocityX,
        velocityY: root.kineticVelocityY
      }, frameTime, {
        deceleration: root.kineticDeceleration,
        scale: root.globeScale,
        longitudeSensitivity: root.longitudeSensitivity,
        latitudeSensitivity: root.latitudeSensitivity,
        minimumLatitude: -78,
        maximumLatitude: 78
      })
      root.kineticVelocityX = step.velocityX
      root.kineticVelocityY = step.velocityY
      root.centreLongitude = step.longitude
      root.centreLatitude = step.latitude
      if (!step.active) root.finishKineticRotation()
    }
  }

  Rectangle {
    id: tooltip
    property var station: root.hoveredStation
    property bool landing: false
    property real anchorX: root.hoverX
    property real anchorY: root.hoverY

    visible: !!station && !tapHandler.pressed && !dragHandler.active
      && !kineticAnimation.running
    x: Math.min(root.width - width - 8, Math.max(8, anchorX + 14))
    y: Math.min(root.height - height - 8, Math.max(8, anchorY + 14))
    width: landing
      ? Math.min(280, Math.max(0, root.width - 16))
      : Math.min(280, Math.max(0, root.width - 16), tooltipText.implicitWidth + 20)
    height: tooltipContent.implicitHeight + 14
    color: Qt.rgba(root.backgroundColor.r, root.backgroundColor.g, root.backgroundColor.b, 0.94)
    border.color: root.withAlpha(root.outlineColor, 0.5)
    border.width: 1
    radius: 2

    Column {
      id: tooltipContent
      anchors.centerIn: parent
      width: Math.max(0, parent.width - 20)
      spacing: 2

      Text {
        id: tooltipText
        width: parent.width
        text: tooltip.station
          ? (tooltip.landing ? "Landed near · " : "") + tooltip.station.name
            + (!tooltip.landing && tooltip.station.estimatedLocation === true
              ? " · approximate location" : "")
          : ""
        textFormat: Text.PlainText
        color: root.textColor
        font.family: root.fontFamily
        font.pixelSize: 12
        elide: Text.ElideRight
      }

      Text {
        width: parent.width
        visible: tooltip.landing && tooltip.station
          && tooltip.station.estimatedLocation === true
        text: "approximate location"
        textFormat: Text.PlainText
        color: root.withAlpha(root.textColor, 0.66)
        font.family: root.fontFamily
        font.pixelSize: 11
      }
    }
  }
}
