$(document).ready(function() {

	$('.formDisplay').on('submit', function(event) {
	    selectedRegion = this.id.replace("buttonDisplay_", "");
		$.ajax({
			data : {
				dataset: this.id
			},
			type : 'POST',
			url : '/showGridDisplay_process'
		})
		.done(function(data) {
			$("#bottomDisplayContainer").show()
			$("#bottomActionsContainer").show()

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


            legend.onAdd = function (currentMap) {

                var div = L.DomUtil.create('div', 'info legend'),
                    grades = [0, 10, 20, 50, 100, 200, 500, 1000],
                    labels = [];

                div.innerHTML += '<div><i style="background:' + '#bfbfbf' + '"></i> ' + 'nicht relevant für Berechnungen <br></div>';
                div.innerHTML += '<div><i style="background:' + '#9933ff' + '"></i> ' + 'Zu- und Abfluss <br></div>';
                div.innerHTML += '<div><i style="background:' + '#660066' + '"></i> ' + 'potentielle Wasseransammlungen <br></div>';
                div.innerHTML += '<div><i style="background:' + '#ffffcc' + '"></i> ' + 'Gebäude oder Maßnahme <br></div>';

                return div;
            };

            legend.addTo(currentMap);

            /*var baseLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                'attribution':  'Kartendaten &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> Mitwirkende',
                'useCache': true,
                maxNativeZoom: 22,
                maxZoom: 22
            }).addTo(currentMap);*/

            // var einzugsgebiet = L.polygon(mySavedData.Einzugsgebiete).setStyle({fillColor: '#FF00FF', weight: 1}).addTo(currentMap);

            for (grid in mySavedData.Grid){
                if(mySavedData.Relevant[grid] == 0 && mySavedData.connectedToRelevantNode[grid] == 0){
                    var newPolygon = L.polygon(mySavedData.Grid[grid], {relevant: 0, title: grid}).setStyle({fillColor: '#bfbfbf', weight: 1, fillOpacity: 0.65}).addTo(currentMap);
                }else if(mySavedData.Relevant[grid] == 0 && mySavedData.connectedToRelevantNode[grid] == 1){
                    var newPolygon = L.polygon(mySavedData.Grid[grid], {relevant: 0, title: grid}).setStyle({fillColor: '#9933ff', weight: 1, fillOpacity: 0.65}).addTo(currentMap);
                }else if(mySavedData.MitMassnahme[grid] == "yes"){
                    var newPolygon = L.polygon(mySavedData.Grid[grid], {relevant: 1, title: grid}).setStyle({fillColor: '#ffffcc', weight: 1, fillOpacity: 0.65}).addTo(currentMap);
                }else{
                    var newPolygon = L.polygon(mySavedData.Grid[grid], {relevant: 1, title: grid}).setStyle({fillColor: '#660066', weight: 1, fillOpacity: 0.65}).addTo(currentMap);
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

		});

		event.preventDefault();

	});

});