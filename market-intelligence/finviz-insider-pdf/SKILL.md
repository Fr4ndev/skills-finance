---
name: finviz-insider-pdf
description: Análisis de rotación sectorial con datos reales de Insider Trading de Finviz. Extrae operaciones de directivos, calcula scores de señal, agrega flujos por sector y genera un dashboard PDF visual con gráficos y recomendaciones. Úsalo cuando el usuario pida analizar insider trading, rotación de capital, o generar reportes de Finviz en PDF.
---

# Finviz Insider Trading Dashboard (PDF)

Esta skill permite extraer datos en tiempo real de las operaciones de insiders (compras y ventas de directivos y grandes accionistas) desde Finviz, analizarlos mediante un sistema de scoring de señal y generar un dashboard visual en formato PDF.

## 🎯 Capacidades

1. **Extracción de Datos:** Scrapea las últimas transacciones reportadas a la SEC (Form 4) directamente desde Finviz.
2. **Clasificación Sectorial:** Mapea automáticamente los tickers a sectores clave (Semiconductores, Software, Energía, Biotecnología, etc.).
3. **Scoring de Señal:** Evalúa la convicción de cada operación basándose en el rol del insider, el tamaño de la transacción y el tipo (discrecional vs. plan preestablecido).
4. **Dashboard PDF Visual:** Genera un reporte profesional con KPIs, gráficos (barras, donut, histogramas) e insights accionables generados automáticamente.

## 🛠️ Cómo Usar la Skill

El flujo de trabajo principal se ejecuta a través de un script de Python consolidado que realiza la extracción, el análisis y la generación del PDF en un solo paso.

### Requisitos Previos

Asegúrate de que las dependencias estén instaladas antes de ejecutar los scripts:

```bash
sudo pip3 install requests beautifulsoup4 pandas matplotlib reportlab yfinance
```

### Ejecución Básica

Para generar un reporte con los datos más recientes (1 página de Finviz, ~100 transacciones):

```bash
python3 /home/ubuntu/skills/finviz-insider-pdf/scripts/run_pipeline.py --output /home/ubuntu/insider_dashboard.pdf
```

### Opciones Avanzadas

El script `run_pipeline.py` soporta varios argumentos para personalizar el análisis:

- `--pages N`: Número de páginas de Finviz a descargar (cada página tiene 100 transacciones). Útil para capturar una ventana de tiempo más amplia.
- `--filter [all|buy|sale]`: Filtra por tipo de transacción desde el origen.
- `--enrich`: Usa la API de `yfinance` para clasificar sectores de tickers desconocidos (puede ralentizar la ejecución).
- `--output PATH`: Ruta donde se guardará el PDF generado.
- `--json PATH`: Guarda los datos crudos y procesados en un archivo JSON para inspección manual.

**Ejemplo de análisis profundo (3 páginas, con enriquecimiento sectorial):**

```bash
python3 /home/ubuntu/skills/finviz-insider-pdf/scripts/run_pipeline.py --pages 3 --enrich --output /home/ubuntu/insider_deep_analysis.pdf --json /home/ubuntu/insider_data.json
```

## 🧠 Metodología de Análisis

### 1. Clasificación de Señales (Scoring)

Cada transacción recibe un score de 0 a 100 basado en la metodología del "0,1%":

- **Tipo de Transacción:** Las compras directas (Buy) tienen el mayor peso. Las ventas (Sale) son señales fuertes, pero las ventas propuestas (Proposed Sale) bajo planes 10b5-1 tienen menor convicción.
- **Rol del Insider:** Los CEOs, Fundadores y Presidentes aportan mayor peso a la señal que los oficiales de menor rango.
- **Tamaño Relativo:** Se evalúa el valor en USD y el porcentaje de acciones transaccionadas respecto al total de la posición del insider.

Las señales se etiquetan como:
- 🔴 **MÁXIMA** (Score ≥ 75): Alta convicción.
- 🟡 **FUERTE** (Score 55-74): Considerar acción.
- 🔵 **MODERADA** (Score 35-54): Contexto necesario.
- ⚪ **DÉBIL** (Score < 35): Ruido o planes programados.

### 2. Rotación Sectorial

El capital institucional y de insiders rota entre sectores según el ciclo económico. El script agrega los flujos netos (Compras - Ventas) por sector para identificar:
- **Inflows (Entradas):** Sectores infravalorados o con catalizadores próximos donde los insiders están acumulando.
- **Outflows (Salidas):** Sectores con valoraciones exigentes donde los insiders están tomando beneficios.

## 📂 Estructura de la Skill

- `scripts/finviz_scraper.py`: Lógica de scraping, mapeo sectorial y cálculo de scores.
- `scripts/generate_pdf.py`: Motor de renderizado visual usando `matplotlib` y `reportlab`.
- `scripts/run_pipeline.py`: Orquestador principal que une la extracción y la generación del PDF.

## 💡 Entrega al Usuario

Cuando el usuario solicite un análisis de insider trading:
1. Ejecuta el pipeline con los parámetros adecuados (por defecto 1 o 2 páginas).
2. Revisa que el PDF se haya generado correctamente.
3. Utiliza la herramienta `message` (tipo `result`) para enviar el PDF generado como adjunto, acompañado de un breve resumen de los insights más relevantes encontrados.
