$(document).ready(function() {

	$('.formDraw').on('submit', function(event) {
	    selectedRegion = this.id.replace("buttonDraw_", "");
		$.ajax({
			data : {
				dataset: this.id
			},
			type : 'POST',
			url : '/modifyGraphDraw_process'
		})
		.done(function(data) {
			$("#bottomDisplayContainer").show()
			$("#bottomActionsContainer").show()

			mySavedData = data;
			highestIdAuffangbecken = 0;
			highestIdLeitgraeben = 0

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

            // var baseLayer = L.tileLayer('https://wms.onmaps.de/?key=f9634f549f74a4e002b743f584f6cb08&layer=onmaps_dezent').addTo(currentMap);

            // remove draw control
            if(myDrawControl.length > 0){
                myDrawControl[0].remove();
            }

            //put in markers
            var useClustering = false;

            // Initialise the FeatureGroup to store editable layers
            mymap.addLayer(drawnItems);

            mymap.addControl(myDrawControl);

            mymap.on(L.Draw.Event.CREATED, function (e) {
                var type = e.layerType
                var layer = e.layer;

                if( type == "polygon"){
                    highestIdAuffangbecken = highestIdAuffangbecken + 1;
                    layer.options["title"] = highestIdAuffangbecken;
                    layer.options["type"] = "Auffangbecken";

                    positionArray = []
                    coordinates = layer.editing.latlngs[0][0]
                    for (position in coordinates){
                        positionArray.push([coordinates[position].lat, coordinates[position].lng]);
                    }
                    mySavedData.Auffangbecken[highestIdAuffangbecken] = {};
                    mySavedData.Auffangbecken[highestIdAuffangbecken]["position"] = positionArray;
                    mySavedData.Auffangbecken[highestIdAuffangbecken]["depth"] = 1;
                    mySavedData.Auffangbecken[highestIdAuffangbecken]["cost"] = 1;
                }else if(type == "polyline"){
                    highestIdLeitgraeben = highestIdLeitgraeben + 1;
                    layer.options["title"] = highestIdLeitgraeben;
                    layer.options["type"] = "Leitrgraben";

                    positionArray = []
                    coordinates = layer.editing.latlngs[0]
                    for (position in coordinates){
                        positionArray.push([coordinates[position].lat, coordinates[position].lng]);
                    }
                    mySavedData.Leitgraeben[highestIdLeitgraeben] = {};
                    mySavedData.Leitgraeben[highestIdLeitgraeben]["position"] = positionArray;
                    mySavedData.Leitgraeben[highestIdLeitgraeben]["depth"] = 1;
                    mySavedData.Leitgraeben[highestIdLeitgraeben]["cost"] = 1;
                    mySavedData.Leitgraeben[highestIdLeitgraeben]["leitgrabenOderBoeschung"] = "leitgraben";
                }

                drawnItems.addLayer(layer);
            });

            mymap.on(L.Draw.Event.EDITED, function (e) {
                var type = e.layerType
                var layers = e.layers._layers;
                var nodeId = "none";
                //iterate over changed layers
                for (var key in layers) {
                    if(layers[key].options.type == "Auffangbecken"){
                        if (layers.hasOwnProperty(key)){
                            auffangbeckenId = layers[key].options.title;
                            coordinates = layers[key].editing.latlngs[0][0]
                            positionArray = []
                            for (position in coordinates){
                                positionArray.push([coordinates[position].lat, coordinates[position].lng]);
                            }
                            mySavedData.Auffangbecken[auffangbeckenId]["position"] = positionArray;
                        }
                    }else if(layers[key].options.type == "Leitgraben"){
                        if (layers.hasOwnProperty(key)){
                            leitgrabenId = layers[key].options.title;
                            coordinates = layers[key].editing.latlngs[0]
                            positionArray = []
                            for (position in coordinates){
                                positionArray.push([coordinates[position].lat, coordinates[position].lng]);
                            }
                            mySavedData.Leitgraeben[leitgrabenId]["position"] = positionArray;
                        }
                    }
                }
            });

            mymap.on(L.Draw.Event.DELETED, function (e) {
                var type = e.layerType
                var layers = e.layers._layers;
                var nodeId = "none";

                for (var key in layers) {
                    if(layers[key].options.type == "Auffangbecken"){
                        if (layers.hasOwnProperty(key)) {
                            auffangbeckenId = layers[key].options.title;
                            delete mySavedData.Auffangbecken[auffangbeckenId];
                        }
                    }else if(layers[key].options.type == "Leitgraben"){
                        if (layers.hasOwnProperty(key)) {
                            leitgrabenId = layers[key].options.title;
                            delete mySavedData.Leitgraeben[leitgrabenId];
                        }
                    }
                }
            });

            for (auffangbecken in mySavedData.Auffangbecken){
                var newPolygon = L.polygon(mySavedData.Auffangbecken[auffangbecken].position, {title: auffangbecken, type: "Auffangbecken"}).setStyle({fillColor: '#00004d', color: '#00004d'}).addTo(currentMap);
                drawnItems.addLayer(newPolygon);
                if (highestIdAuffangbecken < parseInt(auffangbecken)){
                    highestIdAuffangbecken = parseInt(auffangbecken);
                }
                newPolygon.on('click', onPolygonClick);
                function onPolygonClick(event){
                    $("#bottomPropertiesContainer").show()
                    $("#bottomPropertiesContainerPolyline").hide()
                    polygonId = this.options.title;
                    polygonProperties = mySavedData.Auffangbecken[polygonId];
                    document.getElementById("inputCost").value = polygonProperties.cost;
                    document.getElementById("inputDepth").value = polygonProperties.depth;
                }
            }

            for (leitgraben in mySavedData.Leitgraeben){
                var color = colorMapping[mySavedData.Leitgraeben[leitgraben].leitgrabenOderBoeschung]
                var newPolyline = L.polyline(mySavedData.Leitgraeben[leitgraben].position, {title: leitgraben, type: "Leitgraben"}).setStyle({color: color}).addTo(currentMap);
                drawnItems.addLayer(newPolyline);
                if (highestIdLeitgraeben < parseInt(leitgraben)){
                    highestIdLeitgraeben = parseInt(leitgraben);
                }
                newPolyline.on('click', onPolylineClick);
                function onPolylineClick(event){
                    $("#bottomPropertiesContainer").hide()
                    $("#bottomPropertiesContainerPolyline").show()
                    actualPolyline = this;
                    polylineId = this.options.title;
                    polylineProperties = mySavedData.Leitgraeben[polylineId];
                    document.getElementById("selectpickerId").value = polylineProperties.leitgrabenOderBoeschung;
                    if(polylineProperties.leitgrabenOderBoeschung == "leitgraben"){
                        tiefeHoeheText = "Tiefe [m]:"
                    }else{
                        tiefeHoeheText = "Höhe [m]:"
                    }
                    document.getElementById("tiefeHoeheText").innerHTML = tiefeHoeheText;
                    document.getElementById("inputCostPolyline").value = polylineProperties.cost;
                    document.getElementById("inputDepthPolyline").value = polylineProperties.depth;
                }
            }
		});

		event.preventDefault();

	});

});