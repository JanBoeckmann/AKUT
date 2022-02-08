function getCheckedRadio(radio_group) {
    for (var i = 0; i < radio_group.length; i++) {
        var button = radio_group[i];
        if (button.checked) {
            return button;
        }
    }
    return undefined;
}

function saveBuildingPropertiesLocally(polygonId) {
    var checkedAkteurButton = getCheckedRadio(document.forms.RadioAkteur).value;
    var checkedSchadensklasseButton = getCheckedRadio(document.forms.RadioSchadensklasse).value;
    var opacity = (25*checkedSchadensklasseButton)/100;  // 25/50/75/100
    var fillOpacity = opacity/2;
    mySavedData.Buildings[polygonId].akteur = checkedAkteurButton;
    mySavedData.Buildings[polygonId].schadensklasse = checkedSchadensklasseButton;
    actualPolygon.setStyle({fillColor: colorMapping[checkedAkteurButton], color: colorMapping[checkedAkteurButton], opacity: opacity, fillOpacity: fillOpacity});
}