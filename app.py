from __future__ import annotations

import json
import random
from pathlib import Path
from uuid import uuid4

import streamlit as st
from PIL import Image, ImageDraw, ImageOps
from streamlit_image_coordinates import streamlit_image_coordinates


APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
HOLDS_PATH = DATA_DIR / "holds.json"
ROUTES_PATH = DATA_DIR / "routes.json"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

HOLD_TYPES = {
    "inicio": {"label": "Inicio", "color": "#2ecc71"},
    "mano": {"label": "Mano", "color": "#3498db"},
    "pie": {"label": "Pie", "color": "#f1c40f"},
    "top": {"label": "Top", "color": "#e74c3c"},
}

ROUTE_ROLE_ORDER = {"inicio": 0, "mano": 1, "pie": 2, "top": 3}

BOARD_STYLES = {
    "equilibrada": {
        "label": "Equilibrada",
        "lateral": 0.12,
        "variance": 0.05,
        "description": "Movimientos limpios, progresivos y faciles de leer.",
    },
    "tension": {
        "label": "Tension",
        "lateral": 0.06,
        "variance": 0.035,
        "description": "Linea mas directa, exige cuerpo apretado y pies precisos.",
    },
    "lateral": {
        "label": "Lateral",
        "lateral": 0.20,
        "variance": 0.07,
        "description": "Cruces y cambios de lado, parecido a bloques de coordinacion controlada.",
    },
    "dinamica": {
        "label": "Dinamica",
        "lateral": 0.26,
        "variance": 0.09,
        "description": "Movimientos mas largos y saltos de mano.",
    },
}

DIFFICULTY_PROFILES = {
    "facil": {
        "label": "Facil",
        "target_moves": 7,
        "max_reach": 0.30,
        "min_gain": 0.06,
    },
    "medio": {
        "label": "Medio",
        "target_moves": 6,
        "max_reach": 0.38,
        "min_gain": 0.08,
    },
    "dificil": {
        "label": "Dificil",
        "target_moves": 5,
        "max_reach": 0.48,
        "min_gain": 0.10,
    },
}

VIEW_WIDTHS = {
    "Celular": 340,
    "Celular grande": 390,
    "Tablet": 650,
    "PC": 950,
}


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        st.warning(f"No pude leer {path.name}. Se usara un JSON vacio.")
        return {}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def list_images() -> list[Path]:
    return sorted(
        path
        for path in APP_DIR.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )


def make_display_image(image: Image.Image, max_width: int) -> tuple[Image.Image, float]:
    scale = min(1.0, max_width / image.width)
    size = (round(image.width * scale), round(image.height * scale))
    return image.resize(size), scale


def load_wall_image(path: Path) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def scaled_point(hold: dict, scale: float) -> tuple[int, int]:
    return round(hold["x"] * scale), round(hold["y"] * scale)


def draw_holds(
    image: Image.Image,
    holds: list[dict],
    scale: float,
    *,
    selected_ids: set[str] | None = None,
    route_ids: list[str] | None = None,
    section_count: int | None = None,
    show_unselected: bool = True,
) -> Image.Image:
    selected_ids = selected_ids or set()
    route_ids = route_ids or []
    route_position = {hold_id: index + 1 for index, hold_id in enumerate(route_ids)}
    hold_by_id = {hold["id"]: hold for hold in holds}
    canvas = image.convert("RGBA")
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    marker_scale = max(0.55, min(1.0, canvas.width / 950))

    if section_count and section_count > 1:
        section_width = canvas.width / section_count
        for section in range(1, section_count):
            x = round(section_width * section)
            draw.line((x, 0, x, canvas.height), fill=(255, 255, 255, 120), width=3)
            draw.line((x, 0, x, canvas.height), fill=(21, 28, 36, 150), width=1)

    if route_ids:
        points = [
            scaled_point(hold_by_id[hold_id], scale)
            for hold_id in route_ids
            if hold_id in hold_by_id and hold_by_id[hold_id].get("type") != "pie"
        ]
        if len(points) > 1:
            draw.line(points, fill=(255, 255, 255, 220), width=6, joint="curve")
            draw.line(points, fill=(21, 28, 36, 240), width=3, joint="curve")

    for index, hold in enumerate(holds, start=1):
        is_selected = hold["id"] in selected_ids
        if selected_ids and not show_unselected and not is_selected:
            continue

        x, y = scaled_point(hold, scale)
        hold_type = hold.get("type", "mano")
        color = HOLD_TYPES.get(hold_type, HOLD_TYPES["mano"])["color"]
        alpha = 42 if is_selected else (26 if not selected_ids else 10)
        radius = round((13 if not is_selected else 20) * marker_scale)
        outline_width = max(1, round((4 if is_selected else 2) * marker_scale))
        rgb = tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
        outline = rgb + (255 if is_selected else 210,)

        if hold_type == "pie":
            points = [
                (x, y - radius - round(4 * marker_scale)),
                (x - radius - round(5 * marker_scale), y + radius),
                (x + radius + round(5 * marker_scale), y + radius),
            ]
            draw.polygon(points, fill=rgb + (alpha,))
            draw.line(points + [points[0]], fill=outline, width=outline_width)
        elif hold_type == "top":
            points = [
                (x, y - radius - round(4 * marker_scale)),
                (x + radius + round(4 * marker_scale), y),
                (x, y + radius + round(4 * marker_scale)),
                (x - radius - round(4 * marker_scale), y),
            ]
            draw.polygon(points, fill=rgb + (alpha,))
            draw.line(points + [points[0]], fill=outline, width=outline_width)
        else:
            draw.ellipse(
                (x - radius, y - radius, x + radius, y + radius),
                fill=rgb + (alpha,),
                outline=outline,
                width=outline_width,
            )
            if hold_type == "inicio" and is_selected:
                draw.ellipse(
                    (
                        x - radius - round(6 * marker_scale),
                        y - radius - round(6 * marker_scale),
                        x + radius + round(6 * marker_scale),
                        y + radius + round(6 * marker_scale),
                    ),
                    outline=(46, 204, 113, 130),
                    width=max(1, round(3 * marker_scale)),
                )

        if is_selected:
            label = {"inicio": "I", "pie": "P", "top": "T"}.get(
                hold_type,
                str(route_position.get(hold["id"], index)),
            )
        else:
            label = str(index)
        bbox = draw.textbbox((0, 0), label)
        text_x = x - (bbox[2] - bbox[0]) / 2
        text_y = y - (bbox[3] - bbox[1]) / 2 - round(1 * marker_scale)
        draw.text(
            (text_x, text_y),
            label,
            fill=(0, 0, 0, 230),
        )

    return Image.alpha_composite(canvas, overlay).convert("RGB")


def nearest_hold(
    holds: list[dict],
    x: float,
    y: float,
    *,
    max_distance: float = 45,
) -> dict | None:
    if not holds:
        return None
    nearest = min(holds, key=lambda hold: (hold["x"] - x) ** 2 + (hold["y"] - y) ** 2)
    distance = ((nearest["x"] - x) ** 2 + (nearest["y"] - y) ** 2) ** 0.5
    return nearest if distance <= max_distance else None


def hold_summary(hold: dict) -> str:
    label = HOLD_TYPES.get(hold.get("type", "mano"), HOLD_TYPES["mano"])["label"]
    return f"{label} | x={round(hold['x'])}, y={round(hold['y'])}"


def route_hold_summary(step: int, hold: dict) -> str:
    label = HOLD_TYPES.get(hold.get("type", "mano"), HOLD_TYPES["mano"])["label"]
    return f"{step}. {label}: x={round(hold['x'])}, y={round(hold['y'])}"


def route_counts(route_ids: list[str], hold_by_id: dict[str, dict]) -> dict[str, int]:
    counts = {key: 0 for key in HOLD_TYPES}
    for hold_id in route_ids:
        hold = hold_by_id.get(hold_id)
        if hold:
            counts[hold.get("type", "mano")] += 1
    return counts


def route_sort_key(hold: dict) -> tuple[int, float]:
    hold_type = hold.get("type", "mano")
    if hold_type == "inicio":
        group = 0
    elif hold_type == "top":
        group = 2
    else:
        group = 1
    return group, -hold["y"]


def normalized_distance(a: dict, b: dict, width: int, height: int) -> float:
    dx = (a["x"] - b["x"]) / width
    dy = (a["y"] - b["y"]) / height
    return (dx * dx + dy * dy) ** 0.5


def section_holds(
    holds: list[dict],
    image_width: int,
    section_index: int,
    section_count: int,
) -> list[dict]:
    left = image_width * section_index / section_count
    right = image_width * (section_index + 1) / section_count
    return [
        hold
        for hold in holds
        if left <= hold["x"] < right
        or (section_index == section_count - 1 and hold["x"] == right)
    ]


def route_quality(route_holds: list[dict], width: int, height: int) -> float:
    if len(route_holds) < 2:
        return 0
    gains = []
    reaches = []
    lateral_changes = 0
    previous_direction = 0

    for prev, current in zip(route_holds, route_holds[1:]):
        gains.append(max(0, (prev["y"] - current["y"]) / height))
        reaches.append(normalized_distance(prev, current, width, height))
        direction = 1 if current["x"] > prev["x"] else -1 if current["x"] < prev["x"] else 0
        if previous_direction and direction and direction != previous_direction:
            lateral_changes += 1
        if direction:
            previous_direction = direction

    steady_gain = 1 - min(1, sum(abs(gain - (sum(gains) / len(gains))) for gain in gains))
    reach_control = 1 - min(1, max(reaches))
    variety = min(1, lateral_changes / max(1, len(route_holds) - 2))
    return round((steady_gain * 0.45 + reach_control * 0.35 + variety * 0.20) * 100, 1)


def choose_by_score(scored: list[tuple[float, dict]], rng: random.Random) -> dict | None:
    if not scored:
        return None
    scored = sorted(scored, key=lambda item: item[0])[:5]
    weights = [1 / (score + 0.05) for score, _ in scored]
    return rng.choices([hold for _, hold in scored], weights=weights, k=1)[0]


def design_board_route(
    holds: list[dict],
    image_size: tuple[int, int],
    *,
    difficulty: str,
    style: str,
    target_moves: int,
    seed: int,
) -> list[dict] | None:
    width, height = image_size
    rng = random.Random(seed)
    profile = DIFFICULTY_PROFILES[difficulty]
    style_profile = BOARD_STYLES[style]

    usable = [hold for hold in holds if hold.get("type") != "pie"]
    if len(usable) < 2:
        return None

    starts = [hold for hold in usable if hold.get("type") == "inicio"]
    if not starts:
        lower_limit = sorted(usable, key=lambda hold: hold["y"], reverse=True)
        starts = lower_limit[: max(1, min(4, len(lower_limit)))]

    tops = [hold for hold in usable if hold.get("type") == "top"]
    if not tops:
        upper_limit = sorted(usable, key=lambda hold: hold["y"])
        tops = upper_limit[: max(1, min(4, len(upper_limit)))]

    start = rng.choice(starts)
    possible_tops = [hold for hold in tops if hold["y"] < start["y"]]
    if not possible_tops:
        return None
    top = rng.choice(possible_tops)

    if start["y"] - top["y"] < height * 0.22:
        return None

    route = [start]
    used = {start["id"], top["id"]}
    interior_slots = max(0, target_moves - 2)
    center_x = (start["x"] + top["x"]) / 2
    direction = rng.choice([-1, 1])

    for step in range(1, interior_slots + 1):
        progress = step / (interior_slots + 1)
        target_y = start["y"] - (start["y"] - top["y"]) * progress
        lateral_wave = direction * ((-1) ** step) * style_profile["lateral"] * width
        target_x = center_x + lateral_wave + rng.uniform(
            -style_profile["variance"] * width,
            style_profile["variance"] * width,
        )

        current = route[-1]
        candidates = []
        for hold in usable:
            if hold["id"] in used:
                continue
            upward_gain = (current["y"] - hold["y"]) / height
            if upward_gain < profile["min_gain"]:
                continue
            if hold["y"] <= top["y"] or hold["y"] >= start["y"]:
                continue
            reach = normalized_distance(current, hold, width, height)
            if reach > profile["max_reach"] + style_profile["lateral"] * 0.35:
                continue
            can_finish = normalized_distance(hold, top, width, height) <= profile["max_reach"] * 1.35
            finish_penalty = 0 if can_finish or step < interior_slots else 2
            score = (
                abs(hold["y"] - target_y) / height * 2.2
                + abs(hold["x"] - target_x) / width * 1.4
                + reach * 0.65
                + finish_penalty
            )
            candidates.append((score, hold))

        next_hold = choose_by_score(candidates, rng)
        if not next_hold:
            break
        route.append(next_hold)
        used.add(next_hold["id"])

    if normalized_distance(route[-1], top, width, height) > profile["max_reach"] * 1.45:
        return None
    route.append(top)

    if len(route) < 3:
        return None
    return route


def add_foot_holds_to_route(
    hand_route: list[dict],
    section_all_holds: list[dict],
    image_size: tuple[int, int],
    *,
    max_feet: int = 4,
) -> list[dict]:
    width, height = image_size
    feet = [hold for hold in section_all_holds if hold.get("type") == "pie"]
    if not feet:
        return hand_route

    selected_feet: list[dict] = []
    used = {hold["id"] for hold in hand_route}
    start_hold = next((hold for hold in hand_route if hold.get("type") == "inicio"), hand_route[0])

    start_foot_candidates = []
    for foot in feet:
        if foot["id"] in used:
            continue
        below_start = foot["y"] > start_hold["y"] + height * 0.03
        if not below_start:
            continue
        dx = abs(foot["x"] - start_hold["x"]) / width
        dy = abs(foot["y"] - start_hold["y"]) / height
        if dx > 0.28 or dy > 0.30:
            continue
        start_foot_candidates.append((dx * 1.5 + dy, foot))

    for _, foot in sorted(start_foot_candidates, key=lambda item: item[0])[:2]:
        selected_feet.append(foot)
        used.add(foot["id"])

    lower_hand_moves = sorted(hand_route[1:-1], key=lambda hold: hold["y"], reverse=True)
    for hand in lower_hand_moves:
        if len(selected_feet) >= max_feet:
            break
        candidates = []
        for foot in feet:
            if foot["id"] in used:
                continue
            below_hand = foot["y"] > hand["y"] + height * 0.03
            if not below_hand:
                continue
            dx = abs(foot["x"] - hand["x"]) / width
            dy = abs(foot["y"] - hand["y"]) / height
            if dx > 0.22 or dy > 0.34:
                continue
            score = dx * 1.4 + dy * 0.8
            candidates.append((score, foot))
        if not candidates:
            continue
        foot = min(candidates, key=lambda item: item[0])[1]
        selected_feet.append(foot)
        used.add(foot["id"])
        if len(selected_feet) >= max_feet:
            break

    if not selected_feet:
        return hand_route

    start = [hold for hold in hand_route if hold.get("type") == "inicio"]
    top = [hold for hold in hand_route if hold.get("type") == "top"]
    middle_hands = [
        hold
        for hold in hand_route
        if hold.get("type") not in {"inicio", "top"}
    ]
    return start + middle_hands + selected_feet + top


def generate_board_style_routes(
    holds_by_image: dict,
    image_paths: list[Path],
    *,
    section_count: int,
    difficulty: str,
    style: str,
    variants_per_section: int,
    target_moves: int | None = None,
) -> tuple[dict, int]:
    generated: dict[str, list[dict]] = {}
    total = 0

    for path in image_paths:
        image = load_wall_image(path)
        image_holds = holds_by_image.get(path.name, [])
        routes: list[dict] = []
        moves = target_moves or DIFFICULTY_PROFILES[difficulty]["target_moves"]

        for section_index in range(section_count):
            holds_in_section = section_holds(
                image_holds,
                image.width,
                section_index,
                section_count,
            )
            if len([hold for hold in holds_in_section if hold.get("type") != "pie"]) < 3:
                continue

            attempts = variants_per_section * 24
            accepted: list[list[dict]] = []
            seen_signatures: set[tuple[str, ...]] = set()

            for attempt in range(attempts):
                route_holds = design_board_route(
                    holds_in_section,
                    image.size,
                    difficulty=difficulty,
                    style=style,
                    target_moves=moves,
                    seed=hash((path.name, section_index, difficulty, style, attempt)),
                )
                if not route_holds:
                    continue
                route_holds = add_foot_holds_to_route(
                    route_holds,
                    holds_in_section,
                    image.size,
                )
                signature = tuple(hold["id"] for hold in route_holds)
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)
                accepted.append(route_holds)
                if len(accepted) >= variants_per_section:
                    break

            for variant_index, route_holds in enumerate(accepted, start=1):
                quality = route_quality(route_holds, image.width, image.height)
                route = {
                    "id": uuid4().hex[:8],
                    "name": (
                        f"Board {DIFFICULTY_PROFILES[difficulty]['label']} "
                        f"S{section_index + 1}.{variant_index}"
                    ),
                    "holds": [hold["id"] for hold in route_holds],
                    "section": section_index + 1,
                    "difficulty": difficulty,
                    "style": style,
                    "quality": quality,
                    "auto": True,
                    "generator": "board-style",
                }
                routes.append(route)

        generated[path.name] = routes
        total += len(routes)

    return generated, total


def generate_section_routes(
    holds_by_image: dict,
    image_paths: list[Path],
    *,
    section_count: int = 4,
    min_holds: int = 2,
) -> tuple[dict, int]:
    generated: dict[str, list[dict]] = {}
    total = 0

    for path in image_paths:
        image = load_wall_image(path)
        image_holds = holds_by_image.get(path.name, [])
        routes: list[dict] = []

        for section_index in range(section_count):
            left = image.width * section_index / section_count
            right = image.width * (section_index + 1) / section_count
            section_holds = [
                hold
                for hold in image_holds
                if left <= hold["x"] < right or (section_index == section_count - 1 and hold["x"] == right)
            ]
            if len(section_holds) < min_holds:
                continue

            ordered_holds = sorted(section_holds, key=route_sort_key)
            route = {
                "id": uuid4().hex[:8],
                "name": f"Auto {path.stem} S{section_index + 1}",
                "holds": [hold["id"] for hold in ordered_holds],
                "section": section_index + 1,
                "auto": True,
            }
            routes.append(route)

        generated[path.name] = routes
        total += len(routes)

    return generated, total


def replace_auto_routes(routes_data: dict, generated_routes: dict) -> dict:
    updated = dict(routes_data)
    for image_name, routes in generated_routes.items():
        existing_routes = [
            route
            for route in updated.get(image_name, [])
            if not route.get("auto")
        ]
        updated[image_name] = existing_routes + routes
    return updated


def usable_holds_count(holds: list[dict]) -> int:
    return len([hold for hold in holds if hold.get("type") != "pie"])


def section_diagnostics(
    holds: list[dict],
    image_width: int,
    section_count: int,
) -> list[str]:
    diagnostics = []
    for section_index in range(section_count):
        holds_in_section = section_holds(holds, image_width, section_index, section_count)
        hands = usable_holds_count(holds_in_section)
        feet = len([hold for hold in holds_in_section if hold.get("type") == "pie"])
        diagnostics.append(f"S{section_index + 1}: {hands} manos/top/inicio, {feet} pies")
    return diagnostics


st.set_page_config(page_title="Muro de escalada", layout="wide")
st.markdown(
    """
    <style>
      .block-container {
        padding-top: 0.75rem;
        padding-left: 0.75rem;
        padding-right: 0.75rem;
      }
      h1 {
        font-size: 1.65rem !important;
        margin-bottom: 0.5rem !important;
      }
      h2, h3 {
        margin-top: 0.4rem !important;
      }
      div[data-testid="stHorizontalBlock"] {
        gap: 0.75rem;
      }
      @media (max-width: 640px) {
        .block-container {
          padding-left: 0.35rem;
          padding-right: 0.35rem;
        }
        h1 {
          font-size: 1.25rem !important;
        }
        button {
          min-height: 2.35rem;
        }
      }
    </style>
    """,
    unsafe_allow_html=True,
)
st.title("Muro de escalada")

images = list_images()
if not images:
    st.error("No encontre imagenes en esta carpeta.")
    st.stop()

holds_data = load_json(HOLDS_PATH)
routes_data = load_json(ROUTES_PATH)

with st.sidebar:
    st.header("Imagen")
    image_path = st.selectbox("Foto del muro", images, format_func=lambda path: path.name)
    mode = st.radio("Modo", ["Marcar presas", "Crear ruta"], horizontal=False)
    view_preset = st.radio(
        "Vista",
        ["Celular", "Celular grande", "Tablet", "PC", "Manual"],
        index=0,
    )
    if view_preset == "Manual":
        max_width = st.slider("Ancho de imagen", 280, 1400, 360, step=10)
    else:
        max_width = VIEW_WIDTHS[view_preset]
        st.caption(f"Ancho de imagen: {max_width}px")
    section_count = st.number_input("Secciones del muro", 1, 8, 4)

image_key = image_path.name
holds_data.setdefault(image_key, [])
routes_data.setdefault(image_key, [])
holds = holds_data[image_key]
routes = routes_data[image_key]

if "active_route_name" not in st.session_state:
    st.session_state.active_route_name = "Proyecto 1"
if "active_route_holds" not in st.session_state:
    st.session_state.active_route_holds = []
if "last_auto_message" not in st.session_state:
    st.session_state.last_auto_message = None
if "image_click_nonce" not in st.session_state:
    st.session_state.image_click_nonce = 0

original_image = load_wall_image(image_path)
display_image, scale = make_display_image(original_image, max_width)

if max_width <= 430:
    right = st.container()
    left = st.container()
else:
    left, right = st.columns([0.72, 0.28], gap="large")

with right:
    if mode == "Marcar presas":
        st.subheader("Nueva presa")
        selected_type = st.radio(
            "Tipo",
            list(HOLD_TYPES.keys()),
            format_func=lambda key: HOLD_TYPES[key]["label"],
            horizontal=True,
        )
        st.caption("Haz clic sobre la imagen para guardar una presa.")

        if st.button("Deshacer ultima presa", disabled=not holds, use_container_width=True):
            holds.pop()
            save_json(HOLDS_PATH, holds_data)
            st.rerun()

        if st.button("Borrar presas de esta imagen", disabled=not holds, use_container_width=True):
            holds_data[image_key] = []
            routes_data[image_key] = []
            save_json(HOLDS_PATH, holds_data)
            save_json(ROUTES_PATH, routes_data)
            st.rerun()

    else:
        st.subheader("Ruta")
        show_unselected_holds = st.toggle(
            "Mostrar presas no usadas",
            value=not st.session_state.active_route_holds,
            help="Dejalo apagado para ver limpia la ruta propuesta. Enciendelo para editar seleccionando otras presas.",
        )
        st.session_state.active_route_name = st.text_input(
            "Nombre",
            value=st.session_state.active_route_name,
        )
        route_options = {route["name"]: route for route in routes}
        chosen_route = st.selectbox(
            "Ruta guardada",
            ["Nueva ruta"] + list(route_options.keys()),
        )
        if chosen_route != "Nueva ruta" and st.button("Cargar ruta", use_container_width=True):
            route = route_options[chosen_route]
            st.session_state.active_route_name = route["name"]
            st.session_state.active_route_holds = list(route.get("holds", []))
            st.rerun()

        st.caption("Para editar a mano, activa 'Mostrar presas no usadas' y haz clic en presas existentes.")
        c1, c2 = st.columns(2)
        if c1.button("Quitar ultima", disabled=not st.session_state.active_route_holds):
            st.session_state.active_route_holds.pop()
            st.rerun()
        if c2.button("Limpiar ruta", disabled=not st.session_state.active_route_holds):
            st.session_state.active_route_holds = []
            st.rerun()

        if st.button(
            "Guardar ruta",
            disabled=not st.session_state.active_route_holds,
            use_container_width=True,
        ):
            new_route = {
                "id": uuid4().hex[:8],
                "name": st.session_state.active_route_name.strip() or "Ruta sin nombre",
                "holds": st.session_state.active_route_holds,
            }
            routes_data[image_key] = [
                route for route in routes if route["name"] != new_route["name"]
            ]
            routes_data[image_key].append(new_route)
            save_json(ROUTES_PATH, routes_data)
            st.success("Ruta guardada.")
            st.rerun()

        if chosen_route != "Nueva ruta" and st.button("Borrar ruta guardada", use_container_width=True):
            routes_data[image_key] = [
                route for route in routes if route["name"] != chosen_route
            ]
            save_json(ROUTES_PATH, routes_data)
            st.rerun()

        st.divider()
        st.subheader("Rutas automaticas")
        st.caption("Genera bloques estilo board: inicio bajo, progresion ascendente, alcance controlado y top alto.")
        if st.session_state.last_auto_message:
            level, message = st.session_state.last_auto_message
            if level == "success":
                st.success(message)
            elif level == "warning":
                st.warning(message)
            else:
                st.info(message)

        current_usable = usable_holds_count(holds)
        all_usable = sum(usable_holds_count(holds_data.get(path.name, [])) for path in images)
        st.write(f"Presas utiles en esta foto: {current_usable}")
        st.caption("Para generar rutas necesitas al menos 3 presas que no sean pie en alguna seccion.")
        with st.expander("Diagnostico por seccion", expanded=current_usable > 0):
            for line in section_diagnostics(holds, original_image.width, int(section_count)):
                st.write(line)

        auto_difficulty = st.selectbox(
            "Dificultad",
            list(DIFFICULTY_PROFILES.keys()),
            format_func=lambda key: DIFFICULTY_PROFILES[key]["label"],
            index=1,
        )
        auto_style = st.selectbox(
            "Estilo",
            list(BOARD_STYLES.keys()),
            format_func=lambda key: BOARD_STYLES[key]["label"],
        )
        st.caption(BOARD_STYLES[auto_style]["description"])
        auto_moves = st.slider(
            "Movimientos de mano",
            3,
            10,
            DIFFICULTY_PROFILES[auto_difficulty]["target_moves"],
        )
        auto_variants = st.slider("Variantes por seccion", 1, 5, 2)
        auto_current = st.button(
            "Generar board para esta foto",
            disabled=current_usable < 3,
            use_container_width=True,
        )
        auto_all = st.button(
            "Generar board para las 4 fotos",
            disabled=all_usable < 3,
            use_container_width=True,
        )

        if auto_current or auto_all:
            target_images = images if auto_all else [image_path]
            generated, total = generate_board_style_routes(
                holds_data,
                target_images,
                section_count=int(section_count),
                difficulty=auto_difficulty,
                style=auto_style,
                variants_per_section=auto_variants,
                target_moves=auto_moves,
            )
            routes_data = replace_auto_routes(routes_data, generated)
            save_json(ROUTES_PATH, routes_data)
            current_generated = generated.get(image_key, [])
            if total:
                st.session_state.last_auto_message = (
                    "success",
                    f"Se generaron {total} rutas estilo board.",
                )
                if current_generated:
                    first_route = current_generated[0]
                    st.session_state.active_route_name = first_route["name"]
                    st.session_state.active_route_holds = list(first_route["holds"])
                    st.success(f"Ruta cargada: {first_route['name']}")
                else:
                    st.success(f"Se generaron {total} rutas en otras fotos.")
            else:
                st.session_state.last_auto_message = (
                    "warning",
                    "Faltan presas marcadas o no hay una secuencia viable en esas secciones.",
                )
                st.warning(st.session_state.last_auto_message[1])

    if mode == "Crear ruta":
        hold_by_id = {hold["id"]: hold for hold in holds}
        if st.session_state.active_route_holds:
            st.subheader("Ruta visible")
            counts = route_counts(st.session_state.active_route_holds, hold_by_id)
            st.write(
                f"Inicio {counts['inicio']} | Manos {counts['mano']} | "
                f"Pies {counts['pie']} | Top {counts['top']}"
            )
            if counts["pie"] == 0:
                st.warning("Esta ruta no tiene pies. Marca algunas presas como pie y vuelve a generar.")
            with st.expander("Secuencia completa", expanded=True):
                for step, hold_id in enumerate(st.session_state.active_route_holds, start=1):
                    hold = hold_by_id.get(hold_id)
                    if hold:
                        st.write(route_hold_summary(step, hold))
        else:
            st.info("Carga o genera una ruta para verla limpia sobre la imagen.")

    with st.expander("Presas marcadas", expanded=(mode == "Marcar presas")):
        if holds:
            for idx, hold in enumerate(holds, start=1):
                st.write(f"{idx}. {hold_summary(hold)}")
        else:
            st.info("Todavia no hay presas marcadas.")

selected_route_ids = (
    st.session_state.active_route_holds if mode == "Crear ruta" else []
)
selected_ids = set(selected_route_ids)
show_unselected_for_image = True
if mode == "Crear ruta":
    show_unselected_for_image = show_unselected_holds
annotated_image = draw_holds(
    display_image,
    holds,
    scale,
    selected_ids=selected_ids,
    route_ids=selected_route_ids,
    section_count=int(section_count) if mode == "Crear ruta" else None,
    show_unselected=show_unselected_for_image,
)

with left:
    st.subheader(image_path.name)
    click = streamlit_image_coordinates(
        annotated_image,
        width=display_image.width,
        key=f"click-{image_key}-{mode}-{st.session_state.image_click_nonce}",
    )

if click:
    original_x = click["x"] / scale
    original_y = click["y"] / scale

    if mode == "Marcar presas":
        holds.append(
            {
                "id": uuid4().hex[:8],
                "type": selected_type,
                "x": round(original_x, 2),
                "y": round(original_y, 2),
            }
        )
        save_json(HOLDS_PATH, holds_data)
        st.session_state.image_click_nonce += 1
        st.rerun()

    else:
        hold = nearest_hold(holds, original_x, original_y)
        if hold:
            route_holds = st.session_state.active_route_holds
            if hold["id"] in route_holds:
                route_holds.remove(hold["id"])
            else:
                route_holds.append(hold["id"])
            st.session_state.image_click_nonce += 1
            st.rerun()
        else:
            st.toast("Haz clic cerca de una presa marcada.")
