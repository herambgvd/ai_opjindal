window.onload = init;

function init() {
    const mapElement = document.getElementById('myMap')
    const myMap = L.map(mapElement, {
        center: [28.4, 77.05],
        zoom: 5,
        layers: [
            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 10,
                attribution: '&copy; <a href="https://www.geniusvision.in">GVD</a>'
            })
        ]
    })
}