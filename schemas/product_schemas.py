from pydantic import BaseModel, ConfigDict
from typing import List, Optional

# --- SCHEMAS (Pydantic) ---

class StockSucursalInput(BaseModel):
    sucursal_id: int
    cantidad_asignada: int

class VarianteUpdateInput(BaseModel):
    id: int
    mostrar_en_web: bool
    configuracion_stock: List[StockSucursalInput]

class ProductoUpdateSchema(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio_web: Optional[float] = None
    en_tienda_online: Optional[bool] = None
    variantes: Optional[List[VarianteUpdateInput]] = []
    discount_percentage: Optional[float] = 0

    # Configuración V2
    model_config = ConfigDict(from_attributes=True)