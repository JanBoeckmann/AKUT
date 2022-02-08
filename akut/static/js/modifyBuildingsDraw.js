$(document).ready(function() {

	$('.formDraw').on('submit', function(event) {
	    selectedRegion = this.id.replace("buttonDraw_", "");
		$.ajax({
			data : {
				dataset: this.id
			},
			type : 'POST',
			url : '/modifyBuildingsDraw_process'
		})
		.done(function(data) {
			$("#bottomDisplayContainer").show()
			$("#bottomActionsContainer").show()

			mySavedData = data;
			highestIdBuildings = 0;

            //load map
			var currentMap = mapsPlaceholder[0];
            if(mapIsLoaded){
                currentMap.eachLayer(function (layer) {
                    currentMap.removeLayer(layer);
                });
            }
            mapIsLoaded = true;

            center_lat = 49.454;
            center_lon = 7.912;
            if(mySavedData.center_lat){
                center_lat = mySavedData.center_lat;
            }
            if(mySavedData.center_lon){
                center_lon = mySavedData.center_lon;
            }

            currentMap.setView([center_lat, center_lon], 14);
            // var baseLayer = L.tileLayer('https://api.mapbox.com/styles/v1/mapbox/streets-v11/tiles/256/{z}/{x}/{y}?access_token=pk.eyJ1IjoiamFuYm9lY2ttYW5uIiwiYSI6ImNqdnowdGViNjBiejg0M21uNHY3YWFqZzQifQ.8uqa5OydY6xJJ05pSNtUCg', {
            //     maxZoom: 22,
            //     attribution: 'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' +
            //     '<a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, ' +
            //     'Imagery © <a href="http://mapbox.com">Mapbox</a>',
            // }).addTo(currentMap);

            var onmapsCopyright = "Karte: onmaps.de ©GeoBasis-DE/BKG/ZSHH 2021";

            var southWest = L.latLng(center_lat - 0.1, center_lon - 0.1),
			    northEast = L.latLng(center_lat + 0.1, center_lon + 0.1),
			    bounds = L.latLngBounds(southWest, northEast);

            var onmapsWMSLayer = L.tileLayer.wms("http://wms.onmaps.de/", {
                key: 'c2c245d7f744b6266fdb4d6ccd43d8e8',
                bounds: bounds,
                // z.B.: 'onmaps_pastell', 'onmaps_dezent', 'onmaps_pastell_strassentexte', 'onmaps_dezent_strassentexte', ...
                layers: 'onmaps_dezent',
                format: 'image/png',
                transparent: true,
                attribution: onmapsCopyright,
                maxZoom: 22
            });

            currentMap.addLayer(onmapsWMSLayer);


            legend.onAdd = function (currentMap) {

                var div = L.DomUtil.create('div', 'info legend');

                div.innerHTML += '<div><i style="background:' + colorMapping["None"] + '"></i> ' + 'nicht zugeordnet <br></div>';
                div.innerHTML += '<div><i style="background:' + colorMapping["Buerger"] + '"></i> ' + 'Bürger <br></div>';
                div.innerHTML += '<div><i style="background:' + colorMapping["Kommune"] + '"></i> ' + 'Kommune <br></div>';
                div.innerHTML += '<div><i style="background:' + colorMapping["Religion"] + '"></i> ' + 'religiöse Einrichtungen <br></div>';
                div.innerHTML += '<div><i style="background:' + colorMapping["LokaleWirtschaft"] + '"></i> ' + 'lokale Wirtschaft <br></div>';
                div.innerHTML += '<div><i style="background:' + colorMapping["Landwirtschaft"] + '"></i> ' + 'Landwirtschaft <br></div>';
                div.innerHTML += '<div><i style="background:' + colorMapping["Forstwirtschaft"] + '"></i> ' + 'Forstwirtschaft <br></div>';

                return div;
            };

            legend.addTo(currentMap);

            // remove draw control
            if(myDrawControl.length > 0){
                myDrawControl[0].remove();
            }

            // Initialise the FeatureGroup to store editable layers
            mymap.addLayer(drawnItems);

            mymap.addControl(myDrawControl);

            mymap.on(L.Draw.Event.CREATED, function (e) {
                var type = e.layerType
                var layer = e.layer;
                if( type == "polygon"){
                    highestIdBuildings = highestIdBuildings + 1;
                    layer.options["title"] = highestIdBuildings;
                    layer.options["type"] = "Building";

                    positionArray = []
                    coordinates = layer.editing.latlngs[0][0]
                    for (position in coordinates){
                        positionArray.push([coordinates[position].lat, coordinates[position].lng]);
                    }
                    mySavedData.Buildings[highestIdBuildings] = {};
                    mySavedData.Buildings[highestIdBuildings]["position"] = positionArray;
                    mySavedData.Buildings[highestIdBuildings]["properties"] = "";
                    mySavedData.Buildings[highestIdBuildings]["active"] = 1;
                    mySavedData.Buildings[highestIdBuildings]["akteur"] = "None";
                    mySavedData.Buildings[highestIdBuildings]["schadensklasse"] = 2;
                    mySavedData.Buildings[highestIdBuildings]["gebaeudeklasse"] = 9999;
                }
                drawnItems.addLayer(layer);
            });

            mymap.on(L.Draw.Event.EDITED, function (e) {
                var type = e.layerType
                var layers = e.layers._layers;
                var BuildingId = "none";
                //iterate over changed layers
                for (var key in layers) {
                    if(layers[key].options.type == "Building"){
                        if (layers.hasOwnProperty(key)){
                            buildingId = layers[key].options.title;
                            coordinates = layers[key].editing.latlngs[0][0]
                            positionArray = []
                            for (position in coordinates){
                                positionArray.push([coordinates[position].lat, coordinates[position].lng]);
                            }
                            mySavedData.Buildings[buildingId]["position"] = positionArray;
                        }
                    }
                }
            });

            mymap.on(L.Draw.Event.DELETED, function (e) {
                var layers = e.layers._layers;
                var nodeId = "none";

                for (var key in layers) {
                    if(layers[key].options.type == "Building"){
                        //check if layer is not inherited
                        if (layers.hasOwnProperty(key)) {
                            nodeId = layers[key].options.title;
                            delete mySavedData.Buildings[nodeId];
                        }
                    }
                }
            });

            for (building in mySavedData.Buildings){
                var color = colorMapping[mySavedData.Buildings[building].akteur];
                var schkl = mySavedData.Buildings[building].schadensklasse;
                var opacity = (25*schkl)/100;  // 25/50/75/100
                var fillOpacity = opacity/2;

                if (mySavedData.Buildings[building].active.toString() == "1"){
                    var m = L.polygon( mySavedData.Buildings[building]["position"], {title: building, type: "Building", properties: mySavedData.Buildings[building].properties, active: mySavedData.Buildings[building].active.toString(), fillColor: color, color: color, opacity: opacity, fillOpacity: fillOpacity})
                }else{
                    var m = L.polygon( mySavedData.Buildings[building]["position"], {title: building, type: "Building", properties: mySavedData.Buildings[building].properties, active: mySavedData.Buildings[building].active.toString(), fillColor: color, color: color, opacity: opacity, fillOpacity: fillOpacity})
                }
                drawnItems.addLayer(m);
                if (highestIdBuildings < parseInt(building)){
                    highestIdBuildings = parseInt(building);
                }
                m.on('click', onPolygonClick);
                function onPolygonClick(event){
                    $("#bottomPropertiesContainer").show();
                    actualPolygon = this;
                    polygonId = this.options.title;
                    polygonProperties = mySavedData.Buildings[polygonId];
                    document.getElementById("schadensklasse" + polygonProperties.schadensklasse).checked = true
                    document.getElementById("akteur" + polygonProperties.akteur).checked = true
                }
            }
		});

		event.preventDefault();

	});

});