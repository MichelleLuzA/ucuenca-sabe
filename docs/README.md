# U Cuenca - SABE!
## Sistema de Inteligencia Territorial de la Universidad de Cuenca

---

## 📌 Descripción del Proyecto

**U Cuenca - SABE!** es un proyecto estratégico institucional que tiene como objetivo diseñar, instalar y poner en operación un **Sistema de Inteligencia Territorial** para la Universidad de Cuenca. El sistema busca capitalizar la inteligencia colectiva de los profesores e investigadores de la Universidad y articularla con la demanda real de información y análisis que enfrentan los decisores públicos del territorio, los gremios productivos, las organizaciones sociales y la cooperación internacional.

### 🎯 Objetivo General

Diseñar, instalar y poner en operación piloto, durante el período mayo–diciembre de 2026, el Sistema de Inteligencia Territorial de la Universidad de Cuenca, como proyecto estratégico institucional, dotándolo de un modelo institucional sostenible, una agenda de investigación priorizada y una primera cartera de productos y servicios que evidencien su valor ante actores internos y externos.

### 🧩 Componentes del Sistema

1. **Repositorio de datos e indicadores territoriales** - Para preparar intervenciones públicas con celeridad y rigor
2. **Agenda de investigación priorizada** - Educación superior, impacto territorial, desarrollo regional y trabajo
3. **Programa permanente de encuestas y estudios aplicados** - Posicionar a la Universidad como referente técnico

---

## 🏗️ Arquitectura de Datos (Modelo Medallón)

El proyecto implementa una arquitectura de datos en **tres capas (Medallón)** para garantizar calidad, trazabilidad y reproducibilidad:

| Capa | Descripción | Contenido | Acceso |
|------|-------------|-----------|--------|
| **🥉 Bronze** | Datos crudos, sin transformar | Fuentes originales (GTH, VIUC, DSpace, INEC, BCE) | ⚠️ **RESTRINGIDO** - Contiene datos personales (cédulas) |
| **🥈 Silver** | Datos limpios, estandarizados y enriquecidos | Datos anonimizados, con variables complementarias | ✅ Acceso general -por confirmar- |
| **🥇 Gold** | Datos agregados y optimizados para visualización | Métricas, indicadores, KPIs | ✅ Acceso general `por confirmar- |

# 🔐 Política de Datos y Privacidad

### ⚠️ IMPORTANTE

**La capa BRONCE NO está subida a este repositorio** por contener información personal identificable (cédulas, nombres completos, correos personales, etc.), en cumplimiento de:

- **Ley Orgánica de Protección de Datos Personales (LOPDP)**
- **Políticas institucionales de la Universidad de Cuenca**
- **Buenas prácticas de ciencia de datos**
