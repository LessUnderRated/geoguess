import QtQuick
import QtQuick.Controls as QQC
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "StreetModel.js" as Geo

// Geo Guess: globe for exploring Street View and playing a guessing round.
// Click the globe to pick a spot. Play a round to open a hidden panorama.
Panel {
  id: root
  moduleName: "lessunderrated.geoguess"
  ipcTarget: "lessunderrated.geoguess"
  manageIpc: false

  property var anchorItem: null
  property var hostWidget: null

  property var countries: []
  property var markers: []
  property var selectedMarker: null
  property var selectionPin: null
  property real pickedLat: NaN
  property real pickedLon: NaN
  property string pickedLabel: ""
  property string panoUrl: ""
  property string panoMapUrl: ""
  property bool landmarkView: false
  property string statusText: ""
  property bool resolving: false
  property bool lookupQueued: false
  property real queuedLat: NaN
  property real queuedLon: NaN
  property string queuedName: ""
  property string lookupPurpose: "browse"
  property bool suppressLookup: false

  property bool playing: false
  property string regionId: "everywhere"
  property var regionIds: ["everywhere", "usa", "eu", "asia", "landmarks"]
  property string roundPhase: ""
  property int roundNumber: 0
  property int roundAttempts: 0
  property int roundScore: 0
  property int totalScore: 0
  property real answerLat: NaN
  property real answerLon: NaN
  property string answerName: ""
  property var answerPin: null

  readonly property string lookupPath: Qt.resolvedUrl("streetview-lookup").toString().replace(/^file:\/\//, "")

  function open() {
    root.controller.show()
  }

  function close() {
    root.controller.hide()
  }

  function switchPanel(direction) {
    if (root.bar && typeof root.bar.switchPanelFrom === "function")
      return root.bar.switchPanelFrom(root.hostWidget || root, direction)
    return false
  }

  function mapLink(lat, lon) {
    return "https://www.google.com/maps/@?api=1&map_action=map&center=" + lat.toFixed(6) + "," + lon.toFixed(6) + "&zoom=14"
  }

  function startLookup(lat, lon, name) {
    resolving = true
    lookupProc.command = name
      ? [lookupPath, "resolve", String(lat), String(lon), name]
      : [lookupPath, "resolve", String(lat), String(lon)]
    lookupProc.running = true
  }

  function resolveLatLon(lat, lon, label, marker) {
    var flat = Number(lat), flon = Number(lon)
    if (!isFinite(flat) || !isFinite(flon)) return
    lookupPurpose = "browse"
    pickedLat = flat
    pickedLon = flon
    pickedLabel = label || (flat.toFixed(4) + ", " + flon.toFixed(4))
    selectionPin = {
      uuid: "selection-pin",
      name: pickedLabel,
      latitude: flat,
      longitude: flon
    }
    selectedMarker = selectionPin
    landmarkView = false
    panoUrl = ""
    panoMapUrl = mapLink(flat, flon)
    statusText = "Looking up the nearest panorama near " + pickedLabel + "…"
    if (lookupProc.running) {
      queuedLat = flat
      queuedLon = flon
      queuedName = marker ? pickedLabel : ""
      lookupQueued = true
      return
    }
    startLookup(flat, flon, marker ? pickedLabel : "")
  }

  function activateMarker(marker) {
    if (!marker) return
    var flat = Number(marker.latitude), flon = Number(marker.longitude)
    globe.focusCoordinate(flat, flon)
    if (marker.url) {
      pickedLat = flat
      pickedLon = flon
      pickedLabel = String(marker.name || "")
      selectionPin = {
        uuid: "selection-pin",
        name: pickedLabel,
        latitude: flat,
        longitude: flon
      }
      selectedMarker = selectionPin
      landmarkView = true
      panoUrl = String(marker.url)
      panoMapUrl = mapLink(flat, flon)
      statusText = pickedLabel
      resolving = false
      return
    }
    resolveLatLon(flat, flon, String(marker.name || ""), marker)
    landmarkView = true
  }

  function openBrowse() {
    if (!panoUrl || !root.bar) return
    var openPath = lookupPath.replace(/streetview-lookup$/, "open-streetview")
    var url = String(panoUrl).split("#")[0]
    root.bar.run("'" + openPath + "' '" + url + "'")
    close()
  }

  function openStreetView() {
    if (!panoUrl || !root.bar) return
    var openPath = lookupPath.replace(/streetview-lookup$/, "open-streetview")
    var roundUrl = String(panoUrl).split("#")[0] + "#geoguess"
    root.bar.run("'" + openPath + "' '" + roundUrl + "'")
  }

  function openMap() {
    if (!panoMapUrl || !root.bar) return
    root.bar.run("omarchy-launch-webapp '" + panoMapUrl + "'")
  }

  function distanceKm(lat1, lon1, lat2, lon2) {
    var radius = 6371
    var p1 = lat1 * Math.PI / 180
    var p2 = lat2 * Math.PI / 180
    var dLat = (lat2 - lat1) * Math.PI / 180
    var dLon = (lon2 - lon1) * Math.PI / 180
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
      + Math.cos(p1) * Math.cos(p2) * Math.sin(dLon / 2) * Math.sin(dLon / 2)
    return 2 * radius * Math.asin(Math.min(1, Math.sqrt(a)))
  }

  function scoreForKm(km) {
    return Math.round(5000 * Math.exp(-km / 2000))
  }

  function randomLand() {
    var features = countries
    for (var i = 0; i < 80; i++) {
      var lat = Math.random() * 140 - 70
      var lon = Math.random() * 360 - 180
      var hit = Geo.countryAt(features, lat, lon)
      if (hit && hit.code && String(hit.code) !== "-99")
        return { lat: lat, lon: lon }
    }
    return null
  }

  function startRound() {
    if (!countries || countries.length === 0) {
      statusText = "Map is still loading"
      return
    }
    playing = true
    roundPhase = "seeking"
    roundNumber += 1
    roundAttempts = 0
    roundScore = 0
    answerName = ""
    answerPin = null
    selectedMarker = null
    panoUrl = ""
    pickedLabel = ""
    globe.centreLatitude = 18
    globe.centreLongitude = -20
    globe.globeScale = 1
    statusText = "Round " + roundNumber + " · finding a panorama…"
    close()
    seekRound()
  }

  IpcHandler {
    target: "lessunderrated.geoguess-region"
    function region(): string { return root.regionId }
  }

  function seekRound() {
    roundAttempts += 1
    lookupPurpose = "round"
    lookupQueued = false
    if (lookupProc.running) {
      lookupQueued = true
      return
    }
    lookupProc.command = [lookupPath, "street", regionId]
    lookupProc.running = true
  }

  function stopRound() {
    playing = false
    roundPhase = ""
    lookupPurpose = "browse"
    lookupQueued = false
    if (lookupProc.running) suppressLookup = true
    answerPin = null
    selectedMarker = null
    panoUrl = ""
    pickedLabel = ""
    statusText = ""
  }

  function submitGuess(lat, lon) {
    var km = distanceKm(lat, lon, answerLat, answerLon)
    roundScore = scoreForKm(km)
    totalScore += roundScore
    roundPhase = "result"
    answerPin = {
      uuid: "round-answer",
      name: answerName || "Answer",
      latitude: answerLat,
      longitude: answerLon
    }
    selectedMarker = answerPin
    globe.focusCoordinate(answerLat, answerLon)
    var away = km < 1 ? (Math.round(km * 1000) + " m") : (km.toFixed(km < 10 ? 1 : 0) + " km")
    statusText = "Round " + roundNumber + " · " + away + " · " + roundScore
      + " pts · total " + totalScore
      + (answerName ? " · " + answerName : "")
  }

  function dropRandom() {
    var pool = markers.length > 0 ? markers : []
    if (pool.length === 0) return
    var pick = pool[Math.floor(Math.random() * pool.length)]
    if (opened) activateMarker(pick)
    else { activateMarker(pick); open() }
  }

  FileView {
    path: Qt.resolvedUrl("assets/countries.json").toString().replace(/^file:\/\//, "")
    watchChanges: false
    printErrors: true
    onLoaded: {
      try {
        var collection = JSON.parse(text())
        root.countries = Array.isArray(collection.features) ? collection.features : []
      } catch (e) {
        root.countries = []
        root.statusText = "Map data could not be loaded"
      }
    }
  }

  FileView {
    path: Qt.resolvedUrl("treasures.json").toString().replace(/^file:\/\//, "")
    watchChanges: true
    printErrors: true
    onLoaded: {
      try {
        var rows = JSON.parse(text())
        root.markers = Array.isArray(rows) ? rows : []
      } catch (e) {
        root.markers = []
      }
    }
    onFileChanged: reload()
  }

  Process {
    id: lookupProc
    command: []
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: {
        if (root.suppressLookup) {
          root.suppressLookup = false
          root.resolving = false
          return
        }
        if (root.lookupQueued) return
        try {
          var doc = JSON.parse(String(text || "{}"))
          if (root.lookupPurpose === "round") {
            if (doc && doc.ok === true && doc.url && isFinite(doc.lat) && isFinite(doc.lon)
                && root.roundPhase === "seeking") {
              root.answerLat = doc.lat
              root.answerLon = doc.lon
              root.answerName = doc.name ? String(doc.name) : ""
              root.panoUrl = String(doc.url)
              root.panoMapUrl = ""
              root.pickedLabel = ""
              root.statusText = ""
              root.openStreetView()
              root.playing = false
              root.roundPhase = ""
              root.lookupPurpose = "browse"
            } else if (root.roundAttempts < 4) {
              root.seekRound()
            } else {
              root.playing = false
              root.roundPhase = ""
              root.lookupPurpose = "browse"
              root.statusText = (doc && doc.error) ? String(doc.error) : "No panorama for this round"
            }
          } else if (doc && doc.ok === true && doc.url) {
            root.panoUrl = root.landmarkView && doc.placeUrl ? String(doc.placeUrl) : String(doc.url)
            if (doc.mapUrl) root.panoMapUrl = String(doc.mapUrl)
            var away = ""
            if (isFinite(doc.distanceMeters) && doc.distanceMeters >= 100) {
              away = doc.distanceMeters >= 1000
                ? (" · " + (doc.distanceMeters / 1000).toFixed(1) + " km away")
                : (" · " + doc.distanceMeters + " m away")
            }
            var place = doc.name ? String(doc.name) : root.pickedLabel
            root.statusText = (root.selectedMarker ? "★ " : "Nearest panorama · ")
              + place + away + " — ready to open"
          } else {
            root.panoUrl = ""
            root.statusText = (doc && doc.error) ? String(doc.error) : "No panorama near " + root.pickedLabel
          }
        } catch (e) {
          root.panoUrl = ""
          root.statusText = "Street View lookup failed"
          if (root.lookupPurpose === "round") {
            root.playing = false
            root.roundPhase = ""
          }
        }
        root.resolving = false
      }
    }
    onExited: {
      if (root.lookupQueued && root.lookupPurpose === "round") {
        root.lookupQueued = false
        root.seekRound()
      } else if (root.lookupQueued && isFinite(root.queuedLat) && isFinite(root.queuedLon)) {
        root.lookupQueued = false
        root.startLookup(root.queuedLat, root.queuedLon, root.queuedName)
        return
      }
      root.resolving = false
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.hostWidget || root
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(440))
    contentHeight: panel.fittedContentHeight(column.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }
      onTextKey: function(t) {
        if (root.playing && root.roundPhase === "result" && (t === "n" || t === "N")) root.startRound()
        else if (t === "g" || t === "G") root.playing ? root.stopRound() : root.startRound()
        else if (!root.playing && (t === "r" || t === "R")) root.dropRandom()
        else if (!root.playing && (t === "o" || t === "O" || t === "\r") && root.panoUrl)
          root.openBrowse()
      }

      Column {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Style.space(10)

        Item {
          width: parent.width
          height: Math.max(titleText.implicitHeight, closeButton.implicitHeight)

          Text {
            id: titleText
            textFormat: Text.PlainText
            text: "GEO GUESS"
            color: root.bar.foreground
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.title
            font.bold: true
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
          }
          Button {
            id: closeButton
            iconText: ""
            tooltipText: "Close (Esc)"
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            onClicked: root.close()
          }
        }

        Item {
          width: parent.width
          height: Style.space(440)

          Globe {
            id: globe
            anchors.fill: parent
            countries: root.countries
            stations: root.playing ? (root.answerPin ? [root.answerPin] : []) : root.markers.concat(root.selectionPin ? [root.selectionPin] : [])
            selectedStation: root.playing ? root.answerPin : root.selectedMarker
            accentColor: Color.accent
            textColor: root.bar.foreground
            fontFamily: root.bar.fontFamily
            onStationActivated: function(station) {
              if (root.roundPhase === "guess") return
              if (root.playing || root.roundPhase === "seeking") root.stopRound()
              root.activateMarker(station)
            }
            onCoordinateActivated: function(lat, lon) {
              if (root.roundPhase === "guess") root.submitGuess(lat, lon)
              else {
                if (root.playing || root.roundPhase === "seeking") root.stopRound()
                root.resolveLatLon(lat, lon, "")
              }
            }
          }
        }

        Text {
          readonly property string line: (root.resolving && !root.playing)
            ? ("Locating nearest panorama near " + root.pickedLabel + "…")
            : root.statusText
          width: parent.width
          visible: line !== ""
          wrapMode: Text.Wrap
          textFormat: Text.PlainText
          text: line
          horizontalAlignment: Text.AlignHCenter
          color: root.bar.foreground
          opacity: 0.85
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.bodySmall
        }

        Item {
          width: parent.width
          height: Math.max(playButton.implicitHeight, regionBox.implicitHeight)

          QQC.ComboBox {
            id: regionBox
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: playButton.left
            anchors.rightMargin: Style.space(8)
            width: Math.max(Style.space(108), playButton.x - Style.space(16))
            model: ["Everywhere", "USA", "Europe", "Asia", "Landmarks"]
            currentIndex: Math.max(0, root.regionIds.indexOf(root.regionId))
            onActivated: function(index) { root.regionId = root.regionIds[index] }
            palette.text: root.bar.foreground
            palette.buttonText: root.bar.foreground
            palette.windowText: root.bar.foreground
            palette.window: Color.popups.background
            palette.button: Color.popups.background
            palette.highlight: Color.menu.selectedBackground
            palette.highlightedText: root.bar.foreground

            contentItem: Text {
              text: regionBox.displayText
              color: root.bar.foreground
              font.family: root.bar.fontFamily
              font.pixelSize: Style.font.bodySmall
              horizontalAlignment: Text.AlignHCenter
              verticalAlignment: Text.AlignVCenter
              elide: Text.ElideRight
            }

            indicator: Text {
              text: "▾"
              color: root.bar.foreground
              font.family: root.bar.fontFamily
              font.pixelSize: Style.font.bodySmall
              anchors.right: parent.right
              anchors.rightMargin: Style.space(10)
              anchors.verticalCenter: parent.verticalCenter
            }

            background: Rectangle {
              color: "transparent"
              radius: Style.space(8)
              border.width: 1
              border.color: Qt.rgba(root.bar.foreground.r, root.bar.foreground.g, root.bar.foreground.b, 0.35)
            }

            popup: QQC.Popup {
              y: regionBox.height + Style.space(4)
              width: regionBox.width
              padding: Style.space(4)
              contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: regionBox.popup.visible ? regionBox.delegateModel : null
                currentIndex: regionBox.highlightedIndex
              }
              background: Rectangle {
                color: Color.popups.background
                radius: Style.space(8)
                border.width: 1
                border.color: Color.popups.border
              }
            }
          }

          Button {
            id: playButton
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.verticalCenter: parent.verticalCenter
            text: "Play Geo Guess"
            tooltipText: "Drop into a random Street View and guess where you are"
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            onClicked: root.startRound()
          }

          Button {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: playButton.right
            anchors.leftMargin: Style.space(8)
            visible: root.pickedLabel !== "" && !root.playing
            enabled: root.panoUrl !== ""
            text: root.landmarkView ? "View landmark" : "Nearest view"
            tooltipText: root.landmarkView ? "Open this landmark panorama" : "Open the nearest panorama found for this spot"
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            onClicked: root.openBrowse()
          }
        }

        Item {
          width: parent.width
          height: actionRow.implicitHeight
          visible: actionRow.visible

          Row {
            id: actionRow
            spacing: Style.space(8)
            anchors.horizontalCenter: parent.horizontalCenter
            visible: root.playing || root.pickedLabel !== ""

          Button {
            iconText: ""
            tooltipText: "Random treasure (R)"
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            visible: !root.playing && root.pickedLabel !== ""
            onClicked: root.dropRandom()
          }
          Button {
            iconText: ""
            tooltipText: "Open map view instead"
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            visible: !root.playing && root.pickedLabel !== ""
            enabled: root.panoMapUrl !== ""
            onClicked: root.openMap()
          }
          Button {
            visible: root.playing && root.roundPhase === "result"
            text: "Next round"
            tooltipText: "Another random Street View"
            foreground: root.bar.foreground
            fontFamily: root.bar.fontFamily
            onClicked: root.startRound()
          }
          }
        }

      }
    }
  }
}
