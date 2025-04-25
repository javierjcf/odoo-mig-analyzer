# 🧠 Odoo Migration Analyzer (`odoo-mig-analyzer.py`)
Script de apoyo para las migraciones de Odoo enterprise. Cuando Odoo S.A. migra una base de datos, solo hace la parte de Odoo community y Odoo enterprise. Todos los módulos de OCA son ignorados.

Este script analiza módulos de Odoo, incluidos los de la comunidad OCA, buscando carpetas `migrations/` en las ramas especificadas, y genera un informe detallado por repositorio y módulo.

También tiene la capacidad de guardar las carpetas **migrations/** de cada módulo instalado, y por versión de Odoo, facilitando un análisis previo a realizar la migración de OCA de manera manual.

---

## 🚀 Funcionalidades

- ✅ Analiza módulos instalados desde un CSV
- 🔎 Detecta si existen `migrations/` por versión
- 💾 Opción para copiar carpetas `migrations` encontradas
- 🧪 Modo `--dry-run` para simular sin escribir
- 📝 Genera logs, CSVs y reportes `.txt`
- 🧹 Organiza todo en la carpeta `analysis-collector/`

---

## 🔧 Cómo usar

```bash
python3 odoo-mig-analyzer.py -s <versión_origen> -e <versión_destino> -f <archivo_csv>
```

#### 📌 Argumentos obligatorios

| Opción           | Descripción                                                    |
|------------------|----------------------------------------------------------------|
| `-s`, `--start`  | Versión inicial de Odoo a analizar (ej: `12.0`)                |
| `-e`, `--end`    | Versión final de Odoo a analizar (ej: `18.0`)                  |
| `-f`, `--file`   | Ruta al archivo CSV con los módulos instalados                 |


#### 🧩 Opciones adicionales

| Opción                | Descripción                                                                 |
|-----------------------|-----------------------------------------------------------------------------|
| `--save-migrations`   | Si se activa, guarda las carpetas `migrations/` encontradas por módulo      |
| `--dry-run`           | Simula la ejecución sin clonar ni escribir archivos (útil para validar CSV)|
| `--log <archivo>`     | Especifica un archivo de log. Se guarda dentro de `analysis-collector/`          |
| `--comapact`     | Modo compact: Las ramas de cáda mmódulo se rescriben en la misma líena          |


## 📦 Formato del CSV
Partimos de un csv con todos los módulos de instalados a analizar. Normalmente se usará
solo para ver los módulos de OCA.

Pordemos conseguirlo filtrando los módulos instalados cuyo **Autor** contiene OCA y agrupando por **Sitio Web**. Después seleccionamos todos los repositorios y exportamos.
Debe solo dos **dos columnas**, interpretada la primera como nombre de Módulo y la otra como la dirección a OCA: Por ejemplo,"Nombre técnico" y "Sitio web".

Lo ideal es No tener las cabeceras en la primera línea, para que no lo detecte como error.
Hay que revisar que la URL de OCa es correcta, ya que la exportación de Sitio Web no siempre es precisa.

## Limitaciones
- Los módulos renombrados no se detectan
- Si un módulo se mueve de un repositorio a otro lo detectará como no encontrado en el repositorio original
- No tienen en cuenta los PR de OCA, es decir puede decir que no se encontró un módulo en una versión pero si hay PR


**Ejemplo:**

```csv
stock_picking_batch, https://github.com/OCA/stock-logistics-workflow
base_report_to_printer_mail, https://github.com/OCA/report-print-send
```

## 📂 Estructura de salida
```
analysis-collector/
├── repos/                          # Repositorios clonados por rama
│   └── web/14.0/module_name/
├── migrations/                    # Carpeta migrations copiadas
│   └── web/14.0_module_name/
│
├── analysis_csv/                    # Carpeta migrations copiadas
│   └──analysis-by-report.csv        # Análisis agrupado por repositorio
│   └──analysis-migration.csv        # Módulos a migrar
│   └──analysis-not-found.csv        # Módulos que desaparecen en alguna 
│  
├── analysis_txt/                    # Carpeta migrations copiadas
│   └─analysis-full.csv              # Detalles completos (módulo, versión, estado)
│   └─analysis-full.txt              # Módulos a migrar
│   └─analysis-not-found.txt         # Módulos que desaparecen en alguna version
├── analysis-errors.csv              # Errores de lectura de CSV
│  
├── mi_log.txt                       # (si usaste --log)

```

# Ejemplos de uso
⚙️ Uso básico
```bash
python3 odoo-mig-analyzer.py -s 14.0 -e 17.0 -f modulos.csv --save-migrations

```
🧪 Simulación (sin descargar, sin copiar)
```bash
python3 odoo-mig-analyzer.py -s 14.0 -e 17.0 -f modulos.csv --dry-run
```

📝 Log personalizado

```bash
python3 odoo-mig-analyzer.py -s 14.0 -e 17.0 -f modulos.csv --log analisis.log
```
