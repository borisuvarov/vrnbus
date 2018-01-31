(function () {
    "use strict";
    const XHR = ("onload" in new XMLHttpRequest()) ? XMLHttpRequest : XDomainRequest;
    var coords = {latitude: 51.6754966, longitude: 39.2088823}

    var lastbusquery = document.getElementById('lastbusquery')
    var my_map
    var BusIconContentLayout
    var info = document.getElementById('info')
    var businfo = document.getElementById('businfo')

    document.getElementById('lastbus').onclick = function (event) {
        const bus_query = lastbusquery.value
        get_bus_positions(bus_query)
    }

    document.getElementById('lastbus_codd').onclick = function (event) {
        const bus_query = lastbusquery.value
        get_bus_codd_positions(bus_query)
    }

    lastbusquery.onkeyup = function (event) {
        event.preventDefault()
        if (event.keyCode === 13) {
            const bus_query = lastbusquery.value
            get_bus_codd_positions(bus_query)
        }
    }

    if ("geolocation" in navigator) {
        var nextbusgeo = document.getElementById('nextbusgeo')
        nextbusgeo.onclick = function (event) {
            event.preventDefault()
            get_current_pos(info)
        }
        get_current_pos(info)
    }


    function get_current_pos(info) {
        navigator.geolocation.getCurrentPosition(get_bus_arrival)
    }

    function get_bus_arrival(position) {
        var xhr = new XHR()
        coords = position.coords
        var params = 'lat=' + encodeURIComponent(coords.latitude) + '&lon=' + encodeURIComponent(coords.longitude);
        xhr.open('GET', '/arrival?' + params, true);
        xhr.send()
        xhr.onreadystatechange = function () {
            if (this.readyState != 4) return;

            if (this.status != 200) {
                info.innerHTML = 'Ошибка: ' + (this.status ? this.statusText : 'запрос не удался')
                return
            }
            var data = JSON.parse(this.responseText)
            info.innerHTML = data.text
            // lastbusquery.value = data.routes
        }
    }

    function get_bus_positions(query) {
        var xhr = new XHR()

        var params = 'q=' + encodeURIComponent(query)
        xhr.open('GET', '/businfo?' + params, true);
        xhr.send()
        xhr.onreadystatechange = function () {
            if (this.readyState != 4) return;

            if (this.status != 200) {
                info.innerHTML = 'Ошибка: ' + (this.status ? this.statusText : 'запрос не удался')
                return
            }
            var data = JSON.parse(this.responseText)
            const q = data.q
            const text = data.text
            businfo.innerHTML = 'Маршруты: ' + q + '\n' + text
        }
    }

    function get_bus_codd_positions(query) {
        var xhr = new XHR()

        var params = 'q=' + encodeURIComponent(query)
        if (coords) {
            params += '&lat=' + encodeURIComponent(coords.latitude)
            params += '&lon=' + encodeURIComponent(coords.longitude)
        }
        xhr.open('GET', '/coddbus?' + params, true);
        xhr.send()
        xhr.onreadystatechange = function () {
            if (this.readyState != 4) return;

            if (this.status != 200) {
                info.innerHTML = 'Ошибка: ' + (this.status ? this.statusText : 'запрос не удался')
                return
            }
            var data = JSON.parse(this.responseText)
            update_map(data.result)
        }
    }

    function update_map(buses) {
        my_map.geoObjects.removeAll()
        buses.forEach(function (bus) {
            const hint = bus.last_time_ + '; ' + bus.azimuth
            const desc = bus.last_time_ + JSON.stringify(bus)
            my_map.geoObjects.add(new BusMark(bus.last_lat_, bus.last_lon_, bus.azimuth, bus.route_name_.trim(), hint, desc))
        })
    }


    var BusMark = function (lat, lon, rotation, caption, hint, description) {
        this.placemark = new ymaps.Placemark([lat, lon], {
            hintContent: hint,
            balloonContent: description,
            iconContent: caption,
            rotation: rotation,
        }, {
            // Опции.
            // Необходимо указать данный тип макета.
            iconLayout: 'default#imageWithContent',
            // Своё изображение иконки метки.
            iconImageHref: 'bus_round.png',
            // Размеры метки.
            iconImageSize: [32, 32],
            // Смещение левого верхнего угла иконки относительно
            // её "ножки" (точки привязки).
            iconImageOffset: [-16, -16],
            // Смещение слоя с содержимым относительно слоя с картинкой.
            iconContentOffset: [0, 0],
            // Макет содержимого.
            iconContentLayout: BusIconContentLayout
        });

        return this.placemark
    }


    ymaps.ready(ymap_show);

    function ymap_show() {
        my_map = new ymaps.Map('map', {
            center: [coords.latitude, coords.longitude],
            zoom: 14
        }, {
            searchControlProvider: 'yandex#search'
        })

        BusIconContentLayout = ymaps.templateLayoutFactory.createClass(
            '<img class="bus-icon" style=" z-index: -1; transform: rotate({{properties.rotation}}deg); "src="arrow.png">' +
            '<ymaps class="bus-title" style="z-index: -2; color: orange; font-weight: bold;"> $[properties.iconContent] </ymaps>'
        )

        if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
            test_mark()
        }
    }

    function test_mark() {
        var bus_obj = {
            "obj_id_": 0,
            "proj_id_": 0,
            "last_speed_": 0,
            "last_lon_": 39.262801,
            "last_lat_": 51.683984,
            "lon2": 0,
            "lat2": 0,
            "azimuth": 0,
            "dist": 0,
            "last_time_": "Jan 31, 2018 11:42:48 AM",
            "route_name_": "18 ",
            "type_proj": 0,
            "lowfloor": 0
        }

        my_map.setCenter([bus_obj.last_lat_, bus_obj.last_lon_])
        my_map.geoObjects.removeAll()

        var bus_marker = new BusMark(bus_obj.last_lat_, bus_obj.last_lon_, 0, "text", "hhhhh", 'bbbbb')

        var marker = new ymaps.Placemark([bus_obj.last_lat_, bus_obj.last_lon_], {
            rotation: 0
        }, {});
        my_map.geoObjects.add(marker);
        my_map.geoObjects.add(bus_marker);
        var i = 0
        // начать повторы с интервалом 2 сек
        var timerId = setInterval(function () {
            var rotation = (5 * (i++))
            bus_marker.properties.set('rotation', rotation);
            bus_marker.properties.set('iconContent', rotation);
            // bus_marker.balloon.open();
        }, 100);

        setTimeout(function () {
            clearInterval(timerId);
        }, 50000);

    }
})()