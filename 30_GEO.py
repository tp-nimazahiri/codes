import attribute_controller as ac
import element_controller as ec
import geometry_controller as gc
import cadwork as cw
import file_controller as fc
import material_controller as mc
import utility_controller as uc
import visualization_controller as vc
from cadwork import element_module_properties
from cadwork import element_type
import connector_axis_controller as cac
import machine_controller as mac
import menu_controller as mec
import bim_controller as bc
import math
from math import sqrt
from collections import defaultdict
import re
import sys
import os
import openpyxl
#sys.path.append('T:\\01-Engineering\\privat\\60_Food_For_Plugins\\site-packages_V2')
# ----------------------------------------------------------------------------------------------------------------------
components_visible = ec.get_visible_identifiable_element_ids()
components = ec.get_active_identifiable_element_ids()

walls = []
parts = []
openings = []
floors = []
roofs = []
installations = []

for component in components:

    if ac.is_wall(component) or ac.is_framed_wall(component) or ac.is_solid_wall(component):
        walls.append(component)

    elif ac.is_roof(component) or ac.is_framed_roof(component) or ac.is_solid_roof(component):
        roofs.append(component)

    elif ac.is_floor(component) or ac.is_framed_floor(component) or ac.is_solid_floor(component):
        floors.append(component)

    elif ac.is_opening(component):
        openings.append(component)

    elif ac.is_circular_mep(component) or ac.is_rectangular_mep(component):
        installations.append(component)

    else:
        parts.append(component)

blocks = walls + floors + roofs
elements = walls + floors + roofs + openings
parts = parts + installations

project_number = uc.get_project_number()

# ----------------------------------------------------------------------------------------------------------------------
menu_options = ('Elementrichtung Angleichen (ELM)',
                'Bearbeitung Löschen (WND)',
                'Öffnung Anpassen (ÖFF)',
                'Beplankung Bundseite (EZT)',
                'Schwerpunkt der Module (KOM)',
                'Ausgabe Einstellungen (EZT)',
                'Platte / Stab',
                'Installation-Rund (EZT)',
                'Installation-Fer-schicht (EZT)',
                'Wandschweissen (WND-ÖFF)',
                'Katalogerstellung',
                '',
                'Zurück')


while True:
    menu = mec.display_simple_menu(menu_options)

    if menu == 'Elementrichtung Angleichen (ELM)':

        for element in elements:

            p1 = gc.get_p1(element)
            p2 = gc.get_p2(element)

            p1_x_value = p1.x
            p1_y_value = p1.y
            p2_x_value = p2.x
            p2_y_value = p2.y

            diff_x_value = p1_x_value - p2_x_value
            diff_y_value = p1_y_value - p2_y_value

            if abs(diff_x_value) > abs(diff_y_value):
                if diff_x_value > 0:
                    gc.rotate_length_axis_180([element])
            else:
                if diff_y_value > 0:
                    gc.rotate_length_axis_180([element])


    elif menu == 'Bearbeitung Löschen (WND)':
        for wall in walls:
            cuts = ec.delete_processes_keep_cutting_bodies([wall], False)
            ec.delete_elements(cuts)


    elif menu == 'Öffnung Anpassen (ÖFF)':
        # Opening Adjustments: _________________________________________________________________________________________
        for opening in openings:
            cog = gc.get_center_of_gravity(opening)

            for element in elements:
                if ac.is_framed_wall(element) or ac.is_solid_wall(element):

                    bounding_box_ver = gc.get_element_vertices(element)
                    min_ver, max_ver = list(map(min, zip(*bounding_box_ver))), list(map(max, zip(*bounding_box_ver)))

                    if all(min_ver[i] <= cog[i] <= max_ver[i] for i in range(3)):
                        element_group_value = ac.get_group(element)
                        element_subgroup_value = ac.get_subgroup(element)

                        ac.set_group([opening], element_group_value)
                        ac.set_subgroup([opening], element_subgroup_value)

        # Opening Names: _______________________________________________________________________________________________
        for opening in openings:

            for part in parts:

                part_name = ac.get_name(part)

                if 'eze' in part_name:
                    if ":" in part_name:
                        part_real_name = part_name.split(":")[1]
                    else:
                        part_real_name = part_name

                    cog_part = gc.get_center_of_gravity(part)
                    cog_opening = gc.get_center_of_gravity(opening)

                    distance = math.sqrt(sum((cog_opening[i] - cog_part[i]) ** 2 for i in range(3)))
                    if distance < 400:
                        article_nr = ac.get_user_attribute(part, 7)
                        ac.set_name([opening], part_real_name)
                        ac.set_comment([opening], article_nr)


    elif menu == 'Beplankung Bundseite (EZT)':

        for block in blocks:
            block_subgroup = ac.get_subgroup(block)
            cog_block = gc.get_center_of_gravity(block)

            for part in parts:
                part_subgroup = ac.get_subgroup(part)
                name = ac.get_name(part)

                if block_subgroup == part_subgroup and "beplankung" in name.lower():

                    gc.auto_regenerate_axes([part])
                    ver_face = gc.get_element_reference_face_vertices(part)
                    ver_part = gc.get_element_vertices(part)
                    avr_ver_face = [sum(coord) / len(coord) for coord in zip(*ver_face)]
                    avr_ver_part = [sum(coord) / len(coord) for coord in zip(*ver_part)]

                    dis_face = math.sqrt(sum((cog_block[i] - avr_ver_face[i]) ** 2 for i in range(3)))
                    dis_part = math.sqrt(sum((cog_block[i] - avr_ver_part[i]) ** 2 for i in range(3)))

                    if dis_face < dis_part:
                        print("true")

                        gc.rotate_height_axis_180([part])


    elif menu == 'Schwerpunkt der Module (KOM)':

        grouped_components = defaultdict(list)

        for component in components:
            group_value = ac.get_group(component)
            if group_value is not None:
                grouped_components[group_value].append(component)

        for group_value, components in grouped_components.items():
            cog = gc.get_center_of_gravity_for_list_considering_materials(components)
            point = cw.point_3d(cog[0], cog[1], cog[2])
            node = ec.create_node(point)

            vc.set_color([node], 39)
            ac.set_group([node], group_value)
            ac.set_name([node], "Schwerpunkt")


    elif menu == 'Ausgabe Einstellungen (EZT)':

        def parse_ua13_layer(layer_value):
            if layer_value is None:
                return None

            layer_text = str(layer_value).strip().upper()

            if layer_text == "TW":
                return 0

            match_g = re.fullmatch(r"G(\d+)", layer_text)
            if match_g:
                return int(match_g.group(1))

            match_b = re.fullmatch(r"B(\d+)", layer_text)
            if match_b:
                return -int(match_b.group(1))

            return None

        def set_layer_without_output(component_id, layer_number):
            ls = cw.layer_settings()
            ls.set_layer(layer_number)
            ls.set_without_output()
            ac.set_layer_settings([component_id], ls)

        def set_layer_without_dimensions(component_id, layer_number):
            ls = cw.layer_settings()
            ls.set_layer(layer_number)
            ls.set_without_dimensions_output()
            ac.set_layer_settings([component_id], ls)

        def set_layer_with_dimensions_and_attributes(component_id, layer_number):
            ls = cw.layer_settings()
            ls.set_layer(layer_number)
            ls.set_with_dimensions_output()
            ls.set_with_attributes_output()
            ac.set_layer_settings([component_id], ls)

        components_by_module = defaultdict(list)
        for component in components:
            key = (ac.get_group(component), ac.get_subgroup(component))
            components_by_module[key].append(component)

        for _, module_components in components_by_module.items():
            max_g = 0
            max_b = 0

            for component in module_components:
                layer_value = ac.get_user_attribute(component, 13)
                layer_text = "" if layer_value is None else str(layer_value).strip().upper()

                match_g = re.fullmatch(r"G(\d+)", layer_text)
                if match_g:
                    max_g = max(max_g, int(match_g.group(1)))
                    continue

                match_b = re.fullmatch(r"B(\d+)", layer_text)
                if match_b:
                    max_b = max(max_b, int(match_b.group(1)))

            outer_layers = ([-i for i in range(1, max_b + 1)] +
                            [i for i in range(1, max_g + 1)])
            relevant_layers = [0] + outer_layers

            for component in module_components:
                current_layer = parse_ua13_layer(ac.get_user_attribute(component, 13))

                if current_layer is None:
                    continue

                if current_layer == 0:
                    # TW active: all non-TW layers are shown without dimensions.
                    for layer in outer_layers:
                        set_layer_without_dimensions(component, layer)
                    set_layer_with_dimensions_and_attributes(component, current_layer)
                else:
                    for layer in relevant_layers:
                        set_layer_without_output(component, layer)

                    set_layer_with_dimensions_and_attributes(component, current_layer)

                    # Only layers farther away from TW on the same side are shown without dimensions.
                    for layer in outer_layers:
                        if layer == current_layer:
                            continue

                        same_side = (layer > 0 and current_layer > 0) or (layer < 0 and current_layer < 0)
                        farther_from_tw = abs(layer) > abs(current_layer)

                        if same_side and farther_from_tw:
                            set_layer_without_dimensions(component, layer)


    elif menu == 'Platte / Stab':

        for p in parts:
            if (ac.get_user_attribute(p, 10) == "KBZ" or ac.get_user_attribute(p, 10) == "HHH") and (ac.is_panel(p)):
                ec.convert_panel_to_beam([p])
            if ac.get_user_attribute(p, 10) == "BAZ" and (ac.is_beam(p)):
                ec.convert_beam_to_panel([p])

        vc.refresh()


    elif menu == 'Duplikationskontrolle (KOM)':
        duplications = vc.set_active(ec.check_element_duplicates(components_visible))


    elif menu == 'Kollisionskontrolle (KOM)':

        for i in range(len(elements)):
            for j in range(i + 1, len(elements)):
                if ec.check_if_elements_are_in_collision(elements[i], elements[j]):
                    vc.set_active([elements[i]])

        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                if ec.check_if_elements_are_in_collision(parts[i], parts[j]):
                    vc.set_active([parts[i]])


    elif menu == 'Installation-Rund (EZT)':

        for part in parts:

            beschreibung = ac.get_user_attribute(part, 9)

            if "Leerrohr" in beschreibung:

                group = ac.get_group(part)
                subgroup = ac.get_subgroup(part)
                building = bc.get_building(part)
                storey = bc.get_storey(part)
                manufacturer = ac.get_user_attribute(part, 8)

                gc.auto_regenerate_axes([part])
                height = gc.get_height(part)

                p1 = gc.get_p1(part)
                p2 = gc.get_p2(part)
                points = [p1, p2]

                circular_mep = ec.create_circular_mep(height, points)
                ac.set_user_attribute([circular_mep], 9, beschreibung)
                ac.set_group([circular_mep], group)
                ac.set_subgroup([circular_mep], subgroup)
                bc.set_building_and_storey([circular_mep], building, storey)
                #ac.set_user_attribute([circular_mep], 8, manufacturer)

                ac.set_user_attribute([circular_mep], 13, "TW")
                vc.set_color([circular_mep], 5)
                ls = cw.layer_settings()
                ls.set_layer(0)
                ls.set_with_dimensions_output()  # mit Bemaßung
                ls.set_with_attributes_output()  # mit Beschriftung
                ac.set_layer_settings([circular_mep], ls)

                for layer in [1, -1]:
                    ls = cw.layer_settings()
                    ls.set_layer(layer)
                    ls.set_without_output()
                    ls.set_without_dimensions_output()  # ohne Bemaßung
                    ac.set_layer_settings([circular_mep], ls)

                ec.delete_elements([part])


    elif menu == 'Installation-Fer-schicht (EZT)':

        for installation in installations:

            cog = gc.get_center_of_gravity(installation)

            for part in parts:

                bounding_box_ver = gc.get_element_vertices(part)
                min_ver, max_ver = list(map(min, zip(*bounding_box_ver))), list(map(max, zip(*bounding_box_ver)))

                if all(min_ver[i] <= cog[i] <= max_ver[i] for i in range(3)):
                    part_construction_layer = ac.get_user_attribute(part, 13)

                    ac.set_user_attribute([installation], 13, part_construction_layer)

    elif menu == 'Wandschweissen (WND-ÖFF)':
        def distance(p1, p2):
            return sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2 + (p1.z - p2.z) ** 2)


        wall_groups = defaultdict(list)
        added_walls = set()

        for i in range(len(walls)):
            wall1_center = gc.get_center_of_gravity(walls[i])
            wall1_center_tuple = (wall1_center.x, wall1_center.y, wall1_center.z)

            if walls[i] not in added_walls:
                added_walls.add(walls[i])
                wall_groups[wall1_center_tuple].append(walls[i])

            for j in range(i + 1, len(walls)):
                wall2_center = gc.get_center_of_gravity(walls[j])

                if ac.get_group(walls[i]) == ac.get_group(walls[j]) and distance(wall1_center, wall2_center) < 500 and \
                        walls[j] not in added_walls:
                    added_walls.add(walls[j])
                    wall_groups[wall1_center_tuple].append(walls[j])

        for wall_group_key in wall_groups.keys():
            wall_group = wall_groups[wall_group_key]
            wm_walls = [wall for wall in wall_group if ac.get_name(wall)[2:4] == "WM"]
            wd_walls = [wall for wall in wall_group if ac.get_name(wall)[2:4] == "WD"]
            wf_walls = [wall for wall in wall_group if ac.get_name(wall)[2:4] == "WF"]
            other_walls = [wall for wall in wall_group if not (ac.get_name(wall)[2:4] in {"WM", "WD", "WF"})]
            sorted_wall_group = wm_walls + wd_walls + wf_walls + other_walls

            if len(sorted_wall_group) > 1:

                wm_names = "".join([ac.get_name(w)[4:] for w in wm_walls])
                wd_names = "".join([ac.get_name(w)[4:] for w in wd_walls])
                wf_names = "".join([ac.get_name(w)[4:] for w in wf_walls])

                underline_index = wm_names.rfind('_')
                if underline_index != -1 and underline_index > 0:
                    letter = wm_names[underline_index - 1]

                else:
                    letter = 'h'

                wm_thickness, wm_parentheses = "", ""
                wd_thickness, wd_parentheses = "", ""
                wf_thickness, wf_parentheses = "", ""

                if wm_walls:
                    wm_thickness = str(round(gc.get_height(wm_walls[0])))
                    wm_parentheses = re.findall(r'\(.*?\)', wm_names)[0] if re.findall(r'\(.*?\)', wm_names) else ""
                if wd_walls:
                    wd_thickness = str(round(gc.get_height(wd_walls[0])))
                    wd_parentheses = re.findall(r'\(.*?\)', wd_names)[0] if re.findall(r'\(.*?\)', wd_names) else ""
                if wf_walls:
                    wf_thickness = str(round(gc.get_height(wf_walls[0])))
                    wf_parentheses = re.findall(r'\(.*?\)', wf_names)[0] if re.findall(r'\(.*?\)', wf_names) else ""

                soldered_element = ec.solder_elements(sorted_wall_group)
                width = str(round(gc.get_height(soldered_element[0])))

                wall_group_name = "tpWA" + width + letter + "_" + wf_thickness + "_" + wd_thickness + wd_parentheses + "_" + wm_thickness + wd_parentheses
                ac.set_name(soldered_element, wall_group_name)

                cuts = ec.delete_processes_keep_cutting_bodies(sorted_wall_group, False)
                ec.delete_elements(cuts)

        walls_with_openings = defaultdict(list)
        for opening in openings:
            cog = gc.get_center_of_gravity(opening)
            for wall in walls:
                bounding_box_ver = gc.get_element_vertices(wall)
                min_ver, max_ver = list(map(min, zip(*bounding_box_ver))), list(map(max, zip(*bounding_box_ver)))
                if all(min_ver[i] <= cog[i] <= max_ver[i] for i in range(3)):
                    walls_with_openings[wall].append(opening)

        for wall, openings in walls_with_openings.items():
            if len(openings) > 1:
                wall_subgroup = ac.get_subgroup(wall)
                soldered_opening = ec.solder_elements(openings)
                ac.set_subgroup(soldered_opening, wall_subgroup)

    elif menu == 'Katalogerstellung':

        APPLUS_XLSX_PATH = r"T:\11-timpla-Datenaustausch\APplus_Artikelstamm.xlsx"

        EXPORT_DIR = os.path.join(
            os.environ.get("USERPROFILE", os.path.expanduser("~")),
            "Timpla GmbH",
            "Engineering - departmentHUB - Dokumente",
            "02_Software - Prozess PLA",
            "25_Cadwork",
            "01_Stammdaten",
            "cadwork.cat",
            "catalog_3d",
            "tp_Standardbauteile",
        )

        def _s(v) -> str:
            if v is None:
                return ""
            return str(v).strip()

        def _to_float(v):
            text = _s(v)
            if not text:
                return None
            text = text.replace(" ", "").replace(",", ".")
            try:
                return float(text)
            except Exception:
                return None

        def _to_int(v):
            n = _to_float(v)
            if n is None:
                return None
            try:
                return int(round(n))
            except Exception:
                return None

        def _sanitize_filename(name: str) -> str:
            clean = re.sub(r'[<>:"/\\|?*]', "_", _s(name))
            clean = clean.strip(" .")
            return clean or "unnamed"

        def _beam_length_mm_from_f(col_f: str):
            text = _s(col_f).lower().replace(" ", "")
            if not text.endswith("m"):
                return None
            meters = _to_float(text[:-1])
            if meters is None:
                return None
            return meters * 1000.0

        def _panel_w_l_mm_from_f(col_f: str):
            text = _s(col_f).lower().replace(" ", "").replace("x", "x")
            if "x" not in text:
                return None, None
            parts_f = text.split("x")
            if len(parts_f) != 2:
                return None, None
            width = _to_float(parts_f[0])
            length = _to_float(parts_f[1])
            if width is None or length is None:
                return None, None
            return width, length

        def _classify_row(d_val, e_val, f_val):
            d_mm = _to_float(d_val)
            e_mm = _to_float(e_val)
            f_text = _s(f_val)
            if d_mm is None:
                return ""

            if e_mm is not None and _beam_length_mm_from_f(f_text) is not None:
                return "beam"

            if _s(e_val) == "" and _panel_w_l_mm_from_f(f_text)[0] is not None:
                return "panel"

            return ""

        def _ensure_material(material_name: str):
            name = _s(material_name)
            if not name:
                return None
            try:
                mid = mc.get_material_id(name)
                if mid:
                    return mid
            except Exception:
                pass
            try:
                return mc.create_material(name)
            except Exception:
                return None

        def _apply_common_attributes(eid: int, a: str, name_b: str, f: str, h: str, i, j: str, k: str, l: str, m: str, o: str, t: str):
            ac.set_name([eid], _s(name_b))
            ac.set_user_attribute([eid], 7, _s(a))
            ac.set_user_attribute([eid], 31, _s(f))
            ac.set_user_attribute([eid], 1, _s(j))
            ac.set_user_attribute([eid], 6, _s(k))
            ac.set_user_attribute([eid], 14, _s(l))
            ac.set_user_attribute([eid], 8, _s(m))
            ac.set_user_attribute([eid], 9, _s(o))
            ac.set_user_attribute([eid], 20, _s(t))

            mat_id = _ensure_material(h)
            if mat_id is not None:
                try:
                    ac.set_element_material([eid], mat_id)
                except Exception:
                    pass

            color_id = _to_int(i)
            if color_id is not None:
                try:
                    vc.set_color([eid], color_id)
                except Exception:
                    pass

        def _create_beam(d_mm, e_mm, f_text):
            length_mm = _beam_length_mm_from_f(f_text)
            if length_mm is None:
                return None

            start = cw.point_3d(0.0, 0.0, 0.0)
            x_dir = cw.point_3d(1.0, 0.0, 0.0)
            z_dir = cw.point_3d(0.0, 0.0, 1.0)

            return ec.create_rectangular_beam_vectors(float(e_mm), float(d_mm), float(length_mm), start, x_dir, z_dir)

        def _create_panel(d_mm, f_text):
            width_mm, length_mm = _panel_w_l_mm_from_f(f_text)
            if width_mm is None or length_mm is None:
                return None

            start = cw.point_3d(0.0, 0.0, 0.0)
            x_dir = cw.point_3d(1.0, 0.0, 0.0)
            z_dir = cw.point_3d(0.0, 0.0, 1.0)

            return ec.create_rectangular_panel_vectors(float(width_mm), float(d_mm), float(length_mm), start, x_dir, z_dir)

        def _read_rows_from_applus(path: str):
            if not os.path.exists(path):
                raise FileNotFoundError(f"APplus file not found: {path}")

            wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
            try:
                ws = wb.active
                for ridx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                    a = _s(row[0] if len(row) > 0 else "")
                    b = _s(row[1] if len(row) > 1 else "")
                    d = row[3] if len(row) > 3 else None
                    e = row[4] if len(row) > 4 else None
                    f = row[5] if len(row) > 5 else None
                    h = _s(row[7] if len(row) > 7 else "")
                    i = row[8] if len(row) > 8 else None
                    j = _s(row[9] if len(row) > 9 else "")
                    k = _s(row[10] if len(row) > 10 else "")
                    l = _s(row[11] if len(row) > 11 else "")
                    m = _s(row[12] if len(row) > 12 else "")
                    o = _s(row[14] if len(row) > 14 else "")
                    t = _s(row[19] if len(row) > 19 else "")

                    yield {
                        "row_index": ridx,
                        "A": a,
                        "B": b,
                        "D": d,
                        "E": e,
                        "F": f,
                        "H": h,
                        "I": i,
                        "J": j,
                        "K": k,
                        "L": l,
                        "M": m,
                        "O": o,
                        "T": t,
                    }
            finally:
                wb.close()

        def _export_element_3dc(eid: int, name_a: str, target_dir: str):
            os.makedirs(target_dir, exist_ok=True)
            base = _sanitize_filename(name_a)
            path = os.path.join(target_dir, f"{base}.3dc")
            fc.export_3dc_file([eid], path)
            return path

        created = 0
        created_beams = 0
        created_panels = 0
        skipped = 0
        failures = []
        saved_paths = []

        for rec in _read_rows_from_applus(APPLUS_XLSX_PATH):
            row_no = rec["row_index"]
            a = rec["A"]
            b = rec["B"]
            d = rec["D"]
            e = rec["E"]
            f = rec["F"]
            h = rec["H"]
            i = rec["I"]
            j = rec["J"]
            k = rec["K"]
            l = rec["L"]
            m = rec["M"]
            o = rec["O"]
            t = rec["T"]

            if not t:
                skipped += 1
                continue

            kind = _classify_row(d, e, f)
            if not kind:
                skipped += 1
                continue

            d_mm = _to_float(d)
            e_mm = _to_float(e)
            try:
                if kind == "beam":
                    eid = _create_beam(d_mm, e_mm, _s(f))
                else:
                    eid = _create_panel(d_mm, _s(f))

                if eid is None:
                    skipped += 1
                    continue

                _apply_common_attributes(eid, a, b, _s(f), h, i, j, k, l, m, o, t)
                saved_paths.append(_export_element_3dc(eid, b, EXPORT_DIR))
                try:
                    ec.delete_elements([eid])
                except Exception:
                    pass
                if kind == "beam":
                    created_beams += 1
                else:
                    created_panels += 1
                created += 1
            except Exception as ex:
                failures.append(f"Row {row_no} ({a}): {ex}")

        lines = [
            f"APplus source: {APPLUS_XLSX_PATH}",
            f"Export dir: {EXPORT_DIR}",
            f"Created: {created} (beams: {created_beams}, panels: {created_panels})",
            f"Skipped: {skipped}",
            f"Failures: {len(failures)}",
        ]
        if failures:
            lines.append("")
            lines.append("First failures:")
            lines.extend(failures[:20])

        uc.print_info("\n".join(lines))

    elif menu in ('Zurück', None, ''):
        break










