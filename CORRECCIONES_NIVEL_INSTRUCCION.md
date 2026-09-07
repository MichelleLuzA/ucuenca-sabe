# Correcciones: Manejo de Variables Diferentes pero del Mismo Tema

## 🔴 PROBLEMA IDENTIFICADO

En el dataset ENEMDU 2021-2025, existen **variables diferentes que preguntan sobre el mismo tema**, con **estructuras incompatibles**:

### Ejemplo 1: Nivel de Instrucción

| Característica | p10a | nnivins |
|---|---|---|
| **Años disponibles** | 2021-2022, 2024-2025 | 2023 SOLO |
| **Categorías** | 10 (detallado) | 5 (simplificado) |
| **Pregunta** | "¿Cuál es tu nivel de instrucción?" (detallado) | "¿Cuál es tu nivel de instrucción?" (simplificado) |
| **¿Son intercambiables?** | ❌ **NO** |

#### Etiquetas de p10a (10 categorías):
```
1: Ninguno
2: Centro de alfabetización
3: Jardín de infantes
4: Primaria
5: Educación Básica
6: Secundaria
7: Educación Media/Bachillerato
8: Superior no universitaria
9: Superior universitaria
10: Post-grado
```

#### Etiquetas de nnivins (5 categorías):
```
1: Ninguno
2: Centro de Alfabetización
3: Educación Básica
4: Educación Media/Bachillerato
5: Superior
```

**El problema:** No puedes "mapear" nnivins a p10a sin perder información:
- nnivins nunca pregunta por Jardín, Primaria o Secundaria como categorías separadas
- nnivins agrupa "Superior no uni" + "Superior uni" en una sola categoría
- Son **preguntas diferentes, no versiones de la misma**

---

## ✅ SOLUCIÓN IMPLEMENTADA

### 1. **NO normalizar entre variables diferentes**

Eliminé la función `normalize_nivel_instruccion()` que intentaba mapear nnivins → p10a.

**Razón**: Eso falsificaba los datos.

### 2. **Crear fallbacks SEPARADOS para cada variable**

```python
# Para p10a (2021-2022, 2024-2025)
FALLBACK_NIVEL_INSTRUCCION: Dict[int, str] = {
    1: "Ninguno",
    2: "Centro de alfabetización",
    3: "Jardín de infantes",
    4: "Primaria",
    5: "Educación Básica",
    6: "Secundaria",
    7: "Educación Media/Bachillerato",
    8: "Superior no universitaria",
    9: "Superior universitaria",
    10: "Post-grado",
}

# Para nnivins (2023 SOLO)
FALLBACK_NNIVINS: Dict[int, str] = {
    1: "Ninguno",
    2: "Centro de Alfabetización",
    3: "Educación Básica",
    4: "Educación Media/Bachillerato",
    5: "Superior",
}
```

### 3. **Detectar y usar la variable correcta por año**

```python
def get_nivel_instruccion_variable(df, ano):
    """Detecta cuál variable usar según el año."""
    if ano == 2023:
        return 'nnivins'  # 5 categorías
    else:
        return 'p10a'     # 10 categorías
```

### 4. **Normalizar espacios en blanco (lo ÚNICO que se mapea)**

```python
# En classify_labels() y resolve_map()
norm = str(text).strip().lower()  # Elimina " Urbana" → "Urbana"
```

---

## 📝 OTRAS VARIABLES CON EL MISMO PATRÓN

Revisar en tu pipeline si hay otras variables que **cambian de estructura pero preguntan sobre lo mismo**:

- `condact`: Cambió ligeramente en 2022, pero la estructura se mantiene
- `p59`, `p60a-k`: Solo existen en 2021-2023 (desaparecen en 2024-2025)
- `p081`, `p085`: Nuevas en 2024-2025

**No intentes "unificar" estas. Trátalas como variantes de la misma pregunta, no como la misma pregunta.**

---

## 🎯 CÓMO USAR EN TU CÓDIGO

### Para procesar nivel de instrucción:

```python
from src.processing.enemdu_mappings import (
    FALLBACK_NIVEL_INSTRUCCION,
    FALLBACK_NNIVINS,
    resolve_map,
    EDU_PATTERNS
)

def process_nivel_instruccion(df, meta, ano):
    value_labels = meta.variable_value_labels
    
    # Detectar cuál variable existe
    if ano == 2023 and 'nnivins' in value_labels:
        labels = value_labels['nnivins']
        fallback = FALLBACK_NNIVINS
        var_name = 'nnivins'
    elif 'p10a' in value_labels:
        labels = value_labels['p10a']
        fallback = FALLBACK_NIVEL_INSTRUCCION
        var_name = 'p10a'
    else:
        raise ValueError(f"Año {ano}: no encontrada variable nivel_instruccion")
    
    # Aplicar clasificación y normalización
    result, source = resolve_map(labels, EDU_PATTERNS, fallback)
    
    return result, var_name, source
```

---

## 📊 CAMBIOS EN ENEMDU_MAPPINGS.PY

| Cambio | Antes | Después |
|--------|-------|---------|
| `FALLBACK_NNIVINS` | ❌ No existía | ✅ Nuevo (5 categorías) |
| `normalize_nivel_instruccion()` | ❌ Existía (INCORRECTO) | ✅ Eliminada |
| `.strip()` en funciones | ✅ Sí | ✅ Se mantiene |
| `FALLBACK_CONDACT` | ✅ Actualizado | ✅ Con código 0 |

---

## ⚠️ IMPORTANTE

**NO es problema tener variables diferentes del mismo tema.**

Es un PROBLEMA:
- ❌ Intentar unificarlas artificialmente
- ❌ Perder información en el mapeo
- ❌ Asumir que son intercambiables

La solución:
- ✅ Documentarlas como diferentes
- ✅ Usar fallbacks específicos para cada una
- ✅ Dejar que el usuario elija cómo combinarlas (si lo desea)
