import pandas as pd
import os 
from pathlib import Path

# ============================================================
# CONFIGURACIÓN - Cambia estas rutas según tu proyecto
# ============================================================

RUTA_EXCEL = r"C:\Users\michu\Documents\ucuenca-sabe\data\silver\silver_catastropure.xlsx"
HOJA = None
CARPETA_SALIDA = r"C:\Users\michu\Documents\ucuenca-sabe\visualizacion"
NOMBRE_HTML = "mapa_investigacion.html"

# ============================================================
# FIN DE CONFIGURACIÓN
# ============================================================

def cargar_datos_excel(ruta_excel, hoja=None):
    """Carga el Excel exportado de Power BI."""
    print(f"📂 Leyendo: {ruta_excel}")
    
    if ruta_excel.endswith('.csv'):
        df = pd.read_csv(ruta_excel, sep=';', encoding='utf-8')
    else:
        if hoja:
            df = pd.read_excel(ruta_excel, sheet_name=hoja)
        else:
            df = pd.read_excel(ruta_excel)
    
    print(f"   ✅ {len(df)} registros cargados")
    return df


def seleccionar_columnas(df):
    """Selecciona y renombra las columnas necesarias."""
    mapeo = {
        'investigador': ['investigador', 'Investigador', 'INVESTIGADOR'],
        'grupo': ['grupo_investigacion', 'Grupo_Investigacion', 'grupo', 'Grupo'],
        'vicerrectorado': ['Vicerrectorado', 'vicerrectorado', 'VICERRECTORADO', 'silver_jerarquía.Vicerrectorado'],
        'unidad': ['Unidad_Investigacion', 'unidad_investigacion', 'Unidad', 'silver_jerarquía.Unidad_Investigacion'],
    }
    
    columnas_encontradas = {}
    for clave, posibles in mapeo.items():
        for col in df.columns:
            if col.strip() in posibles or col.strip().lower() in [p.lower() for p in posibles]:
                columnas_encontradas[clave] = col
                break
    
    if len(columnas_encontradas) < 4:
        print("   ⚠️ Columnas disponibles:", list(df.columns))
        print("   🔍 Buscando por palabras clave...")
        for clave, patron in [('investigador', 'investigador'), ('grupo', 'grupo'), 
                               ('vicerrectorado', 'vicerrectorado'), ('unidad', 'unidad')]:
            if clave not in columnas_encontradas:
                for col in df.columns:
                    if patron.lower() in col.lower():
                        columnas_encontradas[clave] = col
                        break
    
    df_out = df[[
        columnas_encontradas.get('investigador', df.columns[0]),
        columnas_encontradas.get('grupo', df.columns[1]),
        columnas_encontradas.get('vicerrectorado', df.columns[2]),
        columnas_encontradas.get('unidad', df.columns[3]),
    ]].copy()
    
    df_out.columns = ['investigador', 'grupo_investigacion', 'Vicerrectorado', 'Unidad_Investigacion']
    df_out = df_out.dropna(subset=['Vicerrectorado', 'Unidad_Investigacion'])
    df_out['grupo_investigacion'] = df_out['grupo_investigacion'].fillna('Sin grupo asignado')
    
    print(f"   ✅ {len(df_out)} registros después de limpiar")
    print(f"   👤 {df_out['investigador'].nunique()} investigadores únicos")
    print(f"   📁 {df_out['grupo_investigacion'].nunique()} grupos")
    
    return df_out


def convertir_a_csv_texto(df):
    """Convierte el DataFrame a texto CSV con formato."""
    lines = ["investigador;grupo_investigacion;Vicerrectorado;Unidad_Investigacion"]
    for _, row in df.iterrows():
        inv = str(row['investigador']).replace(';', ',').strip()
        grupo = str(row['grupo_investigacion']).replace(';', ',').strip()
        vic = str(row['Vicerrectorado']).replace(';', ',').strip()
        uni = str(row['Unidad_Investigacion']).replace(';', ',').strip()
        lines.append(f"{inv};{grupo};{vic};{uni}")
    return '\n'.join(lines)


def generar_html(csv_texto, total_investigadores, ruta_salida):
    """Inserta el CSV en la plantilla HTML y guarda."""
    
    html = r'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Grupos de Investigación · Universidad de Cuenca</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        :root {
            --bg: #F8F9FA; --primary: #003156; --accent: #A51008;
            --gray: #6F6F6F; --light-gray: #DADADA; --text: #111111; --white: #FFFFFF;
            --dpe-gold: #B8860B;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: var(--bg); color: var(--text);
            overflow: hidden; height: 100vh;
            display: flex; flex-direction: column; user-select: none;
        }
        header {
            text-align: center; padding: 18px 16px 6px; flex-shrink: 0; z-index: 10;
        }
        header h1 { font-size: 24px; font-weight: 300; color: var(--primary); letter-spacing: 2px; text-transform: uppercase; }
        header p { font-size: 10px; font-weight: 700; color: var(--gray); letter-spacing: 3px; text-transform: uppercase; }
        .total-inv { font-size: 11px; font-weight: 600; color: var(--gray); margin-top: 4px; letter-spacing: 1px; }
        .total-inv span { color: var(--primary); font-weight: 700; }
        #stats-panel {
            position: absolute; top: 100px; left: 50%; transform: translateX(-50%);
            display: flex; background: var(--white); border: 1px solid var(--light-gray);
            border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.06);
            z-index: 20; opacity: 0; transition: all 0.5s ease; pointer-events: none; overflow: hidden;
        }
        #stats-panel.visible { opacity: 1; pointer-events: auto; }
        #stats-panel .stat { text-align: center; padding: 12px 22px; }
        #stats-panel .stat:not(:last-child) { border-right: 1px solid var(--light-gray); }
        #stats-panel .stat .number { font-size: 22px; font-weight: 700; color: var(--primary); line-height: 1; }
        #stats-panel .stat .label { font-size: 9px; font-weight: 700; color: var(--gray); text-transform: uppercase; letter-spacing: 1px; margin-top: 3px; }
        
        /* CONTENEDOR PRINCIPAL QUE ENVUELVE SVG + DPE */
        #main-wrapper {
            flex: 1; display: flex; flex-direction: column; align-items: center;
            justify-content: center; position: relative; overflow: hidden; padding: 16px;
        }
        main { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; }
        main svg { width: 100%; height: 100%; max-width: 1000px; max-height: 70vh; }
        
        /* DPE BADGE FLOTANTE - Paralelo a los vicerrectorados */
        #dpe-flotante {
            position: absolute; bottom: 60px; left: 50%; transform: translateX(-50%);
            z-index: 15; opacity: 1; transition: opacity 0.5s ease;
            pointer-events: none; /* No interfiere con clics en el mapa */
        }
        #dpe-flotante.oculto { opacity: 0; }
        .dpe-badge {
            display: inline-flex; flex-direction: column; align-items: center; gap: 4px;
            padding: 10px 28px;
            background: var(--white);
            border: 2px dashed var(--dpe-gold);
            border-radius: 50px;
            box-shadow: 0 4px 16px rgba(184,134,11,0.08);
            text-align: center;
        }
        .dpe-badge .dpe-title {
            font-size: 12px; font-weight: 700; color: var(--dpe-gold);
            letter-spacing: 1px; text-transform: uppercase;
        }
        .dpe-badge .dpe-sub {
            font-size: 9px; color: var(--gray); font-weight: 500;
            letter-spacing: 0.5px;
        }
        
        #instruction {
            position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%);
            font-size: 11px; color: var(--gray); font-weight: 500; letter-spacing: 1px;
            transition: opacity 0.4s; pointer-events: none; z-index: 5;
        }
        /* PIE DE PÁGINA */
        footer {
            display: flex; flex-direction: column; align-items: center; gap: 10px;
            padding-bottom: 16px; flex-shrink: 0; z-index: 10;
        }
        /* BREADCRUMB CENTRADO Y COMPACTO */
        #breadcrumb {
            background: var(--white); border: 1px solid var(--light-gray); border-radius: 30px;
            padding: 8px 20px;
            display: inline-flex;
            align-items: center; gap: 2px;
            font-size: 11px; font-weight: 700; color: var(--gray);
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
            max-width: fit-content;
            margin: 0 auto;
        }
        #breadcrumb button {
            background: none; border: none; font-size: 11px; font-weight: 600; color: var(--gray);
            cursor: pointer; padding: 4px 8px; border-radius: 12px; transition: all 0.2s; font-family: inherit;
            white-space: nowrap;
        }
        #breadcrumb button:hover { color: var(--primary); background: rgba(0,49,86,0.04); }
        #breadcrumb button.current { color: var(--primary); }
        #breadcrumb .sep { color: var(--light-gray); pointer-events: none; }
        /* HUD INFERIOR SIMÉTRICO */
        .bottom-hud {
            display: flex; justify-content: center; align-items: center; gap: 30px;
            padding: 8px 20px; width: 100%; max-width: 1000px; margin: 0 auto;
        }
        .hud-badge {
            display: flex; align-items: center; gap: 8px; padding: 8px 18px;
            background: var(--white); border: 1px solid var(--light-gray); border-radius: 50px;
            font-size: 11px; color: var(--gray); box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .hud-badge .hud-label { font-weight: 700; color: var(--primary); }
        .hud-badge .hud-text { font-weight: 500; }
        .hud-right .hud-text { color: var(--accent); }
        /* SIDEBAR */
        #sidebar {
            position: fixed; top: 0; right: 0; height: 100%; width: 300px;
            background: var(--white); border-left: 1px solid var(--light-gray);
            box-shadow: -8px 0 30px rgba(0,0,0,0.08); transform: translateX(100%);
            transition: transform 0.4s ease; z-index: 50; display: flex; flex-direction: column;
        }
        #sidebar.open { transform: translateX(0); }
        #sidebar-header {
            padding: 20px; border-bottom: 1px solid var(--light-gray);
            display: flex; justify-content: space-between; align-items: flex-start; background: var(--bg);
        }
        #sidebar-header h3 { font-size: 14px; font-weight: 700; color: var(--primary); padding-right: 8px; }
        #sidebar-header button { background: none; border: none; font-size: 22px; color: var(--gray); cursor: pointer; line-height: 1; }
        #sidebar-body { padding: 20px; overflow-y: auto; flex: 1; }
        #sidebar-body p { font-size: 10px; font-weight: 700; color: var(--gray); text-transform: uppercase; letter-spacing: 2px; margin-bottom: 12px; }
        #sidebar-body ul { list-style: none; }
        #sidebar-body li {
            padding: 10px 12px; background: #F8F9FA; border: 1px solid var(--light-gray);
            border-radius: 8px; margin-bottom: 6px; font-size: 13px; font-weight: 500;
            display: flex; align-items: center; gap: 8px;
        }
        /* TOOLTIP */
        #tooltip {
            position: absolute; opacity: 0; pointer-events: none; background: var(--white);
            border: 1px solid var(--light-gray); border-radius: 8px; padding: 10px 14px;
            box-shadow: 0 8px 25px rgba(0,0,0,0.1); z-index: 100; font-size: 12px; transition: opacity 0.15s;
        }
        #tooltip .tt-name { font-weight: 700; color: var(--primary); margin-bottom: 2px; }
        #tooltip .tt-count { color: var(--gray); font-weight: 600; }
        @media (max-width: 768px) {
            header h1 { font-size: 20px; }
            #stats-panel .stat { padding: 10px 14px; }
            #stats-panel .stat .number { font-size: 18px; }
            #sidebar { width: 260px; }
        }
    </style>
</head>
<body>
    <header>
        <h1>Grupos de Investigación</h1>
        <p>Universidad de Cuenca · Ecuador</p>
        <p class="total-inv">Investigadores únicos en el catálogo: <span>##TOTAL_INVESTIGADORES##</span></p>
    </header>
    <div id="stats-panel">
        <div class="stat"><div class="number" id="stat-unidades">-</div><div class="label" id="stat-label-unidades">Unidades</div></div>
        <div class="stat"><div class="number" id="stat-grupos">-</div><div class="label">Grupos</div></div>
        <div class="stat"><div class="number" id="stat-investigadores">-</div><div class="label">Investigadores</div></div>
    </div>
    <div id="main-wrapper">
        <main>
            <svg id="canvas"></svg>
        </main>
        <!-- DPE: Badge flotante sobre el área del mapa, visible solo en vista raíz -->
        <div id="dpe-flotante">
            <div class="dpe-badge">
                <div class="dpe-title">⚡ Dirección de Proyectos Estratégicos</div>
                <div class="dpe-sub">Unidad Transversal │ Coordinación inter‑vicerrectorados │ Apoyo a formulación de proyectos</div>
            </div>
        </div>
        <div id="instruction">Haz clic en un círculo para explorar</div>
    </div>
    <footer>
        <div id="breadcrumb"><button class="current">Universidad de Cuenca</button></div>
        <div id="bottom-hud" class="bottom-hud">
            <div class="hud-badge hud-left">
                <span class="hud-label">Fuente:</span>
                <span class="hud-text">Pure, Scopus & Elsevier Fingerprint Engine™ │ Vicerrectorado de Investigación</span>
            </div>
            <div class="hud-badge hud-right">
                <span class="hud-label">Elaborado por:</span>
                <span class="hud-text">Karen Michelle Luzuriaga</span>
            </div>
        </div>
    </footer>
    <div id="sidebar">
        <div id="sidebar-header"><h3 id="sidebar-title">Grupo</h3><button id="close-sidebar">&times;</button></div>
        <div id="sidebar-body"><p>Investigadores del Grupo</p><ul id="sidebar-list"></ul></div>
    </div>
    <div id="tooltip"></div>
    <script id="csv-data" type="text/csv">
''' + csv_texto + r'''
    </script>
    <script>
        function loadData() {
            const csvElement = document.getElementById('csv-data');
            if (csvElement && csvElement.textContent.trim()) {
                return buildHierarchyFromCSV(csvElement.textContent.trim());
            }
            return null;
        }
        function buildHierarchyFromCSV(csvText) {
            const lines = csvText.trim().split('\n');
            if (lines.length < 2) return null;
            const header = lines[0].split(';');
            const idxInv = header.findIndex(h => h.trim().toLowerCase().includes('investigador'));
            const idxGrupo = header.findIndex(h => h.trim().toLowerCase().includes('grupo'));
            const idxVic = header.findIndex(h => h.trim().toLowerCase().includes('vicerrectorado'));
            const idxUni = header.findIndex(h => h.trim().toLowerCase().includes('unidad'));
            const root = { name: "Universidad de Cuenca", children: [] };
            const vMap = {};
            for (let i = 1; i < lines.length; i++) {
                const line = lines[i].trim();
                if (!line) continue;
                const cols = line.split(';');
                if (cols.length < 4) continue;
                const investigador = cols[idxInv]?.trim() || '';
                const grupo = cols[idxGrupo]?.trim() || 'Sin grupo asignado';
                const vicerrectorado = cols[idxVic]?.trim() || '';
                const unidad = cols[idxUni]?.trim() || '';
                if (!vicerrectorado || !unidad) continue;
                if (!vMap[vicerrectorado]) vMap[vicerrectorado] = { name: vicerrectorado, color: vicerrectorado.includes('Académico') ? '#003156' : '#A51008', children: {} };
                if (!vMap[vicerrectorado].children[unidad]) vMap[vicerrectorado].children[unidad] = { name: unidad, children: {} };
                if (!vMap[vicerrectorado].children[unidad].children[grupo]) vMap[vicerrectorado].children[unidad].children[grupo] = { name: grupo, investigadores: new Set() };
                if (investigador) vMap[vicerrectorado].children[unidad].children[grupo].investigadores.add(investigador);
            }
            root.children = Object.values(vMap).map(v => ({ name: v.name, color: v.color, children: Object.values(v.children).map(u => ({ name: u.name, children: Object.values(u.children).map(g => ({ name: g.name, value: g.investigadores.size || 1, investigadores: Array.from(g.investigadores) })) })) }));
            return root.children.length > 0 ? root : null;
        }
        
        function init() {
            const data = loadData();
            if (!data) { document.getElementById('instruction').textContent = 'No se encontraron datos.'; return; }
            
            const width = 1000, height = 600;
            const svg = d3.select("#canvas").attr("viewBox", `0 0 ${width} ${height}`).on("click", (event) => { if (event.target === svg.node()) zoom(root); });
            const defs = svg.append("defs");
            const filterShadow = defs.append("filter").attr("id", "shadow").attr("height", "140%");
            filterShadow.append("feDropShadow").attr("dx", 0).attr("dy", 4).attr("stdDeviation", 10).attr("flood-opacity", 0.08);
            const gradBlue = defs.append("linearGradient").attr("id", "gradBlue").attr("x1","0%").attr("y1","0%").attr("x2","100%").attr("y2","100%");
            gradBlue.append("stop").attr("offset","0%").attr("stop-color","#004B82"); gradBlue.append("stop").attr("offset","100%").attr("stop-color","#003156");
            const gradRed = defs.append("linearGradient").attr("id","gradRed").attr("x1","0%").attr("y1","0%").attr("x2","100%").attr("y2","100%");
            gradRed.append("stop").attr("offset","0%").attr("stop-color","#C41E14"); gradRed.append("stop").attr("offset","100%").attr("stop-color","#A51008");
            
            const root = d3.hierarchy(data);
            root.leaves().forEach(d => { d.realValue = d.data.investigadores ? d.data.investigadores.length : (d.data.value || 1); });
            const vAcad = root.children.find(c => c.data.name.includes("Académico"));
            const vInv = root.children.find(c => c.data.name.includes("Investigación"));
            if (vAcad) vAcad.leaves().forEach(d => d.value = d.realValue * (100 / (d3.sum(vAcad.leaves(), l => l.realValue) || 1)));
            if (vInv) vInv.leaves().forEach(d => d.value = d.realValue * (100 / (d3.sum(vInv.leaves(), l => l.realValue) || 1)));
            root.eachAfter(d => { if (d.children) d.value = d3.sum(d.children, c => c.value); });
            root.sort((a, b) => b.value - a.value);
            
            const pack = d3.pack()
                .size([width, height])
                .padding(d => {
                    if (d.depth === 0) return 0;
                    if (d.depth === 1) return 8;
                    if (d.depth === 2) return 4;
                    return 2;
                });
                
            const nodes = pack(root).descendants();
            let focus = root, view;
            const nodeGroup = svg.append("g");
            const circle = nodeGroup.selectAll("circle").data(nodes.slice(1)).join("circle")
                .attr("fill", d => d.depth === 1 ? (d.data.color === "#003156" ? "url(#gradBlue)" : "url(#gradRed)") : "white")
                .attr("stroke", d => d.depth > 1 ? (d.parent?.data?.color || "#DADADA") : "none")
                .attr("stroke-width", d => d.depth > 1 ? 1.5 : 0)
                .style("filter", d => d.depth === 1 ? "url(#shadow)" : "none")
                .style("opacity", d => d.depth === 1 ? 1 : 0)
                .style("pointer-events", d => d.depth === 1 ? "all" : "none")
                .style("cursor", "pointer")
                .on("click", (event, d) => { event.stopPropagation(); if (d.children && d.depth <= 2) zoom(d); else { circle.attr("stroke-width", c => c.depth > 1 ? 1.5 : 0); d3.select(event.currentTarget).attr("stroke","#111111").attr("stroke-width",2.5); openSidebar(d.data); } })
                .on("mouseover", (event, d) => { const visible = (focus === root && d.depth === 1) || d.parent === focus; if (visible) { d3.select("#tooltip").style("opacity",1).html(`<div class="tt-name">${d.data.name}</div><div class="tt-count">${d3.sum(d.leaves(), l => l.realValue)} Investigadores</div>`).style("left",(event.pageX+15)+"px").style("top",(event.pageY-15)+"px"); } })
                .on("mouseout", () => d3.select("#tooltip").style("opacity",0));
            
            const label = nodeGroup.selectAll("g.label-group")
                .data(nodes.slice(1))
                .join("g")
                .attr("class", "label-group")
                .style("opacity", d => d.depth === 1 ? 1 : 0)
                .style("pointer-events","none");

            label.each(function(d) {
                const el = d3.select(this);
                el.selectAll("*").remove();
                let name = d.data.name;
                const isDepth1 = d.depth === 1;
                const isDepth2 = d.depth === 2;
                if (isDepth2) {
                    name = name.replace(/^(Facultad de\s+|Departamento de\s+|Depto\.\s+de\s+|Departamento Interdisciplinario de\s+)/i, "");
                }
                let maxLineLength = Math.max(14, Math.floor(d.r * 0.32));
                if (isDepth1) maxLineLength = 28; 
                const words = name.split(/\s+/);
                let lines = [];
                let currentLine = "";
                words.forEach(word => {
                    if ((currentLine + " " + word).trim().length <= maxLineLength) {
                        currentLine = (currentLine + " " + word).trim();
                    } else {
                        if (currentLine) lines.push(currentLine);
                        currentLine = word;
                    }
                });
                if (currentLine) lines.push(currentLine);
                if (lines.length > 3) {
                    lines = [lines[0], lines[1], lines[2] + "..."];
                }
                let fontSizeNum = Math.min(isDepth1 ? 18 : (isDepth2 ? 13 : 11), d.r * 0.25);
                fontSizeNum = Math.max(isDepth1 ? 14 : (isDepth2 ? 9.5 : 8), fontSizeNum);
                const fontSize = fontSizeNum + "px";
                const lineHeight = fontSizeNum * 1.15;
                const totalHeight = lines.length * lineHeight;
                const startY = isDepth2 ? (-(totalHeight / 2) + lineHeight / 2) : (-(totalHeight / 2) + lineHeight / 2 - 2);
                const textNode = el.append("text")
                    .attr("text-anchor", "middle")
                    .attr("fill", isDepth1 ? "white" : "#111111")
                    .style("font-size", fontSize)
                    .style("font-weight", "700")
                    .style("font-family", "inherit");
                lines.forEach((line, i) => {
                    textNode.append("tspan")
                        .attr("x", 0)
                        .attr("y", startY + (i * lineHeight))
                        .text(line);
                });
                if (!isDepth2) {
                    const realCount = d3.sum(d.leaves(), l => l.realValue);
                    el.append("text")
                        .attr("text-anchor", "middle")
                        .attr("y", (totalHeight / 2) + (isDepth1 ? 15 : 10))
                        .attr("fill", isDepth1 ? "rgba(255,255,255,0.85)" : "#6F6F6F")
                        .style("font-size", (fontSizeNum * 0.8) + "px")
                        .style("font-weight", "600")
                        .text(`${realCount} inv.`);
                }
            });

            function zoom(d) { 
                focus = d; 
                const zp = focus.depth === 0 ? focus.r * 2.05 : focus.depth === 1 ? focus.r * 2.15 : focus.r * 2.2; 
                const t = svg.transition().duration(900); 
                t.tween("zoom", () => { 
                    const i = d3.interpolateZoom(view, [focus.x, focus.y, zp]); 
                    return t2 => zoomTo(i(t2)); 
                }); 
                circle.style("pointer-events", d => focus === root ? (d.depth === 1 ? "all" : "none") : (d.parent === focus ? "all" : "none")); 
                circle.transition(t).style("opacity", d => focus === root ? (d.depth === 1 ? 1 : 0) : (d === focus || d.parent === focus ? 1 : 0)); 
                label.transition(t).style("opacity", d => focus === root ? (d.depth === 1 ? 1 : 0) : (d.parent === focus ? 1 : 0)); 
                updateUI(focus); 
            }
            
            function zoomTo(v) { view = v; const k = height/v[2]; const tx = d => (d.x-v[0])*k+width/2; const ty = d => (d.y-v[1])*k+height/2; circle.attr("transform", d => `translate(${tx(d)},${ty(d)})`).attr("r", d => d.r*k); label.attr("transform", d => `translate(${tx(d)},${ty(d)})`); }
            function updateUI(node) {
                const isRoot = node === root;
                // Mostrar/ocultar DPE solo en vista raíz
                const dpe = document.getElementById("dpe-flotante");
                if (dpe) dpe.classList.toggle("oculto", !isRoot);
                document.getElementById("instruction").style.opacity = isRoot ? "1" : "0";
                const stats = document.getElementById("stats-panel");
                stats.classList.toggle("visible", !isRoot);
                if (!isRoot) {
                    document.getElementById("stat-unidades").textContent = node.children ? node.children.length : 1;
                    document.getElementById("stat-grupos").textContent = node.leaves().length;
                    document.getElementById("stat-investigadores").textContent = d3.sum(node.leaves(), d => d.realValue);
                    document.getElementById("stat-label-unidades").textContent = node.depth === 1 ? (node.data.name.includes("Académico") ? "Facultades" : "Deptos.") : "Grupos";
                }
                const bc = document.getElementById("breadcrumb");
                bc.innerHTML = "";
                const path = node.ancestors().reverse();
                path.forEach((n,i) => {
                    if(i>0){const s=document.createElement("span");s.className="sep";s.textContent="›";bc.appendChild(s);}
                    const b=document.createElement("button");
                    b.textContent=n.depth===0?"Universidad":n.data.name.length>25?n.data.name.slice(0,23)+"…":n.data.name;
                    if(i===path.length-1)b.classList.add("current");
                    b.onclick=(e)=>{e.stopPropagation();zoom(n);closeSidebar();};
                    bc.appendChild(b);
                });
            }
            function openSidebar(data) { document.getElementById("sidebar-title").textContent = data.name; const list = document.getElementById("sidebar-list"); list.innerHTML = ""; if (data.investigadores && data.investigadores.length > 0) { data.investigadores.sort().forEach(name => { const li = document.createElement("li"); li.innerHTML = `<span style="color:#003156;font-weight:700;">▸</span> ${name}`; list.appendChild(li); }); } else { const li = document.createElement("li"); li.textContent = "Sin investigadores asignados"; li.style.fontStyle = "italic"; li.style.color = "#6F6F6F"; list.appendChild(li); } document.getElementById("sidebar").classList.add("open"); }
            function closeSidebar() { document.getElementById("sidebar").classList.remove("open"); circle.attr("stroke-width", c => c.depth > 1 ? 1.5 : 0).attr("stroke", c => c.depth > 1 ? (c.parent?.data?.color || "#DADADA") : "none"); }
            document.getElementById("close-sidebar").onclick = closeSidebar;
            zoomTo([root.x, root.y, root.r * 2]);
            updateUI(root);
        }
        init();
    </script>
</body>
</html>'''
    
    html = html.replace('##TOTAL_INVESTIGADORES##', str(total_investigadores))
    
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n🎉 HTML generado: {ruta_salida}")
    return ruta_salida


def main():
    print("=" * 50)
    print("   GENERADOR DE MAPA MENTAL - UCUENCA")
    print("=" * 50)
    print()
    
    df = cargar_datos_excel(RUTA_EXCEL, HOJA)
    df_limpio = seleccionar_columnas(df)
    csv_texto = convertir_a_csv_texto(df_limpio)
    total_investigadores = df_limpio['investigador'].nunique()
    print(f"🧮 Total investigadores únicos (para el encabezado): {total_investigadores}")
    
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    ruta_html = os.path.join(CARPETA_SALIDA, NOMBRE_HTML)
    generar_html(csv_texto, total_investigadores, ruta_html)
    
    print(f"\n🚀 Abriendo en el navegador...")
    os.startfile(ruta_html)
    
    print("\n✅ ¡Listo! Cada vez que ejecutes este script:")
    print("   1. Lee los datos actualizados")
    print("   2. Genera un nuevo HTML con DPE flotante paralela a los círculos")
    print("   3. Lo abre automáticamente")


if __name__ == '__main__':
    main()