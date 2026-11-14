"""Recorrido a pie común para plantillas con sótano (y < 0): lint.walk toma cualquier celda vacía con y < 0 como
suelo natural, así que se audita una copia desplazada hacia arriba (uso: from unicas._comun.recorrido import walk)."""
from core import Template
import lint

DY = 20     # desplazamiento vertical para el recorrido a pie: lint.walk toma y < 0 como suelo natural


def shifted(t):
    s = Template(t.name)
    s.blocks = {(x, y + DY, z): v for (x, y, z), v in t.blocks.items()}
    s.jigsaws = [dict(j, pos=(j["pos"][0], j["pos"][1] + DY, j["pos"][2])) for j in t.jigsaws]
    return s


def walk(t):
    return {(x, y - DY, z) for (x, y, z) in lint.walk(shifted(t))}


