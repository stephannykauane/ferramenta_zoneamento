import rasterio
import numpy as np
from rasterio.mask import mask
import geopandas as gpd
from skimage.segmentation import slic
from skimage import graph
import pandas as pd
from rasterio.features import shapes
from shapely.geometry import shape
from sklearn.cluster import AgglomerativeClustering
import networkx as nx
import os


stack_path = "./data/clientes/TALHAO TESTE/NDVI/S2A_tile_20240424_5m_[-50.882981229969396,-17.097573954292077,-50.86088953785392,-17.079685949383393]_clip_ndvi.tif"
talhao_path = "data/clientes/TALHAO TESTE/Limite_luiz"
base_output_dir = "zoneamento_luiz/10_M/300_10Z"

lista_compactness = [0.01, 0.03, 0.05, 0.07, 0.08]
n_segments_fixo = 300
n_zonas_final = 10


distancia_suavizacao = 10 


gdf = gpd.read_file(talhao_path)
with rasterio.open(stack_path) as src:
    if gdf.crs != src.crs:
        gdf = gdf.to_crs(src.crs)
    img_masked, transform = mask(src, gdf.geometry, crop=True, nodata=np.nan)
    profile = src.profile.copy()
    res_x, res_y = src.res

img_real = img_masked[0].astype(np.float32) 


min_val = np.nanpercentile(img_real, 2)
max_val = np.nanpercentile(img_real, 98)
img_norm = np.clip((img_real - min_val) / (max_val - min_val), 0, 1)

mask_slic = ~np.isnan(img_real)
img_slic_input = np.nan_to_num(img_norm, nan=0).astype(np.float64)
img_slic_input_3d = img_slic_input[:, :, np.newaxis]

for cp in lista_compactness:
    cp_str = str(cp).replace('.', '_')
    id_name = f"zoneamento_10M_{cp_str}_n{n_segments_fixo}"
    
    path_final = os.path.join(base_output_dir, id_name)
    os.makedirs(path_final, exist_ok=True)
    
    print(f"\nProcessando com Arredondamento: {id_name}")


    superpixels = slic(
        img_slic_input_3d,
        mask=mask_slic,
        n_segments=n_segments_fixo, 
        compactness=cp,
        start_label=1,
        channel_axis=-1,
        enforce_connectivity=True
    )

    g = graph.RAG(superpixels)
    if 0 in g: g.remove_node(0)
    superpixel_ids = np.array(sorted(g.nodes))
    features_medias = np.array([[img_slic_input[superpixels == s_id].mean()] for s_id in superpixel_ids])
    connectivity = nx.adjacency_matrix(g, nodelist=superpixel_ids)
    model = AgglomerativeClustering(n_clusters=n_zonas_final, connectivity=connectivity, linkage='ward')
    labels_finais = model.fit_predict(features_medias)

    mapa_sub = {s_id: label + 1 for s_id, label in zip(superpixel_ids, labels_finais)}
    zonas = np.zeros_like(superpixels)
    for s_id, z_id in mapa_sub.items():
        zonas[superpixels == s_id] = z_id
    zonas[~mask_slic] = 0

    stats = []
    area_pixel_ha = (res_x * res_y) / 10000  
    for z in np.unique(zonas[zonas > 0]):
        mask_z = (zonas == z)
        stats.append({
            "Zona": int(z),
            "NDVI_Medio": round(float(np.nanmean(img_real[mask_z])), 4),
            "Area_Hectares": round(np.sum(mask_z) * area_pixel_ha, 2)
        })
    df_stats = pd.DataFrame(stats)


    polygons = []
    values = []
    for geom, value in shapes(zonas.astype(np.int16), mask=(zonas > 0), transform=transform):
        polygons.append(shape(geom))
        values.append(int(value))
    
    gdf_zonas = gpd.GeoDataFrame({"zona": values}, geometry=polygons, crs=profile['crs'])
    

    gdf_zonas = gdf_zonas.dissolve(by='zona').reset_index()

    gdf_zonas['geometry'] = gdf_zonas['geometry'].buffer(distancia_suavizacao, join_style=1).buffer(-distancia_suavizacao, join_style=1)
    

    gdf_zonas['geometry'] = gdf_zonas['geometry'].simplify(2, preserve_topology=True)

    
    gdf_zonas = gdf_zonas.merge(df_stats[['Zona', 'NDVI_Medio']], left_on='zona', right_on='Zona').drop(columns=['Zona'])
    gdf_zonas.to_file(os.path.join(path_final, f"vector_{id_name}.shp"))
    df_stats.to_csv(os.path.join(path_final, f"stats_{id_name}.csv"), index=False)

    profile.update(
    height=zonas.shape[0],
    width=zonas.shape[1],
    transform=transform,
    dtype=rasterio.int16,
    count=1,
    nodata=0
)

    out_tif = os.path.join(path_final, f"raster_{id_name}.tif")

    with rasterio.open(out_tif, "w", **profile) as dst:
        dst.write(zonas.astype(np.int16), 1)

    print(f"Raster salvo em: {out_tif}")

    print(f"Sucesso: Zoneamento arredondado salvo em {path_final}")

print("\nProcesso concluído!")