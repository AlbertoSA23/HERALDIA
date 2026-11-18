"""Genera, valida y audita los recursos de estructuras de Heraldia.

Uso: python3 main.py --out <carpeta de recursos> --registries <resumen mcmeta 26.3>
Termina con código 1 ante cualquier error de validación o aviso de auditoría; solo escribe si todo pasa.
"""
import argparse, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pack import build_all
from validate import load_registries, validate_registry, validate_loot, validate_structures, validate_advancements
from writer import write, history_tables
import loot
import uniques
import mediums
import mines
import shore as coast
from uniques._common import chest_loot
import biomes
import trades, board
import arena_waves
import wizard_huts
from themes import THEMES
from lint import lint_registry, summarize


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="carpeta raíz de recursos donde se escribe data/heraldia/...")
    ap.add_argument("--registries", default=os.environ.get("MCMETA_SUMMARY"),
                    help="clon de misode/mcmeta rama 26.3-summary (o variable MCMETA_SUMMARY)")
    args = ap.parse_args()
    if not args.registries:
        ap.error("falta --registries (o la variable MCMETA_SUMMARY)")
    load_registries(args.registries)

    reg = build_all()
    errs = validate_registry(reg)
    lerrs = validate_loot([loot.TABLES] + [getattr(m, "LOOT", {}) for _, m in uniques.modules()]
                         + [{k: d["tabla"] for k, d in getattr(m, "KEYS", {}).items()} for _, m in uniques.modules()]
                         + [{s: chest_loot.trophy(s, m.TROPHY) for s, m in uniques.modules() if getattr(m, "TROPHY", None)}]
                         + [history_tables(uniques.modules()) if not reg.warnings else {}]
                         + [trades.items(uniques.modules()), board.items(THEMES), board.tables(), mediums.tables(), mines.tables(), coast.tables(),
                            arena_waves.tables(), wizard_huts.tables()])
    if errs or lerrs or reg.warnings:
        print("ERRORES:", errs, lerrs, reg.warnings[:20])
        return 1
    res = lint_registry(reg)
    if res:
        c, ex = summarize(res)
        print("AUDITORÍA DE DISEÑO:", {k: (n, ex[k]) for k, n in c.items()})
        return 1
    write(reg, args.out)
    serr = validate_structures(args.out) + validate_advancements(args.out) + biomes.check(args.out, args.registries)
    if serr:
        print("ESTRUCTURAS O LOGROS NO CARGABLES:", serr)
        return 1
    n = sum(len(f) for _, _, f in os.walk(args.out))
    print(f"OK: {len(reg.templates)} plantillas, {len(reg.pools)} pools, {n} ficheros en {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
