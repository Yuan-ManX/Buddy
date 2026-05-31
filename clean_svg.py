"""Clean and simplify the Buddy logo SVG - merge fragments, unify colors, remove noise."""
import xml.etree.ElementTree as ET
import re
import math
from collections import defaultdict

# Parse original SVG
tree = ET.parse('/Users/derrick/Desktop/GitHub/Buddy/assets/icon.svg')
root = tree.getroot()
ns = 'http://www.w3.org/2000/svg'

def parse_path_to_absolute(d, tx, ty):
    """Parse SVG path d attribute and convert to absolute coordinates."""
    tokens = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', d)
    points = []
    cx, cy = tx, ty  # start with transform offset
    start_x, start_y = cx, cy
    prev_cpx, prev_cpy = cx, cy
    i = 0
    
    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        if cmd in 'Zz':
            cx, cy = start_x, start_y
            points.append((cx, cy))
            continue
        
        params = []
        while i < len(tokens) and re.match(r'^[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?$', tokens[i]):
            params.append(float(tokens[i]))
            i += 1
        
        rel = cmd.islower()
        cmd_u = cmd.upper()
        
        if cmd_u == 'M':
            for j in range(0, len(params), 2):
                x, y = params[j], params[j+1]
                if rel: x += cx; y += cy
                cx, cy = x, y
                start_x, start_y = x, y
                points.append((x, y))
        elif cmd_u == 'L':
            for j in range(0, len(params), 2):
                x, y = params[j], params[j+1]
                if rel: x += cx; y += cy
                cx, cy = x, y
                points.append((x, y))
        elif cmd_u == 'H':
            for p in params:
                x = p + (cx if rel else 0)
                cx = x
                points.append((cx, cy))
        elif cmd_u == 'V':
            for p in params:
                y = p + (cy if rel else 0)
                cy = y
                points.append((cx, cy))
        elif cmd_u == 'C':
            for j in range(0, len(params), 6):
                cp1x, cp1y = params[j], params[j+1]
                cp2x, cp2y = params[j+2], params[j+3]
                x, y = params[j+4], params[j+5]
                if rel:
                    cp1x += cx; cp1y += cy
                    cp2x += cx; cp2y += cy
                    x += cx; y += cy
                points.append((cp1x, cp1y))
                points.append((cp2x, cp2y))
                points.append((x, y))
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
                points.append((cp1x, cp1y))
                points.append((cp2x, cp2y))
                points.append((x, y))
                prev_cpx, prev_cpy = cp2x, cp2y
                cx, cy = x, y
        elif cmd_u == 'Q':
            for j in range(0, len(params), 4):
                cp1x, cp1y = params[j], params[j+1]
                x, y = params[j+2], params[j+3]
                if rel:
                    cp1x += cx; cp1y += cy
                    x += cx; y += cy
                points.append((cp1x, cp1y))
                points.append((x, y))
                prev_cpx, prev_cpy = cp1x, cp1y
                cx, cy = x, y
        elif cmd_u == 'T':
            for j in range(0, len(params), 2):
                x, y = params[j], params[j+1]
                cp1x = 2*cx - prev_cpx
                cp1y = 2*cy - prev_cpy
                if rel:
                    x += cx; y += cy
                points.append((cp1x, cp1y))
                points.append((x, y))
                cx, cy = x, y
        elif cmd_u == 'A':
            for j in range(0, len(params), 7):
                x, y = params[j+5], params[j+6]
                if rel: x += cx; y += cy
                points.append((x, y))
                cx, cy = x, y
    return points

def path_area(points):
    """Compute approximate area of a polygon using shoelace formula."""
    if len(points) < 3:
        return 0
    area = 0
    n = len(points)
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2

def path_bbox(points):
    if not points:
        return (0, 0, 0, 0)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))

def points_to_path_d(points):
    if not points:
        return ''
    d = f'M{points[0][0]:.1f},{points[0][1]:.1f}'
    for p in points[1:]:
        d += f'L{p[0]:.1f},{p[1]:.1f}'
    d += 'Z'
    return d

def simplify_points(points, tolerance=2.0):
    """Ramer-Douglas-Peucker simplification."""
    if len(points) <= 2:
        return points
    max_dist = 0
    max_idx = 0
    for i in range(1, len(points) - 1):
        # Distance from point to line segment (first to last)
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

# Color quantization - map similar colors to a palette
def quantize_color(hex_color):
    """Map a hex color to one of the key palette colors."""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    
    # Define palette
    palette = {
        'bg':      (253, 253, 253, '#FDFDFD'),
        'blue':    (50, 110, 240, '#326EF0'),
        'blue_dk': (13, 14, 48, '#0D0E30'),
        'blue_md': (15, 20, 70, '#0F1446'),
        'white':   (245, 245, 245, '#F5F5F5'),
        'gray':    (180, 180, 185, '#B4B4B9'),
        'accent':  (30, 30, 45, '#1E1E2D'),
        'warm':    (220, 160, 160, '#DCA0A0'),
    }
    
    best = None
    best_dist = float('inf')
    for name, (pr, pg, pb, phex) in palette.items():
        dist = (r - pr)**2 + (g - pg)**2 + (b - pb)**2
        if dist < best_dist:
            best_dist = dist
            best = (name, phex)
    
    # If too far from any palette color, keep original
    if best_dist > 2500:  # ~50 per channel
        return hex_color.upper()
    return best[1]

# Collect all paths
paths = []
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
    
    points = parse_path_to_absolute(d, tx, ty)
    area = path_area(points)
    bbox = path_bbox(points)
    
    paths.append({
        'fill': fill,
        'points': points,
        'area': area,
        'bbox': bbox,
    })

print(f"Total paths: {len(paths)}")

# Remove background
paths = [p for p in paths if p['fill'] not in ('#FDFDFD', '#FCFCFC', '#FFFFFF')]
print(f"After removing background: {len(paths)}")

# Remove tiny fragments (noise)
MIN_AREA = 30
paths = [p for p in paths if p['area'] > MIN_AREA]
print(f"After removing fragments < {MIN_AREA}px²: {len(paths)}")

# Quantize colors
for p in paths:
    p['fill'] = quantize_color(p['fill'])

# Group by fill color
groups = defaultdict(list)
for p in paths:
    groups[p['fill']].append(p)

print(f"Color groups: {len(groups)}")
for color, group in sorted(groups.items(), key=lambda x: -len(x[1])):
    print(f"  {color}: {len(group)} paths")

# Build output SVG
ET.register_namespace('', 'http://www.w3.org/2000/svg')

# Create new root
new_root = ET.Element('svg', {
    'version': '1.1',
    'xmlns': 'http://www.w3.org/2000/svg',
    'viewBox': '57 33 678 219',
    'width': '678',
    'height': '219',
})

# Add background
bg = ET.SubElement(new_root, 'path')
bg.set('d', 'M0,0 L800,0 L800,272 L0,272 Z')
bg.set('fill', '#FDFDFD')
bg.set('transform', 'translate(0,0)')

# Add simplified paths grouped by color
for color, group in sorted(groups.items(), key=lambda x: -len(x[1])):
    # Merge all points of same color, simplify, and create one path
    all_points = []
    for p in group:
        sp = simplify_points(p['points'], tolerance=2.5)
        if len(sp) >= 3:
            all_points.append(sp)
    
    # Create individual paths for each merged shape
    for pts in all_points:
        d = points_to_path_d(pts)
        path_elem = ET.SubElement(new_root, 'path')
        path_elem.set('d', d)
        path_elem.set('fill', color)

# Write output
tree = ET.ElementTree(new_root)
ET.indent(tree, space='  ')
xml_str = ET.tostring(new_root, encoding='unicode')

# Add XML declaration
output = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

with open('/Users/derrick/Desktop/GitHub/Buddy/assets/icon.svg', 'w') as f:
    f.write(output)

# Count final paths
final_count = len(new_root.findall(f'.//{{{ns}}}path')) - 1  # minus background
print(f"\nFinal paths: {final_count}")
print(f"File size: {len(output)} bytes")

# Also print the color breakdown
color_counts = defaultdict(int)
for path_elem in new_root.findall(f'.//{{{ns}}}path'):
    fill = path_elem.get('fill', '')
    if fill != '#FDFDFD':
        color_counts[fill] += 1

print("\nFinal color distribution:")
for color, count in sorted(color_counts.items(), key=lambda x: -x[1]):
    print(f"  {color}: {count} paths")