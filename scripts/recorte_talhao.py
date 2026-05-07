import geopandas as gpd
import rasterio
import rasterio.mask
from pathlib import Path


rasters_dir = Path("./Luiz Galego")          
shape_path = Path("Luiz Galego/Limite_do_talhão/FAZ_BURITI_II.shp")
outdir = Path("./recorte_luiz")

outdir.mkdir(exist_ok=True)


gdf = gpd.read_file(shape_path)

for raster_path in rasters_dir.glob("*.TIF"):

    print(f"Recortando {raster_path.name}")     

    with rasterio.open(raster_path) as src:

    
        if gdf.crs != src.crs:
            gdf_proj = gdf.to_crs(src.crs)
        else:
            gdf_proj = gdf

        shapes = gdf_proj.geometry.values

        out_image, out_transform = rasterio.mask.mask(
            src, shapes, crop=True
        )

        out_meta = src.meta.copy()

    out_meta.update({
        "driver": "GTiff",
        "height": out_image.shape[1],
        "width": out_image.shape[2],
        "transform": out_transform
    })

    outfile = outdir / f"{raster_path.stem}_clip.tif"

    with rasterio.open(outfile, "w", **out_meta) as dest:
        dest.write(out_image)

print("\nTodos os rasters foram recortados.")
