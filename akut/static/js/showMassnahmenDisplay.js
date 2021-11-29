$(document).ready(function() {

	$('.formDisplay').on('submit', function(event) {
	    selectedRegion = this.id.replace("buttonDisplay_", "");
		$.ajax({
			data : {
				dataset: this.id
			},
			type : 'POST',
			url : '/showMassnahmenDisplay_process'
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

                div.innerHTML += '<div><i style="background:' + '#0cf573' + '"></i> ' + 'Maßnahme wird umgesetzt <br></div>';
                div.innerHTML += '<div><i style="background:' + '#ef4b29' + '"></i> ' + 'Maßnahme wird nicht umgesetzt <br></div>';

                return div;
            };

            legend.addTo(currentMap);

            //var einzugsgebiet = L.polygon(mySavedData.Einzugsgebiete).setStyle({fillColor: '#FF00FF'}).addTo(currentMap);

            for (id in mySavedData.auffangbecken){
                if(mySavedData.auffangbeckenInOptimalSolution[id] == 1){
                    var color = '#0cf573'
                }else{
                    var color = '#ef4b29'
                }
                var newPolygon = L.polygon(mySavedData.auffangbecken[id]["position"], {title: id}).setStyle({fillColor: color, color: color}).addTo(currentMap);
            }

            for (id in mySavedData.leitgraeben){
                if(mySavedData.leitgraebenInOptimalSolution[id] == 1){
                    var color = '#0cf573'
                }else{
                    var color = '#ef4b29'
                }
                var newPolyline = L.polyline(mySavedData.leitgraeben[id]["position"], {title: id}).setStyle({color: color}).addTo(currentMap);
            }
		});

		event.preventDefault();

	});

});