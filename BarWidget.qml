import QtQuick
import Quickshell
import qs.Ui

BarWidget {
  id: root
  moduleName: "lessunderrated.geoguess"

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
      if (buttonCode === Qt.MiddleButton && panelLoader.item)
        panelLoader.item.dropRandom()
      else if (root.opened) root.close()
      else root.open()
    }
  }
}
