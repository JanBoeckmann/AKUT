function getCheckedRadio(radio_group) {
    for (var i = 0; i < radio_group.length; i++) {
        var button = radio_group[i];
        if (button.checked) {
            return button;
        }
    }
    return undefined;
}

function saveKatasterLocally(polygonId) {
    var checkedKooperationsbereitschaftButton = getCheckedRadio(document.forms.RadioKooperationsbereitschaft).value;
    mySavedData.Kataster[polygonId].additionalCost = checkedKooperationsbereitschaftButton;
    actualPolygon.setStyle({fillColor: colorMapping[checkedKooperationsbereitschaftButton], color: colorMapping[checkedKooperationsbereitschaftButton]});
}