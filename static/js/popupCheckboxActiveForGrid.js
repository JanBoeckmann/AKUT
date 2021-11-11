function handleClick(cb) {
    if(cb.checked){
        mySavedData.Relevant[parseInt(cb.value)] = 1;
        activePolygon.setStyle({fillColor: "#660066"});
    }else if(mySavedData.connectedToRelevantNode[parseInt(cb.value)] == 1){
        mySavedData.Relevant[parseInt(cb.value)] = 0;
        activePolygon.setStyle({fillColor: "#9933ff"});
    }else{
        mySavedData.Relevant[parseInt(cb.value)] = 0;
        activePolygon.setStyle({fillColor: "#add8e6"});
    }
}