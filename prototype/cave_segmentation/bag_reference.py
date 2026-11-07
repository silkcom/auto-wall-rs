"""Convert a private, geometry-only Bag of Mapping snapshot to evaluation UVTT."""
import argparse,hashlib,json,math
from pathlib import Path
import cv2


def convert(source,image,output,base_width=52):
    raw=Path(source).read_bytes();data=json.loads(raw);im=cv2.imread(str(image));assert im is not None
    assert math.isfinite(base_width) and base_width>0
    zoom=float(data['mapZoom']);assert math.isfinite(zoom) and zoom>0
    # shortcut: nonzero image offsets/layers need their own verified registration.
    assert float(data['mapXOffset'])==float(data['mapYOffset'])==0,'Only verified zero-offset maps supported'
    assert not data.get('active_map_layer_id') and not data.get('map_layers'),'Layer transforms require registration'
    geometry=data['vttData'];ppg=base_width/zoom;h,w=im.shape[:2]
    for line in geometry.get('line_of_sight',[]):
        assert all(math.isfinite(p[k]) for p in line for k in ('x','y'))
    result={**geometry,'format':.3,'resolution':{'pixels_per_grid':ppg,'map_size':{'x':w/ppg,'y':h/ppg},'map_origin':{'x':0,'y':0}},'evaluation_provenance':{'source':'User-provided Bag of Mapping annotation','snapshot_sha256':hashlib.sha256(raw).hexdigest(),'image_sha256':hashlib.sha256(Path(image).read_bytes()).hexdigest(),'annotation_source':data.get('vttEditorMeta',{}).get('source'),'coordinate_conversion':'pixel = grid_unit * base_token_width / saved_image_zoom; zero image offsets','base_token_width':base_width,'role':'Reference evaluation only; not inference input'}}
    Path(output).write_text(json.dumps(result))
    return {'dimensions':[w,h],'pixels_per_grid':ppg,'wall_segments':sum(len(p)-1 for p in geometry.get('line_of_sight',[])),'portals':len(geometry.get('portals',[]))}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('snapshot');p.add_argument('image');p.add_argument('output');p.add_argument('--base-width',type=float,default=52);a=p.parse_args();print(json.dumps(convert(a.snapshot,a.image,a.output,a.base_width)))
