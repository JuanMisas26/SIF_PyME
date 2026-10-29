#!/usr/bin/env python3
"""
Script CLI interactivo para restaurar backups del Sistema de Facturación.
Uso: python scripts/restore_backup.py

Permite restaurar la base de datos a cualquier punto en el tiempo en < 30 segundos.
"""
import sys
import os
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

# Configure stdout and stderr for UTF-8 compatibility on all platforms
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.paths import DB_PATH, BACKUP_DIR

ANSI_GREEN = "\033[92m"
ANSI_YELLOW = "\033[93m"
ANSI_RED = "\033[91m"
ANSI_CYAN = "\033[96m"
ANSI_BOLD = "\033[1m"
ANSI_RESET = "\033[0m"


def print_header():
    print(f"""
{ANSI_BOLD}{ANSI_CYAN}╔══════════════════════════════════════════════════╗
║      🔄 RESTAURADOR DE BACKUP - SIF PyME         ║
║         Sistema de Facturación Local              ║
╚══════════════════════════════════════════════════╝{ANSI_RESET}
""")


def listar_snapshots():
    if not BACKUP_DIR.exists():
        print(f"{ANSI_RED}❌ No se encontró directorio de backups: {BACKUP_DIR}{ANSI_RESET}")
        return []

    snapshots = sorted(BACKUP_DIR.glob("facturacion_pyme_*.db"), reverse=True)
    return snapshots


def mostrar_snapshots(snapshots):
    print(f"{ANSI_BOLD}Backups disponibles ({len(snapshots)} encontrados):{ANSI_RESET}\n")
    print(f"{'Nº':<4} {'Archivo':<55} {'Tamaño':<10} {'Fecha'}")
    print("-" * 90)
    for i, snap in enumerate(snapshots, 1):
        stat = snap.stat()
        size_kb = round(stat.st_size / 1024, 1)
        fecha = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
        marker = f"{ANSI_GREEN}★{ANSI_RESET} " if i == 1 else "  "
        print(f"{marker}{i:<3} {snap.name:<55} {size_kb:<8} KB  {fecha}")


def restaurar(snapshot_path: Path):
    print(f"\n{ANSI_YELLOW}⚠️  ADVERTENCIA: Se reemplazará la base de datos actual.{ANSI_RESET}")
    confirm = input(f"¿Confirmar restauración de '{snapshot_path.name}'? (escriba 'SI' para confirmar): ")

    if confirm.strip().upper() != 'SI':
        print(f"{ANSI_YELLOW}Operación cancelada.{ANSI_RESET}")
        return False

    # Safety backup
    if DB_PATH.exists():
        safety_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_path = BACKUP_DIR / f"facturacion_pyme_{safety_ts}_pre_restore.db"
        shutil.copy2(str(DB_PATH), str(safety_path))
        print(f"{ANSI_GREEN}✅ Backup de seguridad creado: {safety_path.name}{ANSI_RESET}")

    # Restore
    print("🔄 Restaurando...")
    source_conn = sqlite3.connect(str(snapshot_path))
    dest_conn = sqlite3.connect(str(DB_PATH))
    try:
        source_conn.backup(dest_conn, pages=100)
        print(f"\n{ANSI_GREEN}{ANSI_BOLD}✅ Restauración completada exitosamente.{ANSI_RESET}")
        print(f"   Base de datos restaurada a: {snapshot_path.name}")
        return True
    except Exception as e:
        print(f"{ANSI_RED}❌ Error durante la restauración: {e}{ANSI_RESET}")
        return False
    finally:
        source_conn.close()
        dest_conn.close()


def main():
    print_header()
    snapshots = listar_snapshots()

    if not snapshots:
        print(f"{ANSI_RED}No hay backups disponibles para restaurar.{ANSI_RESET}")
        print(f"Directorio esperado: {BACKUP_DIR}")
        sys.exit(1)

    mostrar_snapshots(snapshots)

    print(f"\n{ANSI_BOLD}Opciones:{ANSI_RESET}")
    print("  [número] - Seleccionar backup a restaurar")
    print("  [q]      - Salir sin cambios")

    while True:
        choice = input("\n> Selección: ").strip().lower()

        if choice == 'q':
            print(f"{ANSI_YELLOW}Saliendo sin cambios.{ANSI_RESET}")
            sys.exit(0)

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(snapshots):
                restaurar(snapshots[idx])
                sys.exit(0)
            else:
                print(f"{ANSI_RED}Número fuera de rango. Ingrese entre 1 y {len(snapshots)}.{ANSI_RESET}")
        except ValueError:
            print(f"{ANSI_RED}Entrada no válida. Ingrese un número o 'q'.{ANSI_RESET}")


if __name__ == '__main__':
    main()
