"""
build_map.py

Читает data.json и строит интерактивную карту рынка труда
Узбекистана → index.html.

Особенности:
- Цветная карта Carto Voyager
- Переключение базовых слоев
- HeatMap вакансий
- Миникарта
- Масштабирование под все города
- Красивые popup и tooltip
"""

import json
from datetime import datetime
from pathlib import Path

import folium
from folium.plugins import HeatMap, MiniMap


# ---------------------------------------------------------------------------
# Строим карту из data.json
# ---------------------------------------------------------------------------

def build_map(data: dict) -> folium.Map:

    cities = data["cities"]
    updated_at = data.get("updated_at", "")

    # -----------------------------------------------------------------------
    # Карта
    # -----------------------------------------------------------------------

    m = folium.Map(
        location=[41.3, 64.5],
        zoom_start=6,
        tiles=None
    )

    # OpenStreetMap
    folium.TileLayer(
        "OpenStreetMap",
        name="Street"
    ).add_to(m)

    # Цветная карта
    folium.TileLayer(
        tiles="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
        attr="CartoDB Voyager",
        name="Color",
        overlay=False,
        control=True
    ).add_to(m)

    # Темная карта
    folium.TileLayer(
        "CartoDB Dark_Matter",
        name="Dark"
    ).add_to(m)

    # Рельеф
    folium.TileLayer(
        tiles="https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
        attr="OpenTopoMap",
        name="Topographic"
    ).add_to(m)

    # -----------------------------------------------------------------------
    # Подсчеты
    # -----------------------------------------------------------------------

    counts = [d["vacancies"] for d in cities.values()] or [1]

    max_count = max(counts)
    total = sum(counts)

    heat_data = []

    bounds = []

    city_layer = folium.FeatureGroup(name="Vacancies")

    # -----------------------------------------------------------------------
    # Города
    # -----------------------------------------------------------------------

    for city, d in cities.items():

        count = d["vacancies"]

        share = (count / total * 100) if total else 0

        radius = 10 + 35 * (count / max_count)

        heat_data.append([
            d["lat"],
            d["lon"],
            count
        ])

        bounds.append([
            d["lat"],
            d["lon"]
        ])

        popup_html = f"""
        <div style="font-family:Arial; min-width:180px;">
            <h4 style="margin-bottom:8px;">{city}</h4>

            <b>Вакансий:</b> {count:,}<br>
            <b>Доля:</b> {share:.1f}%<br>
        </div>
        """

        folium.CircleMarker(
            location=[d["lat"], d["lon"]],
            radius=radius,
            popup=folium.Popup(
                popup_html,
                max_width=250
            ),
            tooltip=f"{city}: {count:,}",
            color="#0b5ed7",
            weight=2,
            fill=True,
            fill_color="#2f80ed",
            fill_opacity=0.75,
        ).add_to(city_layer)

        folium.Marker(
            [d["lat"], d["lon"]],
            icon=folium.DivIcon(
                html=f"""
                <div style="
                    font-size:12px;
                    font-weight:bold;
                    color:#003366;
                    white-space:nowrap;
                    text-shadow:
                        -1px -1px 0 white,
                         1px -1px 0 white,
                        -1px  1px 0 white,
                         1px  1px 0 white;">
                    {city}
                </div>
                """
            )
        ).add_to(city_layer)

    city_layer.add_to(m)

    # -----------------------------------------------------------------------
    # HeatMap
    # -----------------------------------------------------------------------

    HeatMap(
        heat_data,
        name="Heat Map",
        radius=35,
        blur=25,
        min_opacity=0.4
    ).add_to(m)

    # -----------------------------------------------------------------------
    # Миникарта
    # -----------------------------------------------------------------------

    MiniMap(
        toggle_display=True
    ).add_to(m)

    # -----------------------------------------------------------------------
    # Масштабирование
    # -----------------------------------------------------------------------

    if bounds:
        m.fit_bounds(bounds)

    # -----------------------------------------------------------------------
    # Дата обновления
    # -----------------------------------------------------------------------

    try:
        dt = datetime.fromisoformat(updated_at)
        ts = dt.strftime("%d.%m.%Y %H:%M UTC")
    except Exception:
        ts = updated_at or "неизвестно"

    # -----------------------------------------------------------------------
    # Заголовок
    # -----------------------------------------------------------------------

    title_html = f"""
    <div style="
        position: fixed;
        top: 10px;
        left: 50px;
        z-index: 9999;
        background: white;
        padding: 12px 16px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,.25);
        font-family: Arial;
        max-width: 380px;
    ">
        <div style="
            font-size:16px;
            font-weight:bold;
            margin-bottom:4px;
        ">
            🇺🇿 Спрос на рынке труда Узбекистана
        </div>

        <div style="
            font-size:12px;
            color:#555;
        ">
            Источник: hh.uz<br>
            Обновлено: {ts}
        </div>
    </div>
    """

    m.get_root().html.add_child(
        folium.Element(title_html)
    )

    # -----------------------------------------------------------------------
    # Переключатель слоев
    # -----------------------------------------------------------------------

    folium.LayerControl(
        collapsed=False
    ).add_to(m)

    return m


# ---------------------------------------------------------------------------
# Главная точка входа
# ---------------------------------------------------------------------------

def main():

    data_path = Path("data.json")

    if not data_path.exists():
        raise FileNotFoundError(
            "data.json не найден."
        )

    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    print(f"[*] Загружено городов: {len(data['cities'])}")
    print(f"[*] Дата данных: {data.get('updated_at', 'н/д')}")

    m = build_map(data)

    m.save("index.html")

    print("[+] Карта сохранена в index.html")


if __name__ == "__main__":
    main()
