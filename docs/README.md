# UCuenca-SABE!
## Sistema de articulación de experticias para la incidencia pública y privada

---

## 📌 Descripción del Proyecto

**UCuenca-SABE!** es un proyecto estratégico del Rectorado de la Universidad de Cuenca. Su propósito es diseñar, instalar y poner en operación un sistema que capitaliza la inteligencia colectiva de profesores e investigadores, articulándola con la demanda de información de los decisores públicos del territorio, los gremios productivos, las organizaciones sociales y la cooperación internacional.

### 🎯 Objetivo General

Diseñar, instalar y poner en operación piloto, durante el período mayo–diciembre de 2026, el sistema como proyecto estratégico institucional, dotándolo de un modelo institucional sostenible, una agenda de investigación priorizada y una primera cartera de productos y servicios que evidencien su valor ante actores internos y externos.

### 🧩 Componentes del Sistema

1. **Repositorio de datos e indicadores territoriales** - Para preparar intervenciones públicas con celeridad y rigor.
2. **Agenda de investigación priorizada** - Educación superior, impacto territorial, desarrollo regional y trabajo.
3. **Programa permanente de encuestas y estudios aplicados** - Posicionar a la Universidad como referente técnico.

---

## 🏗️ Arquitectura de Datos (Modelo Medallón)

El sistema implementa una arquitectura de datos en tres capas (Medallón) para garantizar calidad, trazabilidad y reproducibilidad:

| Capa | Descripción | Contenido | Acceso |
|------|-------------|-----------|--------|
| **🥉 Bronze** | Datos crudos, sin transformar | Fuentes originales (GTH, VIUC, DSpace, INEC, BCE) | ⚠️ **RESTRINGIDO** - Contiene datos personales (cédulas) |
| **🥈 Silver** | Datos limpios, estandarizados y enriquecidos | Datos anonimizados, con variables complementarias | ✅ Acceso general (por confirmar) |
| **🥇 Gold** | Datos agregados y optimizados para visualización | Métricas, indicadores, KPIs | ✅ Acceso general (por confirmar) |

---

## 🔐 Política de Datos y Privacidad

### ⚠️ IMPORTANTE

**La capa BRONCE NO está subida a este repositorio** por contener información personal identificable (cédulas, nombres completos, correos personales, etc.), en cumplimiento de:

- **Ley Orgánica de Protección de Datos Personales (LOPDP)**
- **Políticas institucionales de la Universidad de Cuenca**
- **Buenas prácticas de ciencia de datos**

---

## 📂 Estructura y Nomenclatura

Este repositorio aloja el código y la documentación correspondiente a la versión beta del sitio web del proyecto.

- El nombre del repositorio y los títulos de los tableros utilizan exclusivamente la denominación `UCuenca-SABE!`.
- Los términos "Sistema de Inteligencia Territorial", "Sistema de Inteligencia Laboral" y "Observatorio" han sido retirados de todas las piezas públicas (código, documentación y visualizaciones) en línea con la guía de estilo institucional.
- Las referencias al sistema en el código fuente utilizan el descriptor oficial definido en el proyecto.

---

## 📖 Guía de Estilo

Para el desarrollo de piezas públicas (sitio web, tableros, documentos de difusión, redes sociales), se debe seguir rigurosamente la **Guía de Estilo para Piezas Públicas (DPE-GE-009)**. Esta guía establece:

- Identidad verbal y reglas de nomenclatura.
- Voz y tono institucional.
- Paleta de colores, tipografías y uso de logotipo.
- Criterios de accesibilidad y manejo de fuentes de datos.

---

## ✅ Verificación Previa a la Publicación

Antes de cualquier despliegue o actualización de la landing page, se debe verificar que:

1. El nombre del Sistema esté escrito como **UCuenca-SABE!**.
2. No aparezcan términos retirados en títulos, menús o metadatos.
3. Toda cifra publicada incluya fuente y año.
4. Las afirmaciones sean proporcionales a la evidencia disponible.
5. Se haya identificado claramente si el contenido es un producto institucional o un aporte de una persona investigadora.

---

*Documento actualizado en agosto de 2026, versión 1.0. En caso de dudas sobre la aplicación de la guía, consulte con la Dirección de Proyectos Estratégicos.*
