$(document).ready(function() {

	$('.formDisplay').on('submit', function(event) {
	    selectedRegion = this.id.replace("buttonDisplay_", "");
		$.ajax({
			data : {
				dataset: this.id
			},
			type : 'POST',
			url : '/modifyGraphDisplay_process'
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

            // remove draw control
            var myDrawControl = $('.leaflet-draw');
            if(myDrawControl.length > 0){
                myDrawControl[0].remove();
            }

            //put in markers
            var useClustering = false;

            blueIcon = new L.Icon({
              iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
              shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
              iconSize: [25, 41],
              iconAnchor: [12, 41],
              popupAnchor: [1, -34],
              shadowSize: [41, 41]
            });

            greyIcon = new L.Icon({
              iconUrl: 'https://cdn.rawgit.com/pointhi/leaflet-color-markers/master/img/marker-icon-grey.png',
              shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/images/marker-shadow.png',
              iconSize: [25, 41],
              iconAnchor: [12, 41],
              popupAnchor: [1, -34],
              shadowSize: [41, 41]
            });


            var markerClusters = L.markerClusterGroup();
            for (building in mySavedData.Buildings){
                if ("addr:street" in mySavedData.Buildings[building].properties){
                    var popup = building.toString() +
                            '<br/>' + mySavedData.Buildings[building].properties["addr:street"] + " " + mySavedData.Buildings[building].properties["addr:housenumber"] +
                            '<br/>' + '<div class="form-check"><input class="form-check-input" type="checkbox" value="" checked="checked" id="defaultCheck1"><label class="form-check-label active" for="defaultCheck1">Node Active</label></div>';
                }else{
                    var popup = building.toString() +
                            '<br/>' + "no adress" +
                            '<br/>' + '<div class="form-check"><input class="form-check-input" type="checkbox" value="" checked="checked" id="defaultCheck1"><label class="form-check-label active" for="defaultCheck1">Node Active</label></div>';
                }

                //code Popup changing the active Status as well
                if (mySavedData.Buildings[building].active.toString() == "1"){
                    var m = L.marker( [mySavedData.Buildings[building]["yCoord"], mySavedData.Buildings[building]["xCoord"]], {title: building.toString(), active: mySavedData.Buildings[building].active.toString(), icon: blueIcon});
                }else{
                    var m = L.marker( [mySavedData.Buildings[building]["yCoord"], mySavedData.Buildings[building]["xCoord"]], {title: building.toString(), active: mySavedData.Buildings[building].active.toString(), icon: greyIcon});
                }
                m.on('click', onMarkerClick);
                function onMarkerClick(event){
                    var popupContent = this.options.title;
                    if ("addr:street" in mySavedData.Buildings[parseInt(this.options.title)].properties){
                        popupContent = popupContent + '<br/>' + mySavedData.Buildings[parseInt(this.options.title)].properties["addr:street"] + " " + mySavedData.Buildings[parseInt(this.options.title)].properties["addr:housenumber"];
                    }else{
                        popupContent = popupContent + '<br/>' + "no adress";
                    }
                    if(mySavedData.Buildings[parseInt(this.options.title)].active == "1"){
                        popupContent = popupContent + '<br/>' + '<div class="form-check"><input class="form-check-input" type="checkbox" value="' + this.options.title + '" onclick="handleClick(this);" checked="checked" id="checkbox' + this.options.title + '"><label class="form-check-label active" for="defaultCheck1">Node Active</label></div>';
                    }else{
                        popupContent = popupContent + '<br/>' + '<div class="form-check"><input class="form-check-input" type="checkbox" value="' + this.options.title + '" onclick="handleClick(this);" id="checkbox' + this.options.title + '"><label class="form-check-label" for="defaultCheck1">Node Active</label></div>';
                    }
                    var popup = L.popup()
                       .setLatLng(event.latlng)
                       .setContent(popupContent)
                       .openOn(currentMap);
                    activeMarker = this;
                }
                activeMarker = m;
                markerClusters.addLayer(m);
                //console.log(building);
            }
            currentMap.addLayer(markerClusters);
            for (auffangbecken in mySavedData.Auffangbecken){
                var newPolygon = L.polygon(mySavedData.Auffangbecken[auffangbecken].position, {title: auffangbecken, type: "Auffangbecken"}).setStyle({fillColor: '#add8e6'}).addTo(currentMap);
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
                var newPolyline = L.polyline(mySavedData.Leitgraeben[leitgraben].position, {title: leitgraben, type: "Leitgraben"}).setStyle({fillColor: '#add8e6'}).addTo(currentMap);
                newPolyline.on('click', onPolylineClick);
                function onPolylineClick(event){
                    $("#bottomPropertiesContainer").hide()
                    $("#bottomPropertiesContainerPolyline").show()
                    polylineId = this.options.title;
                    polylineProperties = mySavedData.Leitgraeben[polylineId];
                    document.getElementById("inputCostPolyline").value = polylineProperties.cost;
                    document.getElementById("inputDepthPolyline").value = polylineProperties.depth;
                }
            }

		});

		event.preventDefault();

	});

});