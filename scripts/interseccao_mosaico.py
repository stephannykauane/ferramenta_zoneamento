import os
from pathlib import Path

import geopandas as gpd
import requests
from dotenv import load_dotenv



caminho_shp_1 = Path("../data/clientes/TALHAO TESTE/Limite_luiz/FAZ_BURITI_II.shp")
caminho_tiles = Path("../data/temp/GRID_BRASIL")

DEM_TYPE = "SRTMGL1"
OUTPUT_DIR = "../data/dem_teste"



try:


    os.makedirs(OUTPUT_DIR, exist_ok=True)

    load_dotenv()
    api_key = os.getenv("API_KEY")

    if not api_key:
        raise ValueError("API_KEY não encontrada no .env")


    gdf_1 = gpd.read_file(caminho_shp_1)

    if gdf_1.empty:
        raise ValueError("Shapefile do cliente está vazio")

    geom_area = gdf_1.geometry.union_all()

    for shp in caminho_tiles.rglob("*.shp"):

        try:
            gdf_2 = gpd.read_file(shp)

            if gdf_2.empty:
                print(f"arquivo vazio: {shp}")
                continue


            if gdf_1.crs != gdf_2.crs:
                print(f"crs diferentes: {shp.name}")
                gdf_2 = gdf_2.to_crs(gdf_1.crs)


            mask = gdf_2.intersects(geom_area)
            tiles_intersectadas = gdf_2[mask]

            if tiles_intersectadas.empty:
                print(f"sem interseccao: {shp}")
                continue

            print(f"tem interseccao: {shp}")

  
            tiles_wgs84 = tiles_intersectadas.to_crs("EPSG:4326")

            minx, miny, maxx, maxy = tiles_wgs84.total_bounds

            south = miny
            north = maxy
            west = minx
            east = maxx

            url = (
                "https://portal.opentopography.org/API/globaldem"
                f"?demtype={DEM_TYPE}"
                f"&south={south}"
                f"&north={north}"
                f"&west={west}"
                f"&east={east}"
                f"&outputFormat=GTiff"
                f"&API_Key={api_key}"
            )

            print("baixando DEM...")

            r = requests.get(url, stream=True)

            if r.status_code != 200:
                print(f"erro na API para {shp.name}:")
                print(r.text)
                continue

            output_file = os.path.join(
                OUTPUT_DIR,
                f"{shp.stem}_dem.tif"
            )

            with open(output_file, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            print(f"DEM salvo em: {output_file}")

        except Exception as e:
            print(f"erro no arquivo {shp.name}: {e}")

except Exception as e:
    print(f"erro geral: {e}")