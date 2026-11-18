"""Piezas comunes y parametrizadas de las estructuras únicas (no es una estructura: el prefijo _ la excluye).

  botin.py   tablas de cofre con grupo extra solo_sin_lootr, objetos con nombre traducible, libros, pociones.
  redstone.py simulador estático de redstone (forma de cables y reglas del juego) para auditar puzles.
  piezas.py  generadores, guardianes, carteles, cofres, puertas secretas de pistones, trampas de hilo y de TNT,
             escaleras de caracol (por tramos de 6, continua de peldaños o de losas de media altura), círculos,
             cuadros y conexiones de vallas/cristales/muros.
  recorrido.py vistas para lint.walk (con mecanismos cerrados o abiertos), alcance, recorrido estricto (andar, con
             agua=True para nadar), caminos sin vuelta y bloques flotantes.
Las piezas reciben `put(x, y, z, estado, nbt=None)`, así sirven para cualquier sistema de coordenadas.
"""
