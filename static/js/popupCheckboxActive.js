function handleClick(cb) {
    if(cb.checked){
        mySavedData.Buildings[parseInt(cb.value)].active = 1;
        activeMarker.setIcon(blueIcon);
    }else{
        mySavedData.Buildings[parseInt(cb.value)].active = 0;
        activeMarker.setIcon(greyIcon);
    }
}