$(document).ready(function() {

	$('.formDisplay').on('submit', function(event) {
	    selectedRegion = this.id.replace("buttonDisplay_", "");
		$.ajax({
			data : {
				dataset: this.id
			},
			type : 'POST',
			url : '/showFliesswegeDisplay_process'
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

            var onmapsWMSLayer = L.tileLayer.wms("https://wms.onmaps.de/", {
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
                div.innerHTML += 'Wasserfluss pro Fläche<br>';
                div.innerHTML += '<div><i style="background:' + '#ff66ff' + '"></i> ' + 'gering (0,1-0,5m³/m²) <br></div>';
                div.innerHTML += '<div><i style="background:' + '#ff00ff' + '"></i> ' + 'mäßig (0,5-1m³/m²) <br></div>';
                div.innerHTML += '<div><i style="background:' + '#cc00cc' + '"></i> ' + 'hoch (1-5m³/m²)<br></div>';
                div.innerHTML += '<div><i style="background:' + '#660066' + '"></i> ' + 'sehr hoch (>5m³/m²)<br></div>';

                return div;
            };

            legend.addTo(currentMap);

            //var einzugsgebiet = L.polygon(mySavedData.Einzugsgebiete).setStyle({fillColor: '#FF00FF'}).addTo(currentMap);

            for (id in mySavedData.flow_through_nodes){
                var drawPolygon = true;
                if(mySavedData.flow_through_nodes[id] <= 0.0001){
                    drawPolygon = false;
                    //var color = '#ffffff'
                }else if(mySavedData.flow_through_nodes[id] <= 0.1){
                    var color = '#ff66ff'
                }else if(mySavedData.flow_through_nodes[id] <= 0.5){
                    var color = '#ff00ff'
                }else if(mySavedData.flow_through_nodes[id] <= 1){
                    var color = '#cc00cc'
                }else if(mySavedData.flow_through_nodes[id] > 5){
                    var color = '#660066'
                }
                if(drawPolygon){
                    var newPolygon = L.polygon(mySavedData.Grid[id], {schadensklasse: 1, title: id}).setStyle({fillColor: color, weight: 0, fillOpacity: 0.65}).addTo(currentMap);
                    newPolygon.on('click', onPolygonClick);

                    function onPolygonClick(event) {
                        var popupContent = this.options.title + '<br/> flow through node: ' + mySavedData.flow_through_nodes[parseInt(this.options.title)];
                        var popup = L.popup()
                            .setLatLng(event.latlng)
                            .setContent(popupContent)
                            .openOn(currentMap);
                        activePolygon = this;
                    }
                }
            }

		});

		event.preventDefault();

	});

});