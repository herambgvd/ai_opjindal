document.addEventListener("DOMContentLoaded", function () {
    // Initialize the map
    const myMap = L.map('map').setView([22.9074872, 79.07306671], 4);
    const tileUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    const attribution = '&copy; <a href="#">GVD</a>';
    const tileLayer = L.tileLayer(tileUrl, {attribution});
    tileLayer.addTo(myMap);

    // Get the GeoJSON data from the window object
    let locationGeoJSON = window.locationGeoJSON;
    let greenMarkerUrl = window.onlineUrl;
    let redMarkerUrl = window.offlineUrl;

    function makePopupContent(location) {
        return `<div>
            <h4>${location.properties.branchName}</h4>
            <p>${location.properties.branchAddress}</p>
            <button class="btn btn-xm btn-outline-info">Dashboard <i class="ri-arrow-right-line"></i> </button>
        </div>`;
    }

    function onEachFeature(feature, layer) {
        layer.bindPopup(makePopupContent(feature), {closeButton: false, offset: L.point(0, -8)});
    }

    function getMarkerIcon(status) {
        return L.icon({
            iconUrl: status ? greenMarkerUrl : redMarkerUrl,
            iconSize: [30, 40]
        });
    }

    // Add GeoJSON layer to the map
    const locationsLayer = L.geoJSON(locationGeoJSON, {
        onEachFeature: onEachFeature,
        pointToLayer: function (feature, latlng) {
            return L.marker(latlng, {icon: getMarkerIcon(feature.properties.status)});
        }
    });
    locationsLayer.addTo(myMap);

    // Fly to location on the map
    function flyToLocation(lat, lng, content) {
        myMap.flyTo([lat, lng], 14, {
            duration: 3
        });
        setTimeout(() => {
            L.popup({closeButton: false, offset: L.point(0, -8)})
                .setLatLng([lat, lng])
                .setContent(content)
                .openOn(myMap);
        }, 3000);
    }

    // Add event listeners to branch cards
    const branchCards = document.querySelectorAll('.branch-card');
    branchCards.forEach(card => {
        card.addEventListener('click', function () {
            // Add the cursor change class
            this.classList.add('card-clicked');
            const lat = this.getAttribute('data-lat');
            const lng = this.getAttribute('data-lng');
            // const url = this.getAttribute('data-url');
            const content = `<div class="text-center">
                <h4>${this.querySelector('h5').innerText}</h4>
                <p>${this.querySelector('p').innerText}</p>
                <a href='#' target="_blank">
                    <button class="btn btn-xm btn-outline-info">Dashboard <i class="ri-arrow-right-line"></i> </button>
                </a>
            </div>`;
            flyToLocation(lat, lng, content);
            // Remove the cursor change class after the fly animation
            setTimeout(() => {
                this.classList.remove('card-clicked');
            }, 3000); // Match this duration with the flyTo duration
        });
    });
});
