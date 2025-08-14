import csv
from datetime import datetime

estadisticas = {
    "total_senales": 0,
    "ganadoras": 0,
    "perdedoras": 0,
    "pares": {},
    "horas": {}
}

def registrar_senal(par, resultado):
    estadisticas["total_senales"] += 1
    if resultado == "win":
        estadisticas["ganadoras"] += 1
    elif resultado == "loss":
        estadisticas["perdedoras"] += 1

    estadisticas["pares"][par] = estadisticas["pares"].get(par, 0) + 1
    hora = datetime.now().hour
    estadisticas["horas"][hora] = estadisticas["horas"].get(hora, 0) + 1

    with open("estadisticas.csv", "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.now(), par, resultado])

def obtener_resumen():
    return estadisticas
