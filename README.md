# 🧠 OCA Migration Analyzer (`oca-mig-analyzer.py`)
Script de apoyyo para las migraciones de Odoo enterprise. Cuando Odoo S.A. migra una base de datos, solo hace la parte de Odoo community y Odoo enterprise. Todos los módulos de OCA son ignorados.

Este script analiza módulos de Odoo de la comunidad OCA, buscando carpetas `migrations/` en las ramas especificadas, y genera un informe detallado por repositorio y módulo.

También tiene la capacidad de guardar las carpetas **migrations/** de cada módulo instalado, y por versión de Odoo, facilitando un análisis previo a realizar la migración de OCA de manera manual.

---

## 🚀 Funcionalidades

- ✅ Analiza módulos instalados desde un CSV
- 🔎 Detecta si existen `migrations/` por versión
- 💾 Opción para copiar carpetas `migrations` encontradas
- 🧪 Modo `--dry-run` para simular sin escribir
- 📝 Genera logs, CSVs y reportes `.txt`
- 🧹 Organiza todo en la carpeta `oca-collector/`

---

## 🔧 Cómo usar

```bash
python3 oca-mig-analyzer.py -s <versión_origen> -e <versión_destino> -f <archivo_csv>
```

#### 📌 Argumentos obligatorios

| Opción           | Descripción                                                    |
|------------------|----------------------------------------------------------------|
| `-s`, `--start`  | Versión inicial de Odoo a analizar (ej: `14.0`)                |
| `-e`, `--end`    | Versión final de Odoo a analizar (ej: `17.0`)                  |
| `-f`, `--file`   | Ruta al archivo CSV con los módulos instalados de OCA         |


#### 🧩 Opciones adicionales

| Opción                | Descripción                                                                 |
|-----------------------|-----------------------------------------------------------------------------|
| `--save-migrations`   | Si se activa, guarda las carpetas `migrations/` encontradas por módulo      |
| `--dry-run`           | Simula la ejecución sin clonar ni escribir archivos (útil para validar CSV)|
| `--log <archivo>`     | Especifica un archivo de log. Se guarda dentro de `oca-collector/`          |


## 📦 Formato del CSV
Partimos de un csv con todos los módulos de OCA Instalados.

Pordemos conseguirlo filtrando los módulos instalados cuyo **Autor** contiene OCA y agrupando por **Sitio Web**. Después seleccionamos todos los repositorios y exportamos.
Debe solo dos **dos columnas**, interpretada la primera como nombre de Módulo y la otra como la dirección a OCA: Por ejemplo,"Nombre técnico" y "Sitio web".


**Ejemplo:**

```csv
stock_picking_batch, https://github.com/OCA/stock-logistics-workflow
base_report_to_printer_mail, https://github.com/OCA/report-print-send
```

## 📂 Estructura de salida
```
oca-collector/
├── repos/                          # Repositorios clonados por rama
│   └── web/14.0/module_name/
├── migrations/                    # Carpeta migrations copiadas
│   └── web/14.0_module_name/
├── oca-analysis-full.txt          # Análisis completo por repo
├── oca-analysis-resume.txt        # Solo resumen de módulos a migrar
├── oca-analysis-full.csv          # Detalles completos (módulo, versión, estado)
├── oca-analysis-resume.csv        # Solo módulos con migrations y errores
├── oca-errors.csv                 # Errores de lectura de CSV
├── mi_log.txt                     # (si usaste --log)

```

# Ejemplos de uso
⚙️ Uso básico
```bash
python3 oca-mig-analyzer.py -s 14.0 -e 17.0 -f modulos.csv --save-migrations

```
🧪 Simulación (sin descargar, sin copiar)
```bash
python3 oca-mig-analyzer.py -s 14.0 -e 17.0 -f modulos.csv --dry-run
```

📝 Log personalizado

```bash
python3 oca-mig-analyzer.py -s 14.0 -e 17.0 -f modulos.csv --log analisis.log
```
