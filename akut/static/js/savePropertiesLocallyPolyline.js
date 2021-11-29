function savePropertiesLocallyPolyline(polylineId) {
    mySavedData.Leitgraeben[polylineId].cost = document.getElementById("inputCostPolyline").value;
    mySavedData.Leitgraeben[polylineId].depth = document.getElementById("inputDepthPolyline").value;
    mySavedData.Leitgraeben[polylineId].leitgrabenOderBoeschung = document.getElementById("selectpickerId").value;
}