"""
build_map.py

Читает data.json (собранный локально через fetch_data.py)
и строит интерактивную карту (folium) → index.html.

Запускается в GitHub Actions — никаких внешних запросов не делает.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import folium


# ---------------------------------------------------------------------------
# Строим карту из data.json
# ---------------------------------------------------------------------------

def build_map(data: dict) -> folium.Map:
    cities = data["cities"]
    updated_at = data.get("updated_at", "")

    m = folium.Map(location=[41.3, 64.5], zoom_start=6, tiles="cartodbpositron")

    counts = [d["vacancies"] for d in cities.values()] or [1]
    max_count = max(counts)
    total = sum(counts)

    for city, d in cities.items():
        count = d["vacancies"]
        share = (count / total * 100) if total else 0
        radius = 8 + 30 * (count / max_count) if max_count else 8

        popup_html = (
            f"<b>{city}</b><br>"
            f"Открытых вакансий: <b>{count:,}</b><br>"
            f"Доля по стране: {share:.1f}%"
        )

        folium.CircleMarker(
            location=[d["lat"], d["lon"]],
            radius=radius,
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=f"{city}: {count:,}",
            color="#1f4e8c",
            weight=1,
            fill=True,
            fill_color="#3186cc",
            fill_opacity=0.65,
        ).add_to(m)

        folium.map.Marker(
            [d["lat"], d["lon"]],
            icon=folium.DivIcon(
                html=(
                    f'<div style="font-size:11px; font-weight:bold; '
                    f'color:#1f4e8c; white-space:nowrap;">{city}</div>'
                )
            ),
        ).add_to(m)

    # Форматируем дату обновления красиво
    try:
        dt = datetime.fromisoformat(updated_at)
        ts = dt.strftime("%d.%m.%Y %H:%M UTC")
    except Exception:
        ts = updated_at or "неизвестно"

    title_html = f"""
    <div style="position: fixed; top: 10px; left: 50px; z-index: 9999;
                background: white; padding: 10px 15px; border-radius: 8px;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3); font-family: sans-serif;
                max-width: 340px;">
        <div style="font-size:15px; font-weight:bold;">
            Спрос на рынке труда: вакансии по городам Узбекистана
        </div>
        <div style="font-size:12px; color:#555; margin-top:4px;">
            Источник: hh.uz · Данные собраны: {ts}
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    return m


# ---------------------------------------------------------------------------
# Главная точка входа
# ---------------------------------------------------------------------------

def main():
    data_path = Path("data.json")

    if not data_path.exists():
        raise FileNotFoundError(
            "data.json не найден. "
            "Запусти fetch_data.py локально и закоммить результат."
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
