import geopandas as gpd
from shapely.geometry import box
import numpy as np
import os
import pathlib
from pathlib import Path


brasil = gpd.read_file("../data/temp/SHAPEFILE_BRASIL/BR_Pais_2025.shp").to_crs("EPSG:4326")
brasil_geom = brasil.geometry.union_all()

minx, miny, maxx, maxy = brasil_geom.bounds

step = 1.0

cells = []
attrs = []

cell_id = 0

for x in np.arange(minx, maxx, step):
    for y in np.arange(miny, maxy, step):
        cell = box(x, y, x + step, y + step)

        if cell.intersects(brasil_geom):
            cells.append(cell)
            attrs.append({
                "cell_id": cell_id,
                "downloaded": 0,
                "tentativas": 0,
                "dem_path": ""
            })

            cell_id += 1

grid = gpd.GeoDataFrame(attrs, geometry=cells, crs="EPSG:4326")

grid.to_file("../data/temp/GRID_BRASIL/grid_brasil.shp")

