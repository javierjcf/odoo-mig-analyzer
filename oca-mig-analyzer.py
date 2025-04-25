#!/usr/bin/env python3
import argparse
import csv
import os
import subprocess
import sys
import shutil
import requests
import datetime
from urllib.parse import urlparse
from collections import defaultdict
import signal

signal.signal(signal.SIGINT, signal.default_int_handler)

# === Rutas generales ===
BASE_DIR = "oca-collector"

CLONES_DIR = os.path.join(BASE_DIR, "repos")
MIGRATIONS_DIR = os.path.join(BASE_DIR, "migrations")
ANALYSIS_TXT_DIR = os.path.join(BASE_DIR, "analysis_txt")
ANALYSIS_CSV_DIR = os.path.join(BASE_DIR, "analysis_csv")

TXT_SUMMARY = os.path.join(ANALYSIS_TXT_DIR, "oca-analysis-full.txt")
TXT_MIGRATION = os.path.join(ANALYSIS_TXT_DIR, "oca-analysis-migration.txt")
TXT_NOT_FOUND = os.path.join(ANALYSIS_TXT_DIR, "oca-analysis-not-found.txt")

CSV_FULL = os.path.join(ANALYSIS_CSV_DIR, "oca-analysis-full.csv")
CSV_MIGRATION = os.path.join(ANALYSIS_CSV_DIR, "oca-analysis-migration.csv")
CSV_NOT_FOUND = os.path.join(ANALYSIS_CSV_DIR, "oca-analysis-not-found.csv")
CSV_BY_REPORT = os.path.join(ANALYSIS_CSV_DIR, "oca-analysis-by-report.csv")
LOG_FILE = None

def log(msg):
    print(msg)
    if LOG_FILE:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] {msg}\n")

def run_git_cmd(cmd, cwd=None):
    try:
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        subprocess.run(["git"] + cmd, cwd=cwd, check=False, env=env)
        return True
    except subprocess.CalledProcessError:
        return False
    except KeyboardInterrupt:
        log("🛑 Ctrl+C durante operación Git.")
        raise

def repo_exists(repo_url):
    try:
        response = requests.head(repo_url.replace(".git", ""), timeout=5)
        return response.status_code == 200
    except KeyboardInterrupt:
        log("🛑 Interrupción durante verificación de repositorio.")
        raise
    except Exception as e:
        log(f"⚠️ Error al verificar repo: {e}")
        return False

def extract_repo_name(url):
    try:
        return urlparse(url).path.strip("/").split("/")[1]
    except:
        return None

def ensure_repo_cloned(repo_url, repo_dir, branch):
    if os.path.exists(repo_dir):
        log(f"🔁 Actualizando rama {branch} en {repo_dir}")
        run_git_cmd(["fetch", "origin", branch], cwd=repo_dir)
        run_git_cmd(["checkout", branch], cwd=repo_dir)
        run_git_cmd(["reset", "--hard", f"origin/{branch}"], cwd=repo_dir)
    else:
        log(f"⬇️ Clonando {repo_url} @ {branch}")
        run_git_cmd(["clone", "--depth", "1", "--branch", branch, "--filter=blob:none", repo_url, repo_dir])

def save_migrations(repo, branch, module, src_root):
    src = os.path.join(src_root, module, "migrations")
    if not os.path.isdir(src):
        return
    dest_repo = os.path.join(MIGRATIONS_DIR, repo)
    os.makedirs(dest_repo, exist_ok=True)
    dest = os.path.join(dest_repo, f"{branch}_{module}")
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(src, dest)

def log_repo_modules(repo, branch, repo_dir, modules):
    modulos_en_repo = {
        name for name in os.listdir(repo_dir)
        if os.path.isdir(os.path.join(repo_dir, name)) and not name.startswith('.')
    } if os.path.isdir(repo_dir) else set()

    modulos_csv = set(mod for mod, _, _ in modules)

    instalados = [m for m in modulos_csv if m in modulos_en_repo]
    no_encontrados = [m for m in modulos_csv if m not in modulos_en_repo]
    no_instalados = [m for m in sorted(modulos_en_repo - modulos_csv)]

    log(f"\n📦 Repositorio: {repo} @ {branch}")
    log("=" * 60)

    if instalados:
        log("\n✅ INSTALADOS (definidos en CSV y presentes en repo):")
        for m in sorted(instalados):
            log(f"    🔍 {m} @ {branch}")

    if no_encontrados:
        log("\n💨 NO ENCONTRADOS (en CSV, no están en el repo):")
        for m in sorted(no_encontrados):
            log(f"    🔍 {m} @ {branch}")

    return instalados, no_encontrados

def parse_arguments():
    parser = argparse.ArgumentParser(description="Analiza módulos de OCA para detectar migrations")
    parser.add_argument("-s", "--start", required=True, help="Versión inicial, ej: 14.0")
    parser.add_argument("-e", "--end", required=True, help="Versión final, ej: 17.0")
    parser.add_argument("-f", "--file", required=True, help="Archivo CSV con módulos")
    parser.add_argument("--save-migrations", action="store_true", help="Guardar carpetas migrations encontradas")
    parser.add_argument("--dry-run", action="store_true", help="Simula sin escribir archivos ni clonar")
    parser.add_argument("--log", help="Archivo log (se guarda en oca-collector/)")
    parser.add_argument("--compact", action="store_true", help="Usar formato compacto @version para los informes")
    return parser.parse_args()

def setup_directories():
    os.makedirs(BASE_DIR, exist_ok=True)
    os.makedirs(ANALYSIS_TXT_DIR, exist_ok=True)
    os.makedirs(ANALYSIS_CSV_DIR, exist_ok=True)
    os.makedirs(CLONES_DIR, exist_ok=True)
    os.makedirs(MIGRATIONS_DIR, exist_ok=True)

def parse_csv(file):
    repos_data = defaultdict(list)
    csv_errors = []
    with open(file, newline='') as csvfile:
        reader = csv.reader(csvfile)
        for line_num, row in enumerate(reader, start=1):
            if len(row) < 2:
                log(f"❌ Fila {line_num} inválida: {row}")
                csv_errors.append((line_num, row))
                continue
            module, url = row[0].strip(), row[1].strip()
            repo = extract_repo_name(url)
            if not repo:
                log(f"❌ Fila {line_num}, URL inválida: {url}")
                csv_errors.append((line_num, row))
                continue
            repos_data[repo].append((module, url, line_num))
    return repos_data, csv_errors

def analyze_repos(args, repos_data, csv_errors):
    start_v = int(args.start.split('.')[0])
    end_v = int(args.end.split('.')[0])
    branches = [f"{v}.0" for v in range(start_v, end_v + 1)]

    resumen = {}
    rows_full, rows_resume = [], []

    for repo, modules in repos_data.items():
        resumen[repo] = {
            "con_migrations": defaultdict(list),
            "sin": set(),
            "errores": [],
            "no_encontrados": defaultdict(list)
        }

        for branch in branches:
            repo_url = f"https://github.com/OCA/{repo}.git"
            repo_dir = os.path.join(CLONES_DIR, repo, branch)

            if not repo_exists(repo_url):
                log(f"❌ Repositorio no encontrado: {repo_url}")
                for mod, _, line in modules:
                    resumen[repo]["errores"].append(f"{mod} @ {branch} (repo no encontrado)")
                    rows_full.append([repo, mod, "Error", f"{branch}: repo no encontrado", line])
                    csv_errors.append((line, [mod, repo_url]))
                break

            if not args.dry_run:
                ensure_repo_cloned(repo_url, repo_dir, branch)

            _, no_encontrados = log_repo_modules(repo, branch, repo_dir, modules)

            for module, _, line in modules:
                if module in no_encontrados:
                    resumen[repo]["no_encontrados"][module].append(branch)
                    continue

                mod_path = os.path.join(repo_dir, module, "migrations")
                if os.path.isdir(mod_path):
                    resumen[repo]["con_migrations"][module].append(branch)
                    if args.save_migrations:
                        save_migrations(repo, branch, module, repo_dir)
                    rows_full.append([repo, module, "Con migrations", branch, line])
                    rows_resume.append([repo, module, branch])
                else:
                    resumen[repo]["sin"].add(module)
                    rows_full.append([repo, module, "Sin migrations", branch, line])

    return resumen, rows_full, rows_resume

def generate_txt_reports(resumen, compact=False):
    def write_section_header(txt, titulo):
        txt.write("\n" + "═" * 60 + "\n")
        txt.write(f"{titulo.center(60)}\n")
        txt.write("═" * 60 + "\n\n")

    def write_versions_line(mod, versions):
        if compact:
            version_str = " ".join(f"@{v}" for v in sorted(versions))
            return f"    🔹 {mod}: {version_str}\n"
        else:
            lines = [f"    🔹 {mod}:\n"]
            lines += [f"        - {v}\n" for v in sorted(versions)]
            return "".join(lines)

    def write_block_migrations(txt):
        write_section_header(txt, "📋  RESUMEN FINAL DE MIGRACIONES  📋")
        for repo, data in resumen.items():
            if not data["con_migrations"]:
                continue
            txt.write(f"\n📁 Repositorio: {repo}\n")
            for mod, vers in sorted(data["con_migrations"].items()):
                txt.write(write_versions_line(mod, vers))

    def write_block_not_found(txt):
        write_section_header(txt, "💨 MÓDULOS NO ENCONTRADOS EN ALGUNAS VERSIONES\n")
        for repo, data in resumen.items():
            no_enc = data.get("no_encontrados", {})
            if not no_enc:
                continue
            txt.write(f"\n📁 Repositorio: {repo}\n")
            for mod, versions in sorted(no_enc.items()):
                version_str = " ".join(f"@{v}" for v in sorted(versions))
                txt.write(f"    🔍 {mod}: No encontrado en {version_str}\n")

    # oca-analysis-full.txt
    with open(TXT_SUMMARY, "w", encoding="utf-8") as txt:
        for repo, data in resumen.items():
            txt.write(f"\n{'*' * 60}\nREPOSITORIO: {repo}\n{'*' * 60}\n")
            txt.write("\n✅ CON MIGRATIONS\n")
            for mod, vers in data["con_migrations"].items():
                version_str = " ".join(f"@{v}" for v in sorted(vers))
                txt.write(f"  • {mod}: {version_str}\n")
            txt.write("\n🚫 SIN MIGRATIONS\n")
            for mod in data["sin"]:
                if mod not in data["con_migrations"]:
                    txt.write(f"  • {mod}\n")
            txt.write("\n❌ ERRORES\n")
            for err in data["errores"]:
                txt.write(f"  • {err}\n")

        txt.write("\n")
        write_block_migrations(txt)
        txt.write("\n")
        write_block_not_found(txt)

    with open(TXT_MIGRATION, "w", encoding="utf-8") as txt:
        write_block_migrations(txt)

    with open(TXT_NOT_FOUND, "w", encoding="utf-8") as txt:
        write_block_not_found(txt)


def generate_csv_reports(rows_full, rows_resume, csv_errors, resumen, compact=False):
    # Análisis completo
    with open(CSV_FULL, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Repositorio", "Módulo", "Estado", "Detalle", "Línea"])
        writer.writerows(rows_full)

    # Solo módulos CON migrations
    with open(CSV_MIGRATION, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Repositorio", "Módulo", "Versión"])
        writer.writerows(rows_resume)

    # # Módulos NO encontrados
    with open(CSV_NOT_FOUND, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Repositorio", "Módulo", "Versiones No Encontradas"])
        for repo, data in resumen.items():
            for mod, versions in data.get("no_encontrados", {}).items():
                version_str = " ".join(f"@{v}" for v in sorted(versions))
                writer.writerow([repo, mod, version_str])

    # Resumen de módulos Agrupado por repositorio
    repos = sorted(resumen.keys())

    # Mapeamos: repo -> lista de líneas (cada línea será una celda en la columna del repo)
    repo_mods = defaultdict(list)

    for repo in repos:
        for mod, vers in sorted(resumen[repo]["con_migrations"].items()):
            if compact:
                version_str = " ".join(f"@{v}" for v in sorted(vers))
                repo_mods[repo].append(f"{mod}: {version_str}")
            else:
                for v in sorted(vers):
                    repo_mods[repo].append(f"{mod}: @{v}")

    # Calculamos máximo número de filas (la columna más larga)
    max_rows = max(len(mods) for mods in repo_mods.values())
    rows = []

    for i in range(max_rows):
        row = []
        for repo in repos:
            mods = repo_mods.get(repo, [])
            row.append(mods[i] if i < len(mods) else "")
        rows.append(row)

    # Guardamos CSV
    with open(CSV_BY_REPORT, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(repos)  # encabezado = nombres de repos
        writer.writerows(rows)

    # CSV con errores de lectura
    if csv_errors:
        with open(os.path.join(BASE_DIR, "oca-errors.csv"), "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Línea", "Contenido"])
            for line, row in csv_errors:
                writer.writerow([f"{line}", " | ".join(row)])


def main():
    global LOG_FILE
    args = parse_arguments()
    if args.log:
        LOG_FILE = os.path.join(BASE_DIR, args.log)
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("")
    setup_directories()
    repos_data, csv_errors = parse_csv(args.file)
    resumen, rows_full, rows_resume = analyze_repos(args, repos_data, csv_errors)
    generate_txt_reports(resumen, compact=args.compact)
    generate_csv_reports(rows_full, rows_resume, csv_errors, resumen)

    log(" 🏁 Análisis completo. Archivos generados en oca-collector/")

    if csv_errors:
        log("\n ⚠️ Se encontraron errores en el CSV:\n")
        for line, row in csv_errors:
            if len(row) < 2:
                log(f"  • Línea {line}: Formato inválido → {row}")
            else:
                module, repo_url = row
                log(f"  • Línea {line}: ❌ Error en módulo '{module}' | Repo: {repo_url}")
        log("\n ℹ️ Revisa también el archivo 'oca-errors.csv' para más detalles.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\n🛑 Interrupción del usuario (Ctrl+C). Cerrando...")
        sys.exit(1)
