$(document).ready(function() {

	$('.formDisplay').on('submit', function(event) {
	    selectedRegion = this.id.replace("buttonDisplay_", "");
		$.ajax({
			data : {
				dataset: this.id
			},
			type : 'POST',
			url : '/showHandlungsbedarfDisplay_process'
		})
		.done(function(data) {
			$("#bottomDisplayContainer").show()

			mySavedData = data;

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

            var legend = L.control({position: 'bottomright'});

            legend.onAdd = function (currentMap) {

                var div = L.DomUtil.create('div', 'info legend');

                div.innerHTML += 'Handlungsbedarf<br>';
                div.innerHTML += '<div><i style="background:' + colorMapping[0] + '"></i> ' + 'keiner <br></div>';
                div.innerHTML += '<div><i style="background:' + colorMapping[1] + '"></i> ' + 'gering <br></div>';
                div.innerHTML += '<div><i style="background:' + colorMapping[2] + '"></i> ' + 'mäßig <br></div>';
                div.innerHTML += '<div><i style="background:' + colorMapping[3] + '"></i> ' + 'hoch <br></div>';
                div.innerHTML += '<div><i style="background:' + colorMapping[4] + '"></i> ' + 'sehr hoch <br></div>';
                div.innerHTML += 'Wasserstand<br>';
                div.innerHTML += '<div><i style="background:' + '#99ccff' + '"></i> ' + '1-10cm <br></div>';
                div.innerHTML += '<div><i style="background:' + '#4da6ff' + '"></i> ' + '10-30cm <br></div>';
                div.innerHTML += '<div><i style="background:' + '#0059b3' + '"></i> ' + '30-50cm <br></div>';
                div.innerHTML += '<div><i style="background:' + '#003366' + '"></i> ' + '50cm + <br></div>';

                return div;
            };

            legend.addTo(currentMap);

            //var einzugsgebiet = L.polygon(mySavedData.Einzugsgebiete).setStyle({fillColor: '#FF00FF'}).addTo(currentMap);

            for (id in mySavedData.Flooded){
                var drawPolygon = true;
                if(mySavedData.waterHeight[id] <= 0.0001){
                    drawPolygon = false;
                    var color = '#ffffff'
                }else if(mySavedData.waterHeight[id] <= 0.1){
                    var color = '#99ccff'
                }else if(mySavedData.waterHeight[id] <= 0.3){
                    var color = '#4da6ff'
                }else if(mySavedData.waterHeight[id] <= 0.5){
                    var color = '#0059b3'
                }else if(mySavedData.waterHeight[id] > 0.5){
                    var color = '#003366'
                }
                if(drawPolygon){
                    var newPolygon = L.polygon(mySavedData.Grid[id], {schadensklasse: 1, title: id}).setStyle({fillColor: color, weight: 0, fillOpacity: 0.65}).addTo(currentMap);
                    newPolygon.on('click', onPolygonClick);

                    function onPolygonClick(event) {
                        var popupContent = this.options.title + '<br/> geodesicHeight' + mySavedData.GeodesicHeight[parseInt(this.options.title)];
                        var popup = L.popup()
                            .setLatLng(event.latlng)
                            .setContent(popupContent)
                            .openOn(currentMap);
                        activePolygon = this;
                    }
                }
            }

            for (building in mySavedData.Buildings){
                var color = colorMapping[mySavedData.handlungsbedarf[building]];

                if (mySavedData.Buildings[building].active.toString() == "1"){
                    var m = L.polygon( mySavedData.Buildings[building]["position"], {title: building, type: "Building", properties: mySavedData.Buildings[building].properties, active: mySavedData.Buildings[building].active.toString(), fillColor: color, color: color})
                }else{
                    var m = L.polygon( mySavedData.Buildings[building]["position"], {title: building, type: "Building", properties: mySavedData.Buildings[building].properties, active: mySavedData.Buildings[building].active.toString(), fillColor: color, color: color})
                }
                m.addTo(currentMap);
            }

/*
            for (grid in mySavedData.Grid){
                if(mySavedData.Relevant[grid] == 0 && mySavedData.connectedToRelevantNode[grid] == 0){
                    var newPolygon = L.polygon(mySavedData.Grid[grid], {relevant: 0, title: grid}).setStyle({fillColor: '#add8e6'}).addTo(currentMap);
                }else if(mySavedData.Relevant[grid] == 0 && mySavedData.connectedToRelevantNode[grid] == 1){
                    var newPolygon = L.polygon(mySavedData.Grid[grid], {relevant: 0, title: grid}).setStyle({fillColor: '#6A0DAD'}).addTo(currentMap);
                }else if(mySavedData.MitMassnahme[grid] == "yes"){
                    var newPolygon = L.polygon(mySavedData.Grid[grid], {relevant: 1, title: grid}).setStyle({fillColor: '#FFFF00'}).addTo(currentMap);
                }else{
                    var newPolygon = L.polygon(mySavedData.Grid[grid], {relevant: 1, title: grid}).setStyle({fillColor: '#FFA500'}).addTo(currentMap);
                }
                newPolygon.on('click', onPolygonClick);
                function onPolygonClick(event){
                    var popupContent = this.options.title;
                    if(mySavedData.Relevant[parseInt(this.options.title)] == 1){
                        popupContent = popupContent + '<br/>' + '<div class="form-check"><input class="form-check-input" type="checkbox" value="' + this.options.title + '" onclick="handleClick(this);" checked="checked" id="checkbox' + this.options.title + '"><label class="form-check-label active" for="defaultCheck1">Relevant für Berechnung</label></div>';
                    }else{
                        popupContent = popupContent + '<br/>' + '<div class="form-check"><input class="form-check-input" type="checkbox" value="' + this.options.title + '" onclick="handleClick(this);" id="checkbox' + this.options.title + '"><label class="form-check-label" for="defaultCheck1">Relevant für Berechnung</label></div>';
                    }
                    var popup = L.popup()
                       .setLatLng(event.latlng)
                       .setContent(popupContent)
                       .openOn(currentMap);
                    activePolygon = this;
                }
                activePolygon = newPolygon
            }
*/

		});

		event.preventDefault();

	});

});