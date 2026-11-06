#!/usr/bin/env python3
"""Image-only, conservative paired-wall-gap experiment; never edits walls.

Run: python building_door_probe.py IMAGE OUTPUT_DIRECTORY
No reference, map identity, wall coordinates or trained model is accepted.
"""
import argparse
import json
from pathlib import Path
import time
import cv2
import numpy as np


def infer(image):
    scale = min(1., 1600 / max(image.shape[:2]))
    small = cv2.resize(image, None, fx=scale, fy=scale)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 60, 150)
    detected = cv2.HoughLinesP(edges, 1, np.pi / 360, 24,
                              minLineLength=28, maxLineGap=3)
    lines = []
    for row in [] if detected is None else detected.reshape(-1, 4):
        a, b = row.reshape(2, 2).astype(float)
        u = (b-a) / np.linalg.norm(b-a)
        if u[0] < 0 or (u[0] == 0 and u[1] < 0):
            a, b, u = b, a, -u
        lines.append((a, b, u))
    gaps = []
    for i, (a, b, u) in enumerate(lines):
        n = np.array([-u[1], u[0]])
        for c, d, v in lines[i+1:]:
            if abs((u[0]*v[1]-u[1]*v[0])) > .052 or abs(np.dot(c-a, n)) > 2.5:
                continue
            if np.dot(c-a, u) < 0:
                left, right = (c, d), (a, b)
            else:
                left, right = (a, b), (c, d)
            p, q = left[1], right[0]
            length = np.dot(q-p, u)
            if 8 <= length <= 45:
                gaps.append((p, q, u))
    proposals = []
    for i, (p, q, u) in enumerate(gaps):
        n = np.array([-u[1], u[0]])
        for r, s, v in gaps[i+1:]:
            thickness = abs(np.dot(r-p, n))
            if (3 <= thickness <= 12 and abs((u[0]*v[1]-u[1]*v[0])) < .052
                    and abs(np.dot(r-p, u)) < 4 and abs(np.dot(s-q, u)) < 4):
                a, b = (p+r)/2, (q+s)/2
                if not any(np.linalg.norm((a+b)/2-(x+y)/2) < 8 for x, y in proposals):
                    proposals.append((a, b))
    # shortcut: geometry cannot establish door semantics; keep proposals for review.
    return {'working_scale': scale, 'line_count': len(lines), 'single_gaps': len(gaps),
            'door_proposals': [[*(a/scale).tolist(), *(b/scale).tolist()] for a,b in proposals]}, edges


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    image = cv2.imread(str(args.image))
    if image is None:
        parser.error('Image could not be decoded')
    started = time.perf_counter()
    result, edges = infer(image)
    result['elapsed_seconds'] = time.perf_counter()-started
    args.output.mkdir(parents=True, exist_ok=True)
    overlay = image.copy()
    for x1,y1,x2,y2 in result['door_proposals']:
        a,b = (round(x1),round(y1)),(round(x2),round(y2))
        cv2.line(overlay,a,b,(0,0,255),8)
        cv2.circle(overlay,a,10,(0,255,255),3)
        cv2.circle(overlay,b,10,(0,255,255),3)
    cv2.imwrite(str(args.output/'overlay.jpg'), overlay)
    cv2.imwrite(str(args.output/'edges.png'), edges)
    (args.output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    assert infer(np.full((256,256,3),220,np.uint8))[0]['door_proposals'] == []
    print(json.dumps({k:v for k,v in result.items() if k!='door_proposals'} | {'proposal_count':len(result['door_proposals'])}))

if __name__ == '__main__':
    main()
