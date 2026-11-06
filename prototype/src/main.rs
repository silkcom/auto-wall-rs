// Throwaway detector comparison, not a public library or a calibrated detector.
use image::{GrayImage, Luma};
use imageproc::{
    contours::{BorderType, find_contours},
    geometry::approximate_polygon_dp,
    point::Point,
};
use serde_json::json;
use std::{env, time::Instant};
fn area(p: &[Point<i32>]) -> f64 {
    p.iter()
        .zip(p.iter().cycle().skip(1))
        .take(p.len())
        .map(|(a, b)| a.x as f64 * b.y as f64 - b.x as f64 * a.y as f64)
        .sum::<f64>()
        .abs()
        / 2.0
}
fn main() {
    let a: Vec<String> = env::args().collect();
    let start = Instant::now();
    let original = image::ImageReader::open(&a[1])
        .unwrap()
        .with_guessed_format()
        .unwrap()
        .decode()
        .unwrap()
        .to_rgb8();
    let decode = start.elapsed().as_secs_f64() * 1000.;
    let t = Instant::now();
    let (ow, oh) = original.dimensions();
    let cap: u32 = a.get(3).map(|s| s.parse().unwrap()).unwrap_or(1600);
    let scale = (cap as f64 / ow.max(oh) as f64).min(1.0);
    let rgb = image::imageops::resize(
        &original,
        (ow as f64 * scale).round() as u32,
        (oh as f64 * scale).round() as u32,
        image::imageops::FilterType::Triangle,
    );
    let (w, h) = rgb.dimensions();
    let sx = ow as f64 / w as f64;
    let sy = oh as f64 / h as f64;
    let gray = image::DynamicImage::ImageRgb8(rgb.clone()).to_luma8();
    let mode = &a[2];
    let mask = if mode == "edges" {
        let edges = imageproc::edges::canny(&gray, 30., 80.);
        imageproc::morphology::close(&edges, imageproc::distance_transform::Norm::LInf, 1)
    } else {
        let threshold = if mode == "void" {
            25
        } else if mode == "dark40" {
            40
        } else {
            70
        };
        GrayImage::from_fn(w, h, |x, y| {
            Luma([if gray.get_pixel(x, y)[0] < threshold {
                255
            } else {
                0
            }])
        })
    };
    let mask = if mode == "void" {
        let closed =
            imageproc::morphology::close(&mask, imageproc::distance_transform::Norm::LInf, 3);
        imageproc::morphology::open(&closed, imageproc::distance_transform::Norm::LInf, 3)
    } else {
        mask
    };
    let mut walls = Vec::new();
    let mut components = 0;
    let min_area = if mode == "void" { 0.001 } else { 0.00008 };
    let epsilon = if mode == "void" { 5.0 } else { 3.0 };
    for c in find_contours::<i32>(&mask) {
        if c.points.len() < 8 || area(&c.points) < (w as f64 * h as f64 * min_area).max(25.) {
            continue;
        }
        // Ignore the image border itself; keep holes in a connected dark background.
        if c.border_type == BorderType::Outer
            && c.points
                .iter()
                .any(|p| p.x == 0 || p.y == 0 || p.x == w as i32 - 1 || p.y == h as i32 - 1)
        {
            continue;
        }
        let p = approximate_polygon_dp(&c.points, epsilon, true);
        if p.len() < 3 {
            continue;
        }
        components += 1;
        for (a, b) in p.iter().zip(p.iter().cycle().skip(1)).take(p.len()) {
            if a == b {
                continue;
            }
            walls.push([
                [a.x as f64 * sx, a.y as f64 * sy],
                [b.x as f64 * sx, b.y as f64 * sy],
            ]);
        }
    }
    let lights_mask = GrayImage::from_fn(w, h, |x, y| {
        let p = rgb.get_pixel(x, y).0;
        let [r, g, b] = p.map(|v| v as f64);
        Luma([
            if r > 175. && g > 95. && r > g * 1.10 && g > b * 1.30 && r - b > 65. {
                255
            } else {
                0
            },
        ])
    });
    let mut lights = Vec::new();
    for c in find_contours::<i32>(&lights_mask) {
        let ar = area(&c.points);
        if c.border_type != BorderType::Outer || ar < 4. || ar > 200. || c.points.is_empty() {
            continue;
        }
        let n = c.points.len() as f64;
        let x = c.points.iter().map(|p| p.x as f64).sum::<f64>() / n;
        let y = c.points.iter().map(|p| p.y as f64).sum::<f64>() / n;
        if lights
            .iter()
            .any(|p: &[f64; 2]| (p[0] - x * sx).hypot(p[1] - y * sy) < 12. * sx)
        {
            continue;
        }
        lights.push([x * sx, y * sy]);
    }
    let detect = t.elapsed().as_secs_f64() * 1000.;
    println!(
        "{}",
        json!({"mode":mode,"original":[ow,oh],"working":[w,h],"decode_ms":decode,"detect_ms":detect,"wall_components":components,"walls":walls,"lights":lights,"portals":[],"simplify_working_pixels":epsilon})
    );
}
