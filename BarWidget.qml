import QtQuick
import Quickshell
import qs.Ui

BarWidget {
  id: root
  moduleName: "lessunderrated.geoguess"
  property var pluginRegistry: null

  readonly property string home: Quickshell.env("HOME")
  readonly property string pluginDir: home + "/.config/omarchy/plugins/lessunderrated.geoguess"
  readonly property string uninstallScript: home + "/.config/omarchy/lessunderrated.geoguess.uninstall.py"

  property bool wasEnabled: false
  property bool tearingDown: false

  readonly property bool opened: panelLoader.item
    ? panelLoader.item.opened === true
    : false
  readonly property bool popoutSwitchClosing: panelLoader.item
    ? panelLoader.item.popoutSwitchClosing === true
    : false

  function open() {
    if (panelLoader.item) panelLoader.item.open()
  }

  function close() {
    if (panelLoader.item) panelLoader.item.close()
  }

  function toggle() {
    if (panelLoader.item) panelLoader.item.toggle()
  }

  function closeForPopoutSwitch() {
    if (panelLoader.item) panelLoader.item.closeForPopoutSwitch()
  }

  function injectPanel() {
    if (!panelLoader.item) return
    panelLoader.item.bar = root.bar
    panelLoader.item.anchorItem = button
    panelLoader.item.hostWidget = root
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  onBarChanged: injectPanel()

  function ensureRuntime() {
    Quickshell.execDetached(["python3", root.pluginDir + "/uninstall.py", "setup"])
  }

  function teardownRuntime() {
    if (root.tearingDown) return
    root.tearingDown = true
    var script = root.uninstallScript
    Quickshell.execDetached(["python3", script, "--unless-enabled"])
  }

  onPluginRegistryChanged: {
    if (root.pluginRegistry && root.pluginRegistry.enabled === true)
      root.wasEnabled = true
  }

  Connections {
    target: root.pluginRegistry
    function onEnabledChanged() {
      if (!root.pluginRegistry) return
      if (root.pluginRegistry.enabled === true) {
        root.wasEnabled = true
        root.tearingDown = false
        root.ensureRuntime()
        return
      }
      if (root.wasEnabled) root.teardownRuntime()
    }
  }

  Component.onCompleted: {
    if (root.pluginRegistry && root.pluginRegistry.enabled === true)
      root.wasEnabled = true
    root.ensureRuntime()
  }

  Component.onDestruction: root.teardownRuntime()

  Loader {
    id: panelLoader
    active: true
    source: Qt.resolvedUrl("Panel.qml")
    visible: false
    onLoaded: {
      root.injectPanel()
      Qt.callLater(root.injectPanel)
    }
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: ""
    tooltipText: panelLoader.item && panelLoader.item.pickedLabel
      ? ("Geo Guess — " + panelLoader.item.pickedLabel)
      : "Open Geo Guess"
    onPressed: function(buttonCode) {
      if (!root.bar) return
      if (buttonCode === Qt.LeftButton) root.toggle()
    }
  }
}
