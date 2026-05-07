from pathlib import Path
import rasterio
import numpy as np

raster_path = Path("./recorte_luiz/S2A_tile_20240424_22KEG_0_[-50.88164601780857,-17.09766966949844,-50.86322615913537,-17.0790187780_clip.tif")

output_dir = Path("./NDVI_luiz")
output_dir.mkdir(exist_ok=True)

print(f"Gerando NDVI de {raster_path.name}")

with rasterio.open(raster_path) as src:
    red = src.read(1).astype(float)
    nir = src.read(4).astype(float)

    profile = src.profile.copy()

    ndvi = np.where(
        (nir + red) == 0,
        0,
        (nir - red) / (nir + red)
    )

profile.update(
    dtype=rasterio.float32,
    count=1,
    nodata=-9999
)

outfile = output_dir / f"{raster_path.stem}_ndvi.tif"

with rasterio.open(outfile, "w", **profile) as dst:
    dst.write(ndvi.astype(rasterio.float32), 1)

print("\nNDVI gerado com sucesso.")
