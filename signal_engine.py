
import random

def evaluar_senal(datos):
    if not datos:
        return None

    tendencia = random.choice(["CALL", "PUT", "NO_OPERAR"])

    if tendencia == "NO_OPERAR":
        return {
            "tipo": "no_operar",
            "mensaje": f"🚫 No operar en {datos['pair']} ahora (confiabilidad baja)"
        }
    else:
        return {
            "tipo": "senal",
            "mensaje": f"📈 Señal: {tendencia} en {datos['pair']}",
            "par": datos['pair'],
            "direccion": tendencia,
            "timestamp": datos["timestamp"]
        }
