"""Clean Buddy SVG: keep original structure, simplify paths, unify colors, remove noise."""
import xml.etree.ElementTree as ET
import re
import math
from collections import defaultdict

def parse_path_to_absolute(d, tx, ty):
    tokens = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', d)
    abs_commands = []
    cx, cy = tx, ty
    start_x, start_y = cx, cy
    prev_cpx, prev_cpy = cx, cy
    i = 0
    
    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        if cmd in 'Zz':
            cx, cy = start_x, start_y
            abs_commands.append(('Z', []))
            continue
        
        params = []
        while i < len(tokens) and re.match(r'^[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?$', tokens[i]):
            params.append(float(tokens[i]))
            i += 1
        
        rel = cmd.islower()
        cmd_u = cmd.upper()
        new_params = []
        
        if cmd_u == 'M':
            for j in range(0, len(params), 2):
                x, y = params[j], params[j+1]
                if rel: x += cx; y += cy
                new_params.extend([x, y])
                cx, cy = x, y
                start_x, start_y = x, y
        elif cmd_u == 'L':
            for j in range(0, len(params), 2):
                x, y = params[j], params[j+1]
                if rel: x += cx; y += cy
                new_params.extend([x, y])
                cx, cy = x, y
        elif cmd_u == 'H':
            for p in params:
                x = p + (cx if rel else 0)
                new_params.append(x)
                cx = x
        elif cmd_u == 'V':
            for p in params:
                y = p + (cy if rel else 0)
                new_params.append(y)
                cy = y
        elif cmd_u == 'C':
            for j in range(0, len(params), 6):
                cp1x, cp1y = params[j], params[j+1]
                cp2x, cp2y = params[j+2], params[j+3]
                x, y = params[j+4], params[j+5]
                if rel:
                    cp1x += cx; cp1y += cy
                    cp2x += cx; cp2y += cy
                    x += cx; y += cy
                new_params.extend([cp1x, cp1y, cp2x, cp2y, x, y])
                prev_cpx, prev_cpy = cp2x, cp2y
                cx, cy = x, y
        elif cmd_u == 'S':
            for j in range(0, len(params), 4):
                cp2x, cp2y = params[j], params[j+1]
                x, y = params[j+2], params[j+3]
                cp1x = 2*cx - prev_cpx
                cp1y = 2*cy - prev_cpy
                if rel:
                    cp2x += cx; cp2y += cy
                    x += cx; y += cy
                new_params.extend([cp1x, cp1y, cp2x, cp2y, x, y])
                prev_cpx, prev_cpy = cp2x, cp2y
                cx, cy = x, y
        elif cmd_u == 'Q':
            for j in range(0, len(params), 4):
                cp1x, cp1y = params[j], params[j+1]
                x, y = params[j+2], params[j+3]
                if rel:
                    cp1x += cx; cp1y += cy
                    x += cx; y += cy
                new_params.extend([cp1x, cp1y, x, y])
                prev_cpx, prev_cpy = cp1x, cp1y
                cx, cy = x, y
        elif cmd_u == 'T':
            for j in range(0, len(params), 2):
                x, y = params[j], params[j+1]
                cp1x = 2*cx - prev_cpx
                cp1y = 2*cy - prev_cpy
                if rel:
                    x += cx; y += cy
                new_params.extend([x, y])
                cx, cy = x, y
        elif cmd_u == 'A':
            for j in range(0, len(params), 7):
                rx, ry, xrot, large, sweep, x, y = params[j:j+7]
                if rel: x += cx; y += cy
                new_params.extend([rx, ry, xrot, large, sweep, x, y])
                cx, cy = x, y
        abs_commands.append((cmd_u, new_params))
    
    return abs_commands

def abs_commands_to_d(commands):
    parts = []
    for cmd, params in commands:
        if cmd == 'Z':
            parts.append('Z')
        else:
            parts.append(f'{cmd}{",".join(f"{p:.1f}" for p in params)}')
    return ''.join(parts)

def path_area_from_commands(commands):
    """Compute approximate area from path commands."""
    points = []
    for cmd, params in commands:
        if cmd == 'M':
            for j in range(0, len(params), 2):
                points.append((params[j], params[j+1]))
        elif cmd == 'L':
            for j in range(0, len(params), 2):
                points.append((params[j], params[j+1]))
        elif cmd == 'Z':
            if points:
                points.append(points[0])
    if len(points) < 3:
        return 0
    area = 0
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2

def simplify_commands(commands, tolerance=2.5):
    """Simplify path by converting L/M segments to fewer points using RDP."""
    new_commands = []
    i = 0
    while i < len(commands):
        cmd, params = commands[i]
        
        if cmd in ('M', 'L'):
            # Collect consecutive M/L commands as polygon vertices
            vertices = []
            j = i
            while j < len(commands) and commands[j][0] in ('M', 'L'):
                c2, p2 = commands[j]
                for k in range(0, len(p2), 2):
                    vertices.append((p2[k], p2[k+1]))
                j += 1
            
            # Simplify polygon vertices
            simplified = simplify_points(vertices, tolerance)
            
            if simplified:
                # First point as M, rest as L
                new_commands.append(('M', [simplified[0][0], simplified[0][1]]))
                for pt in simplified[1:]:
                    new_commands.append(('L', [pt[0], pt[1]]))
            
            i = j
        elif cmd == 'Z':
            new_commands.append(('Z', []))
            i += 1
        else:
            new_commands.append((cmd, params))
            i += 1
    
    return new_commands

def simplify_points(points, tolerance=2.5):
    if len(points) <= 2:
        return points
    max_dist = 0
    max_idx = 0
    for i in range(1, len(points) - 1):
        x0, y0 = points[0]
        x1, y1 = points[-1]
        x, y = points[i]
        dx = x1 - x0
        dy = y1 - y0
        if dx == 0 and dy == 0:
            dist = math.sqrt((x - x0)**2 + (y - y0)**2)
        else:
            t = max(0, min(1, ((x - x0) * dx + (y - y0) * dy) / (dx*dx + dy*dy)))
            px = x0 + t * dx
            py = y0 + t * dy
            dist = math.sqrt((x - px)**2 + (y - py)**2)
        if dist > max_dist:
            max_dist = dist
            max_idx = i
    if max_dist > tolerance:
        left = simplify_points(points[:max_idx + 1], tolerance)
        right = simplify_points(points[max_idx:], tolerance)
        return left[:-1] + right
    return [points[0], points[-1]]

def quantize_color(hex_color):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    
    palette = [
        ('#FDFDFD', (253, 253, 253)),
        ('#326EF0', (50, 110, 240)),
        ('#0D0E30', (13, 14, 48)),
        ('#0F1446', (15, 20, 70)),
        ('#F5F5F5', (245, 245, 245)),
        ('#1E1E2D', (30, 30, 45)),
        ('#DCA0A0', (220, 160, 160)),
        ('#B4B4B9', (180, 180, 185)),
        ('#3870E5', (56, 112, 229)),
        ('#181B4A', (24, 27, 74)),
        ('#141A3C', (20, 26, 60)),
        ('#0E1039', (14, 16, 57)),
        ('#10113B', (16, 17, 59)),
        ('#0D1044', (13, 16, 68)),
        ('#121334', (18, 19, 52)),
        ('#1C1F44', (28, 31, 68)),
        ('#111538', (17, 21, 56)),
        ('#30344A', (48, 52, 74)),
    ]
    
    best_hex = None
    best_dist = float('inf')
    for phex, (pr, pg, pb) in palette:
        dist = (r - pr)**2 + (g - pg)**2 + (b - pb)**2
        if dist < best_dist:
            best_dist = dist
            best_hex = phex
    
    if best_dist > 1200:  # Keep if too far from any palette color
        return f'#{r:02X}{g:02X}{b:02X}'
    return best_hex

# ─── MAIN ───
tree = ET.parse('/Users/derrick/Desktop/GitHub/Buddy/assets/icon.svg')
root = tree.getroot()
ns = 'http://www.w3.org/2000/svg'

paths_data = []
for path_elem in root.findall(f'.//{{{ns}}}path'):
    d = path_elem.get('d', '')
    fill = path_elem.get('fill', '').upper()
    transform = path_elem.get('transform', '')
    
    tx, ty = 0.0, 0.0
    if transform:
        m = re.match(r'translate\(([^)]+)\)', transform)
        if m:
            parts = m.group(1).replace(' ', '').split(',')
            tx, ty = float(parts[0]), float(parts[1])
    
    commands = parse_path_to_absolute(d, tx, ty)
    area = path_area_from_commands(commands)
    
    paths_data.append({
        'commands': commands,
        'fill': fill,
        'area': area,
        'tx': tx, 'ty': ty,
    })

print(f"Total paths: {len(paths_data)}")

# Remove background
paths_data = [p for p in paths_data if p['fill'] not in ('#FDFDFD', '#FCFCFC', '#FFFFFF')]
print(f"Without background: {len(paths_data)}")

# Remove tiny fragments
MIN_AREA = 50
paths_data = [p for p in paths_data if p['area'] > MIN_AREA]
print(f"Without fragments < {MIN_AREA}: {len(paths_data)}")

# Simplify and quantize
for p in paths_data:
    p['commands'] = simplify_commands(p['commands'], tolerance=2.0)
    p['fill'] = quantize_color(p['fill'])

# Group by fill for stats
groups = defaultdict(int)
for p in paths_data:
    groups[p['fill']] += 1

print(f"\nColor groups: {len(groups)}")
for fill, count in sorted(groups.items(), key=lambda x: -x[1]):
    print(f"  {fill}: {count} paths")

# Build new SVG
ET.register_namespace('', ns)
new_root = ET.Element('svg', {
    'version': '1.1',
    'xmlns': ns,
    'viewBox': '57 33 678 219',
    'width': '678',
    'height': '219',
})

# Background
bg = ET.SubElement(new_root, 'path')
bg.set('d', 'M0,0 L800,0 L800,272 L0,272 Z')
bg.set('fill', '#FDFDFD')
bg.set('transform', 'translate(0,0)')

# Add paths - now with no transform since coordinates are absolute
for p in paths_data:
    d = abs_commands_to_d(p['commands'])
    pe = ET.SubElement(new_root, 'path')
    pe.set('d', d)
    pe.set('fill', p['fill'])

ET.indent(tree, space='  ')
xml_str = ET.tostring(new_root, encoding='unicode')
output = '<?xml version="1.0" encoding="UTF-8"?>\n<!-- Buddy Logo -->\n' + xml_str

with open('/Users/derrick/Desktop/GitHub/Buddy/assets/icon.svg', 'w') as f:
    f.write(output)

final_count = len(paths_data)
print(f"\nFinal paths: {final_count}")
print(f"Size: {len(output)} bytes")