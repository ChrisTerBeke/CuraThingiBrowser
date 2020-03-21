// Copyright (c) 2018 Chris ter Beke.
// Thingiverse plugin is released under the terms of the LGPLv3 or higher.
import QtQuick 2.2
import QtQuick.Controls 2.0
import QtQuick.Dialogs 1.1
import QtQuick.Layouts 1.3
import QtQuick.Window 2.2
import UM 1.1 as UM
import Cura 1.0 as Cura

ColumnLayout
{
    AnimatedImage
    {
        visible: ThingiService.things.length === 0
        source: "loading.gif"
        Layout.alignment: Qt.AlignHCenter
        Layout.topMargin: (parent.height / 2) - (height / 2)
    }

    Cura.SecondaryButton
    {
        text: "Back to collections"
        visible: ThingiService.isFromCollection === true && ThingiService.isQuerying === false
        Layout.leftMargin: 20
        Layout.topMargin: 10
        Layout.bottomMargin: 10
        onClicked: {
            ThingiService.getCollections()
        }
    }

    ThingsList
    {
        id: thingsList
        model: ThingiService.things
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.topMargin: 20
        Layout.bottomMargin: 10
    }

    Cura.SecondaryButton
    {
        text: catalog.i18nc("@button", "Show more results")
        visible: ThingiService.things.length > 0
        Layout.leftMargin: 20
        Layout.bottomMargin: 20
        onClicked: {
            ThingiService.addPage()
            Analytics.trackEvent("show_more_results", "button_clicked")
        }
    }
}
